from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import traceback
import urllib.error
import urllib.parse
import urllib.request
from email.utils import formatdate
from typing import Any

import websockets

from .models import ASRResponse, TTSResponse, VoiceConfig


# ─── 场景 → 语音映射 ───────────────────────────────────────────
# (voiceName, gender, phoneNumber, location)
SCENE_VOICE_MAP: dict[str, tuple[str, str, str, str]] = {
    "delivery": ("快递客服女声", "female", "021 38** 7621", "上海"),
    "family": ("亲友焦急男声", "male", "010 67** 1930", "北京"),
    "classmate_link": ("毕业同学青年声", "neutral", "139 **** 1027", "本地"),
    "hacked_friend_accident": ("好友焦急男声", "male", "138 **** 7721", "未知"),
    "elder_deepfake": ("儿女视频来电", "male", "186 **** 5208", "外地"),
    "parttime": ("兼职客服女声", "female", "0755 29** 5408", "深圳"),
    "police": ("办案人员男声", "male", "025 86** 1100", "南京"),
    "eldercare": ("健康顾问女声", "female", "028 61** 8896", "成都"),
    "leader": ("单位领导男声", "male", "0571 77** 4088", "杭州"),
    "investment": ("投资顾问男声", "male", "020 39** 6602", "广州"),
}


class XfyunError(RuntimeError):
    pass


# ─── 公共接口 ───────────────────────────────────────────────


def get_voice_config(scene_id: str) -> VoiceConfig:
    entry = SCENE_VOICE_MAP.get(scene_id, ("训练角色中性声", "neutral", "188 **** 8888", "未知"))
    voice_name, gender, phone, location = entry
    tts_provider = os.getenv("TTS_PROVIDER", "browser")
    asr_provider = os.getenv("ASR_PROVIDER", "browser")
    if tts_provider != "browser" and not _xfyun_ready():
        tts_provider = "browser"
    if asr_provider != "browser" and not _xfyun_ready():
        asr_provider = "browser"
    return VoiceConfig(
        sceneId=scene_id,
        ttsProvider=tts_provider,
        ttsFallback="browser",
        asrProvider=asr_provider,
        asrFallback="browser",
        voiceName=voice_name,
        voiceGender=gender,  # type: ignore[arg-type]
        rate=float(os.getenv("TTS_RATE", "0.95")),
        phoneNumber=phone,
        location=location,
    )


# ─── 异步版本（供 FastAPI async 端点直接 await）───────────────


async def async_synthesize_speech(scene_id: str, text: str) -> TTSResponse:
    config = get_voice_config(scene_id)

    if config.ttsProvider == "browser":
        return TTSResponse(
            provider="browser",
            voiceName=config.voiceName,
            degraded=True,
            error="third_party_tts_not_configured",
        )

    # 超拟人合成（优先）
    if config.ttsProvider == "xfyun-mega":
        try:
            audio = await _xfyun_mega_tts(scene_id, text, config.voiceGender)
            return TTSResponse(
                provider="xfyun-mega",
                voiceName=config.voiceName,
                audioBase64=base64.b64encode(audio).decode("ascii"),
                mimeType="audio/mpeg",
            )
        except Exception as exc:
            traceback.print_exc()
            # 降级到普通讯飞合成
            try:
                audio = await _xfyun_tts(scene_id, text, config.voiceGender)
                return TTSResponse(
                    provider="xfyun",
                    voiceName=config.voiceName,
                    audioBase64=base64.b64encode(audio).decode("ascii"),
                    mimeType=_xfyun_tts_mime_type(),
                    degraded=True,
                    error=f"mega_fallback:{exc.__class__.__name__}:{exc}",
                )
            except Exception:
                return TTSResponse(provider="browser", voiceName=config.voiceName, degraded=True, error=str(exc))

    # 普通讯飞合成
    if config.ttsProvider == "xfyun":
        try:
            audio = await _xfyun_tts(scene_id, text, config.voiceGender)
            return TTSResponse(
                provider="xfyun",
                voiceName=config.voiceName,
                audioBase64=base64.b64encode(audio).decode("ascii"),
                mimeType=_xfyun_tts_mime_type(),
            )
        except Exception as exc:
            return TTSResponse(provider="browser", voiceName=config.voiceName, degraded=True, error=exc.__class__.__name__)

    return _legacy_tts(config, scene_id, text)


async def async_transcribe_audio(scene_id: str, audio_base64: str, mime_type: str) -> ASRResponse:
    config = get_voice_config(scene_id)
    if config.asrProvider == "browser":
        return ASRResponse(provider="browser", degraded=True, error="third_party_asr_not_configured")

    if config.asrProvider in {"xfyun", "xfyun-dialect"}:
        try:
            audio = base64.b64decode(audio_base64)
            text = await _xfyun_asr(audio, mime_type)
            return ASRResponse(provider=config.asrProvider, text=text)
        except Exception as exc:
            return ASRResponse(provider="browser", degraded=True, error=exc.__class__.__name__)

    return _legacy_asr(config, scene_id, audio_base64, mime_type)


# ─── 同步版本（向后兼容）──────────────────────────────────────


def synthesize_speech(scene_id: str, text: str) -> TTSResponse:
    return _run(async_synthesize_speech(scene_id, text))


def transcribe_audio(scene_id: str, audio_base64: str, mime_type: str) -> ASRResponse:
    return _run(async_transcribe_audio(scene_id, audio_base64, mime_type))


# ─── 超拟人合成 (Mega TTS) ───────────────────────────────────


async def _xfyun_mega_tts(scene_id: str, text: str, gender: str) -> bytes:
    """讯飞超拟人合成 API。

    文档：wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6
    协议：header/parameter/payload 三段式，流式返回音频
    响应：payload.audio.audio (base64) + payload.audio.status (0/1/2)
    """
    endpoint = _env("XFYUN_MEGA_TTS_ENDPOINT", "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6")
    url = _xfyun_auth_url(endpoint)
    timeout = int(os.getenv("TTS_TIMEOUT", "15"))

    vcn = _mega_voice(scene_id, gender)
    speed = int(os.getenv("XFYUN_MEGA_TTS_SPEED", "55"))
    volume = int(os.getenv("XFYUN_MEGA_TTS_VOLUME", "55"))

    # 一次性发送全部文本（status=2）
    payload = {
        "header": {
            "app_id": _env("XFYUN_APPID"),
            "status": 2,
        },
        "parameter": {
            "tts": {
                "vcn": vcn,
                "speed": speed,
                "volume": volume,
                "pitch": 50,
                "bgs": 0,
                "reg": 0,
                "rdn": 0,
                "audio": {
                    "encoding": "lame",
                    "sample_rate": 24000,
                    "channels": 1,
                    "bit_depth": 16,
                    "frame_size": 0,
                },
            },
        },
        "payload": {
            "text": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain",
                "status": 2,
                "seq": 0,
                "text": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            }
        },
    }

    chunks: list[bytes] = []
    async with websockets.connect(url, open_timeout=timeout, close_timeout=2, max_size=8 * 1024 * 1024) as ws:
        await ws.send(json.dumps(payload, ensure_ascii=False))

        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            message = json.loads(raw)

            # 检查错误
            header = message.get("header", {})
            code = header.get("code", 0)
            if int(code) != 0:
                raise XfyunError(f"mega_tts_error:{header.get('message', code)}")

            # 提取音频数据 (payload.audio.audio)
            payload_resp = message.get("payload", {})
            audio_data = payload_resp.get("audio", {})
            audio_b64 = audio_data.get("audio", "")
            if audio_b64:
                chunks.append(base64.b64decode(audio_b64))

            # status=2 表示最后一帧
            status = int(audio_data.get("status", 0))
            if status == 2:
                break
            # 也检查 header.status (仅在有 audio key 时才作为结束标志)
            if int(header.get("status", 0)) == 2:
                break

    if not chunks:
        raise XfyunError("empty_mega_tts_audio")
    return b"".join(chunks)


def _mega_voice(scene_id: str, gender: str) -> str:
    """获取超拟人合成的发音人 ID。支持按场景覆盖。"""
    scene_key = f"XFYUN_MEGA_TTS_VOICE_{scene_id.upper()}"
    if os.getenv(scene_key):
        return os.getenv(scene_key, "")
    if gender == "male":
        return os.getenv("XFYUN_MEGA_TTS_VOICE_MALE", "x6_lingfeiyi_pro")
    if gender == "female":
        return os.getenv("XFYUN_MEGA_TTS_VOICE_FEMALE", "x6_lingxiaoxuan_pro")
    return os.getenv("XFYUN_MEGA_TTS_VOICE_NEUTRAL", "x6_lingxiaoxuan_pro")


# ─── 普通讯飞 TTS ───────────────────────────────────────────


async def _xfyun_tts(scene_id: str, text: str, gender: str) -> bytes:
    url = _xfyun_auth_url(_env("XFYUN_TTS_ENDPOINT", "wss://tts-api.xfyun.cn/v2/tts"))
    timeout = int(os.getenv("TTS_TIMEOUT", "15"))
    payload = {
        "common": {"app_id": _env("XFYUN_APPID")},
        "business": {
            "aue": os.getenv("XFYUN_TTS_AUE", "lame"),
            "auf": os.getenv("XFYUN_TTS_AUF", "audio/L16;rate=16000"),
            "vcn": _xfyun_voice(scene_id, gender),
            "tte": "UTF8",
            "speed": _speech_rate_to_xfyun(os.getenv("TTS_RATE", "0.95")),
            "volume": int(os.getenv("XFYUN_TTS_VOLUME", "55")),
            "pitch": int(os.getenv("XFYUN_TTS_PITCH", "50")),
        },
        "data": {"status": 2, "text": base64.b64encode(text.encode("utf-8")).decode("ascii")},
    }
    chunks: list[bytes] = []
    async with websockets.connect(url, open_timeout=timeout, close_timeout=1, max_size=8 * 1024 * 1024) as websocket:
        await websocket.send(json.dumps(payload, ensure_ascii=False))
        while True:
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))
            _raise_for_xfyun_error(message)
            audio = message.get("data", {}).get("audio", "")
            if audio:
                chunks.append(base64.b64decode(audio))
            if int(message.get("data", {}).get("status", 0)) == 2:
                break
    if not chunks:
        raise XfyunError("empty_tts_audio")
    return b"".join(chunks)


# ─── 讯飞 ASR（方言识别大模型 + 普通识别）───────────────────


async def _xfyun_asr(audio: bytes, mime_type: str) -> str:
    endpoint = _env("XFYUN_ASR_ENDPOINT", "wss://iat.cn-huabei-1.xf-yun.com/v1")
    protocol = os.getenv("XFYUN_ASR_PROTOCOL", "v1" if "/v1" in endpoint else "v2").lower()
    
    # Convert non-PCM audio to PCM16 using ffmpeg if needed
    if "audio/l16" not in mime_type.lower() and "pcm" not in mime_type.lower() and "raw" not in mime_type.lower():
        audio = await _convert_to_pcm16(audio, mime_type)
    
    if protocol == "v2":
        return await _xfyun_asr_v2(endpoint, audio)
    return await _xfyun_asr_v1(endpoint, audio)


async def _convert_to_pcm16(audio: bytes, mime_type: str) -> bytes:
    """Convert audio from any format to PCM16 16kHz mono using ffmpeg."""
    import subprocess
    import tempfile
    
    # Determine input format
    ext = ".webm"
    if "mp4" in mime_type:
        ext = ".mp4"
    elif "ogg" in mime_type:
        ext = ".ogg"
    elif "mp3" in mime_type or "mpeg" in mime_type:
        ext = ".mp3"
    
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as inf:
        inf.write(audio)
        in_path = inf.name
    
    out_path = in_path + ".pcm"
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", in_path,
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            out_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        
        if proc.returncode != 0:
            raise XfyunError("ffmpeg_conversion_failed")
        
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        import os as _os
        try:
            _os.unlink(in_path)
        except OSError:
            pass
        try:
            _os.unlink(out_path)
        except OSError:
            pass


async def _xfyun_asr_v1(endpoint: str, audio: bytes) -> str:
    url = _xfyun_auth_url(endpoint)
    timeout = int(os.getenv("ASR_TIMEOUT", "20"))
    results: list[str] = []
    chunks = list(_chunks(audio, int(os.getenv("XFYUN_ASR_FRAME_BYTES", "1280"))))
    if not chunks:
        raise XfyunError("empty_asr_audio")
    completed = False
    async with websockets.connect(url, open_timeout=timeout, close_timeout=1, max_size=8 * 1024 * 1024) as websocket:
        for index, chunk in enumerate(chunks):
            status = 2 if len(chunks) == 1 else 0 if index == 0 else 2 if index == len(chunks) - 1 else 1
            payload = {
                "header": {"app_id": _env("XFYUN_APPID"), "status": status},
                "parameter": {
                    "iat": {
                        "domain": os.getenv("XFYUN_ASR_DOMAIN", "slm"),
                        "language": os.getenv("XFYUN_ASR_LANGUAGE", "zh_cn"),
                        "accent": os.getenv("XFYUN_ASR_ACCENT", "mandarin"),
                        "eos": int(os.getenv("XFYUN_ASR_EOS", "2500")),
                        "result": {"encoding": "utf8", "compress": "raw", "format": "json"},
                    }
                },
                "payload": {
                    "audio": {
                        "encoding": "raw",
                        "sample_rate": int(os.getenv("XFYUN_ASR_SAMPLE_RATE", "16000")),
                        "channels": 1,
                        "bit_depth": 16,
                        "status": status,
                        "audio": base64.b64encode(chunk).decode("ascii"),
                    }
                },
            }
            await websocket.send(json.dumps(payload, ensure_ascii=False))
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))
            _raise_for_xfyun_error(message)
            text = _parse_asr_v1_text(message)
            if text:
                results.append(text)
            completed = int(message.get("header", {}).get("status", 0)) == 2
            if status == 2:
                break
            await asyncio.sleep(float(os.getenv("XFYUN_ASR_FRAME_INTERVAL", "0.04")))

        while not completed:
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))
            _raise_for_xfyun_error(message)
            text = _parse_asr_v1_text(message)
            if text:
                results.append(text)
            completed = int(message.get("header", {}).get("status", 0)) == 2
    return _dedupe_join(results)


async def _xfyun_asr_v2(endpoint: str, audio: bytes) -> str:
    url = _xfyun_auth_url(endpoint)
    timeout = int(os.getenv("ASR_TIMEOUT", "20"))
    results: list[str] = []
    chunks = list(_chunks(audio, int(os.getenv("XFYUN_ASR_FRAME_BYTES", "1280"))))
    if not chunks:
        raise XfyunError("empty_asr_audio")
    completed = False
    async with websockets.connect(url, open_timeout=timeout, close_timeout=1, max_size=8 * 1024 * 1024) as websocket:
        for index, chunk in enumerate(chunks):
            status = 2 if len(chunks) == 1 else 0 if index == 0 else 2 if index == len(chunks) - 1 else 1
            payload = {
                "common": {"app_id": _env("XFYUN_APPID")},
                "business": {
                    "language": os.getenv("XFYUN_ASR_LANGUAGE", "zh_cn"),
                    "domain": os.getenv("XFYUN_ASR_DOMAIN", "iat"),
                    "accent": os.getenv("XFYUN_ASR_ACCENT", "mandarin"),
                    "vad_eos": int(os.getenv("XFYUN_ASR_EOS", "2500")),
                },
                "data": {
                    "status": status,
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio": base64.b64encode(chunk).decode("ascii"),
                },
            }
            await websocket.send(json.dumps(payload, ensure_ascii=False))
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))
            _raise_for_xfyun_error(message)
            text = _parse_iat_result(message.get("data", {}).get("result", {}))
            if text:
                results.append(text)
            completed = int(message.get("data", {}).get("status", 0)) == 2
            if status == 2:
                break
            await asyncio.sleep(float(os.getenv("XFYUN_ASR_FRAME_INTERVAL", "0.04")))

        while not completed:
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))
            _raise_for_xfyun_error(message)
            text = _parse_iat_result(message.get("data", {}).get("result", {}))
            if text:
                results.append(text)
            completed = int(message.get("data", {}).get("status", 0)) == 2
    return _dedupe_join(results)


# ─── Legacy TTS/ASR（第三方通用接口）────────────────────────


def _legacy_tts(config: VoiceConfig, scene_id: str, text: str) -> TTSResponse:
    endpoint = os.getenv("TTS_ENDPOINT")
    api_key = os.getenv("TTS_API_KEY")
    if not endpoint or not api_key:
        return TTSResponse(provider="browser", voiceName=config.voiceName, degraded=True, error="missing_tts_endpoint_or_key")

    payload = {
        "text": text,
        "voice": config.voiceName,
        "gender": config.voiceGender,
        "rate": config.rate,
        "scene_id": scene_id,
    }
    try:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=int(os.getenv("TTS_TIMEOUT", "15"))) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read()
        if "application/json" in content_type:
            data = json.loads(raw.decode("utf-8"))
            return TTSResponse(
                provider=config.ttsProvider,
                voiceName=config.voiceName,
                audioBase64=data.get("audioBase64") or data.get("audio_base64", ""),
                mimeType=data.get("mimeType") or data.get("mime_type", "audio/mpeg"),
            )
        return TTSResponse(
            provider=config.ttsProvider,
            voiceName=config.voiceName,
            audioBase64=base64.b64encode(raw).decode("ascii"),
            mimeType=content_type or "audio/mpeg",
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        return TTSResponse(provider="browser", voiceName=config.voiceName, degraded=True, error=exc.__class__.__name__)


def _legacy_asr(config: VoiceConfig, scene_id: str, audio_base64: str, mime_type: str) -> ASRResponse:
    endpoint = os.getenv("ASR_ENDPOINT")
    api_key = os.getenv("ASR_API_KEY")
    if not endpoint or not api_key:
        return ASRResponse(provider="browser", degraded=True, error="missing_asr_endpoint_or_key")

    payload = {"audioBase64": audio_base64, "mimeType": mime_type, "scene_id": scene_id, "language": "zh-CN"}
    try:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=int(os.getenv("ASR_TIMEOUT", "20"))) as response:
            data = json.loads(response.read().decode("utf-8"))
        return ASRResponse(provider=config.asrProvider, text=data.get("text") or data.get("transcript", ""))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return ASRResponse(provider="browser", degraded=True, error=exc.__class__.__name__)


# ─── 鉴权 ───────────────────────────────────────────────────


def _xfyun_auth_url(endpoint: str) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    path = parsed.path or "/"
    date = formatdate(usegmt=True)
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature = base64.b64encode(
        hmac.new(_env("XFYUN_API_SECRET").encode("utf-8"), signature_origin.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")
    authorization_origin = (
        f'api_key="{_env("XFYUN_API_KEY")}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    query = urllib.parse.urlencode(
        {
            "authorization": base64.b64encode(authorization_origin.encode("utf-8")).decode("ascii"),
            "date": date,
            "host": host,
        }
    )
    separator = "&" if parsed.query else "?"
    return f"{endpoint}{separator}{query}"


# ─── 解析工具 ────────────────────────────────────────────────


def _parse_asr_v1_text(message: dict[str, Any]) -> str:
    payload = message.get("payload", {})
    result = payload.get("result", {})
    encoded = result.get("text") or result.get("result") or ""
    if not encoded:
        return ""
    decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
    data = json.loads(decoded)
    if isinstance(data, dict):
        return data.get("text") or _parse_iat_result(data)
    return ""


def _parse_iat_result(result: dict[str, Any]) -> str:
    pieces: list[str] = []
    for ws_item in result.get("ws", []):
        candidates = ws_item.get("cw", [])
        if candidates:
            pieces.append(candidates[0].get("w", ""))
    return "".join(pieces)


def _raise_for_xfyun_error(message: dict[str, Any]) -> None:
    header = message.get("header", {})
    code = header.get("code", message.get("code", 0))
    if int(code or 0) != 0:
        raise XfyunError(str(header.get("message") or message.get("message") or code))


# ─── 发音人选择 ──────────────────────────────────────────────


def _xfyun_voice(scene_id: str, gender: str) -> str:
    scene_key = f"XFYUN_TTS_VOICE_{scene_id.upper()}"
    if os.getenv(scene_key):
        return os.getenv(scene_key, "")
    if gender == "male":
        return os.getenv("XFYUN_TTS_VOICE_MALE", "aisjiuxu")
    if gender == "female":
        return os.getenv("XFYUN_TTS_VOICE_FEMALE", "xiaoyan")
    return os.getenv("XFYUN_TTS_VOICE_NEUTRAL", "aisxping")


def _xfyun_tts_mime_type() -> str:
    aue = os.getenv("XFYUN_TTS_AUE", "lame").lower()
    if aue in {"raw", "pcm"}:
        return "audio/L16;rate=16000"
    if aue == "speex":
        return "audio/speex"
    return "audio/mpeg"


def _speech_rate_to_xfyun(rate: str) -> int:
    try:
        value = float(rate)
    except ValueError:
        value = 0.95
    return max(0, min(100, int(value * 50)))


# ─── 通用工具 ────────────────────────────────────────────────


def _chunks(data: bytes, size: int):
    for start in range(0, len(data), size):
        yield data[start : start + size]


def _dedupe_join(parts: list[str]) -> str:
    text = ""
    for part in parts:
        if part and not text.endswith(part):
            text += part
    return text.strip()


def _xfyun_ready() -> bool:
    return bool(os.getenv("XFYUN_APPID") and os.getenv("XFYUN_API_KEY") and os.getenv("XFYUN_API_SECRET"))


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise XfyunError(f"missing_{name.lower()}")
    return value


def _run(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)
