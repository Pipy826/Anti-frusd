# 反诈话术陪练助手

轻量互动式反诈科普训练工具。用户可选择虚构诈骗场景，通过文字、模拟电话或模拟视频方式与 AI 角色对话，结束后获得评分和避坑复盘。

## 项目结构

```text
frontend/   Vue3 + Vite 移动端前端
backend/    FastAPI 后端接口
原型图/     原始移动端 UI 图和静态 HTML 原型
文档/       项目需求文档
```

## 本地运行

前端：

```bash
cd frontend
npm install
npm run dev
```

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

如需接入 DeepSeek，设置环境变量：

```bash
set DEEPSEEK_API_KEY=your_api_key
```

没有 `DEEPSEEK_API_KEY` 时，后端会使用内置兜底话术，保证演示流程可跑通。

## Docker 一键部署

```bash
docker compose up --build -d
```

默认前端访问地址为 `http://localhost:8080`，前端容器会把 `/api/*` 反向代理到后端 FastAPI。可通过环境变量调整：

```bash
set FRONTEND_PORT=8080
set DEEPSEEK_API_KEY=your_api_key
set LLM_PROVIDER_ORDER=deepseek,qwen,wenxin
docker compose up --build -d
```

SQLite 数据库和日志会保存在 Docker volume：`anti_fraud_data`、`anti_fraud_logs`。

### 自定义域名

生产部署时建议在客户侧 Nginx、网关或云负载均衡中绑定域名，并把流量转发到前端容器端口：

```nginx
server {
  listen 80;
  server_name anti-fraud.example.gov.cn;

  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

正式环境应配置 HTTPS；浏览器语音识别在非 `localhost` 环境通常也需要 HTTPS 才能启用。

## 合规说明

本项目仅用于反诈科普学习，所有场景均为模拟虚构，不涉及真实案件、真实人员、真实账号、真实支付链接或执法数据。如遇真实诈骗，请立即拨打全国反诈专线 `96110`。

部分代码和文案由 AI 辅助生成，图片素材来自项目原型图裁剪与用户提供素材。
