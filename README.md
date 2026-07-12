# 反诈话术陪练助手

> **V1.0** | 2026-07-12 | 验收通过

沉浸式 AI 反诈科普训练工具。用户可选择虚构诈骗场景，通过**文字对话、模拟电话、模拟视频**三种方式与 AI 角色互动，实时追踪隐私/财产风险指标，结束后获得多维度评分和避坑复盘。

## 快速体验

无需任何 API Key，30 秒启动演示：

```bash
# 前端（独立运行，内置兜底数据）
cd frontend && npm install && npm run dev

# 后端（可选，启用完整功能）
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000
```

前端访问 `http://localhost:5173`，后端不启动时自动使用本地规则引擎。

## 训练闭环

```text
认知校准（3 题前测）
    ↓
沉浸式对话（文字 / 电话 / 视频）
    ↓
实时风险反馈（隐私 + 财产双轨）
    ↓
多维度复盘（四维评分 + 逐轮分析 + 最优路径）
    ↓
历史回看 & 成就追踪
```

## 功能特性

### 用户端

- **多场景选择** — 快递退款、冒充亲友、虚假兼职、杀猪盘投资、冒充公检法等多类诈骗场景
- **三种交互模式** — 文字聊天、模拟电话（含来电动画/通话计时/语音播报）、模拟视频通话
- **实时风险评估** — 隐私泄露 & 财产风险双轨风险值实时变化，触发警告提示
- **认知前测** — 场景开始前的认知测试题，检测用户对诈骗手法的基础认知
- **AI 智能对话** — 基于 DeepSeek/通义千问/文心一言的多模型 failover 对话引擎
- **分阶段话术策略** — 信任建立 → 信息套取 → 资金诱导 → 施压收网，模拟真实诈骗流程
- **语音交互** — TTS 语音合成 + ASR 语音识别（支持讯飞 WebAPI / 浏览器原生）
- **对话复盘** — 多维度评分（信息防御、情绪稳定性、核实意识、行动决策）+ 详细逐轮分析
- **历史记录** — 本地 + 服务端双重保存，随时回看
- **游戏化视图** — 成就系统与练习进度追踪

### 管理端

- **仪表盘** — 训练总量、每日活跃、平均得分、高风险触发率、认知错误率等统计
- **场景管理** — 创建/编辑/上下线场景，管理 system prompt 版本
- **对话审计** — 查看全部会话记录，支持关键词搜索、场景过滤
- **安全词库** — 动态管理输入/输出安全拦截词，支持 block/warn 策略
- **品牌配置** — 自定义 logo、标题、合规声明等白标设置
- **模型监控** — 实时查看各 LLM 提供方状态、API 成功率、平均响应时间
- **数据导出** — CSV / XLSX 格式导出训练数据

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3.5 + Vite 6，纯组件切换路由（无 vue-router） |
| 后端 | Python 3.12 + FastAPI + Pydantic v2 |
| 数据库 | SQLite（零配置，单文件持久化） |
| LLM | DeepSeek / 通义千问 / 文心一言（多模型 failover） |
| 语音 | 讯飞 WebAPI（TTS + ASR）/ 浏览器 Web Speech API |
| 认证 | JWT + bcrypt |
| 部署 | Docker Compose（nginx 反代 + uvicorn） |

## 项目结构

```text
├── frontend/                   Vue3 + Vite 移动端前端
│   ├── src/
│   │   ├── components/         17 个视图组件
│   │   │   ├── HomeView.vue        首页场景选择
│   │   │   ├── ChatView.vue        文字对话界面
│   │   │   ├── ActiveCallView.vue  模拟通话界面
│   │   │   ├── VideoCallView.vue   模拟视频通话
│   │   │   ├── IncomingCallView.vue 来电动画
│   │   │   ├── CalibrationView.vue 认知前测
│   │   │   ├── ReviewView.vue      复盘评分
│   │   │   ├── ReviewDetailView.vue 复盘详情
│   │   │   ├── AdminView.vue       管理后台
│   │   │   ├── HistoryView.vue     训练历史
│   │   │   ├── ProfileView.vue     个人中心
│   │   │   ├── GamifiedView.vue    游戏化成就
│   │   │   ├── LoginView.vue       登录注册
│   │   │   ├── SettingsView.vue    设置页面
│   │   │   ├── ModeModal.vue       模式选择弹窗
│   │   │   ├── StatusBar.vue       顶部状态栏
│   │   │   └── TabBar.vue          底部导航栏
│   │   ├── services/api.js     API 封装 + 本地降级
│   │   ├── data/scenes.js      前端兜底场景数据
│   │   ├── utils/
│   │   │   ├── phoneAudio.js   电话音效处理
│   │   │   └── storage.js      本地存储管理
│   │   ├── App.vue             根组件（路由控制）
│   │   ├── main.js             应用入口
│   │   └── styles.css          全局样式
│   ├── index.html
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf              反向代理配置
│
├── backend/                    FastAPI 后端接口
│   ├── app/
│   │   ├── main.py            API 路由 + 中间件
│   │   ├── models.py          Pydantic 数据模型
│   │   ├── database.py        SQLite 数据层
│   │   ├── llm.py             多模型 LLM 引擎
│   │   ├── voice.py           TTS / ASR 语音模块
│   │   ├── auth.py            JWT 认证模块
│   │   ├── safety.py          内容安全 + 风险评估
│   │   ├── scenes.py          场景管理辅助
│   │   ├── deepseek_client.py DeepSeek 客户端
│   │   └── logging_config.py  日志配置
│   ├── data/anti_fraud.db     SQLite 数据库文件
│   ├── logs/                   运行日志
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example           环境变量模板
│
├── scripts/                    运维与部署脚本
│   ├── acceptance_check.py    部署验收检查
│   ├── stability_monitor.py   长期稳定性监控
│   ├── load_test.py           并发压力测试
│   ├── metrics_report.py      指标报表生成
│   └── package_release.py     离线发布包打包
│
├── 文档/                       项目文档
│   ├── 场景制作SOP.md          场景内容制作流程
│   ├── 离线部署说明.md          内网离线部署指南
│   └── 第二阶段开发清单.md      V1.0 开发任务追踪
│
├── docker-compose.yml          一键部署编排
└── README.md
```

## 本地开发

### 前提条件

- Node.js 18+ / npm
- Python 3.12+
- （可选）讯飞开放平台账号（用于语音功能）

### 前端

```bash
cd frontend
npm install
npm run dev
```

开发服务器默认监听 `http://localhost:5173`。

> 前端通过 `VITE_USE_API` 环境变量控制是否连接后端。设置方式：
> - 在 `frontend/` 目录下创建 `.env` 文件，写入 `VITE_USE_API=true`
> - 或启动时通过命令行传入：`VITE_USE_API=true npm run dev`
>
> 不设置时（默认 `false`），前端使用内置兜底数据独立运行，无需后端服务。

### 后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档自动生成：`http://localhost:8000/docs`

### 环境变量

复制 `backend/.env.example` 为 `backend/.env`，按需填入：

```bash
cp backend/.env.example backend/.env
```

关键配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 空（使用兜底话术） |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |
| `LLM_PROVIDER_ORDER` | 模型优先级 | `deepseek,qwen,wenxin` |
| `TTS_PROVIDER` | 语音合成提供方 | `browser` |
| `ASR_PROVIDER` | 语音识别提供方 | `browser` |
| `XFYUN_APPID` | 讯飞 AppID | 空 |
| `XFYUN_API_SECRET` | 讯飞 API Secret | 空 |
| `XFYUN_API_KEY` | 讯飞 API Key | 空 |
| `JWT_SECRET` | JWT 签名密钥 | 内置默认值（生产请修改） |

没有 `DEEPSEEK_API_KEY` 时，后端自动使用内置兜底话术，保证演示流程可跑通。

### 默认账号

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | `admin` | `admin123` | 首次启动自动创建，可通过环境变量修改 |

> 生产环境务必通过 `ADMIN_PASSWORD` 和 `JWT_SECRET` 环境变量更换默认值。

## Docker 一键部署

```bash
docker compose up --build -d
```

默认前端访问地址：`http://localhost:8080`，前端容器 nginx 自动把 `/api/*` 反向代理到后端。

可通过环境变量调整：

```bash
# Windows CMD
set FRONTEND_PORT=8080
set DEEPSEEK_API_KEY=your_api_key
set LLM_PROVIDER_ORDER=deepseek,qwen,wenxin
docker compose up --build -d

# Linux / macOS
FRONTEND_PORT=8080 DEEPSEEK_API_KEY=your_key docker compose up --build -d
```

**持久化存储：**
- `anti_fraud_data` volume — SQLite 数据库
- `anti_fraud_logs` volume — 应用日志

### 自定义域名

生产部署建议在宿主机 Nginx 或云负载均衡绑定域名：

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

正式环境应配置 HTTPS。浏览器语音识别在非 `localhost` 环境通常也需要 HTTPS 才能启用。

## API 接口概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/start` | 开始对话会话 |
| POST | `/api/chat/send` | 发送消息 |
| POST | `/api/chat/end` | 结束会话并获取复盘 |

### 场景 & 语音

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scenes` | 获取场景列表 |
| GET | `/api/voice/config/{scene_id}` | 获取语音配置 |
| POST | `/api/voice/tts` | 文本转语音 |
| POST | `/api/voice/asr` | 语音转文本 |

### 认知测试

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/cognitive/submit` | 提交认知前测答案 |

### 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/history` | 获取训练历史 |
| GET | `/api/user/settings` | 获取用户设置 |
| PUT | `/api/user/settings` | 更新用户设置 |
| GET | `/api/user/stats` | 获取用户统计 |

### 管理后台（需 Admin JWT）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/dashboard` | 仪表盘数据 |
| GET | `/api/admin/metrics` | 系统监控指标 |
| GET | `/api/admin/model-status` | LLM 模型状态 |
| GET | `/api/admin/scenes` | 场景列表（含下线） |
| POST | `/api/admin/scenes` | 创建场景 |
| PUT | `/api/admin/scenes/{id}` | 更新场景 |
| GET | `/api/admin/conversations` | 对话记录审计 |
| GET | `/api/admin/safety-terms` | 安全词库 |
| POST | `/api/admin/safety-terms` | 添加安全词 |
| PUT | `/api/admin/brand` | 更新品牌配置 |
| GET | `/api/admin/export.csv` | 导出 CSV |
| GET | `/api/admin/export.xlsx` | 导出 XLSX |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/brand` | 获取品牌配置 |
| POST | `/api/frontend/error` | 前端错误上报 |

## 多租户支持

通过请求头 `X-Tenant-ID` 实现数据隔离，默认租户为 `default`。前端通过 URL 参数 `?tenant=xxx` 或 localStorage 自动携带。

## 安全设计

- **内容过滤** — 输入/输出双向安全词拦截，敏感信息脱敏
- **风险评估** — 实时隐私泄露 + 财产风险双轨评估引擎
- **速率限制** — IP 级别 60次/分钟，会话级别 24 条消息上限
- **会话超时** — 空闲 1 小时自动清理
- **JWT 认证** — 管理接口全部受 Admin 角色保护
- **兜底降级** — LLM 不可用时自动切换到本地规则引擎

## 已上线场景

| ID | 标题 | 分类 | 难度 | 交互模式 |
|----|------|------|------|----------|
| `delivery` | 快递退款诈骗 | 青年专区 | ★★☆ | 文字/电话 |
| `classmate_link` | 同学群钓鱼链接 | 青年专区 | ★★★ | 文字/电话 |
| `hacked_friend_accident` | 好友被盗借钱 | 青年专区 | ★★★ | 文字/电话 |
| `elder_deepfake` | AI 换脸视频诈骗 | 老年专区 | ★★★★ | 文字/视频 |
| `family` | 冒充亲友紧急借款 | 老年专区 | ★★★ | 文字/电话 |
| `police` | 冒充公检法 | 青年专区 | ★★★★ | 文字/电话 |
| `investment` | 虚假投资理财 | 职场专区 | ★★★☆ | 文字/电话 |
| `leader` | 冒充领导转账 | 职场专区 | ★★★☆ | 文字/电话 |
| `parttime` | 虚假兼职刷单 | 青年专区 | ★★☆ | 文字/电话 |
| `eldercare` | 养老保健品诈骗 | 老年专区 | ★★★ | 文字/电话 |

新增场景无需修改代码，通过管理后台或 API 即可完成，详见 [场景制作 SOP](文档/场景制作SOP.md)。

## 运维脚本

位于 `scripts/` 目录：

| 脚本 | 用途 | 示例 |
|------|------|------|
| `acceptance_check.py` | 部署后全量验收 | `python scripts/acceptance_check.py --json` |
| `stability_monitor.py` | 7 天持续监控 | `python scripts/stability_monitor.py --duration-days 7` |
| `load_test.py` | 并发压力测试 | `python scripts/load_test.py` |
| `metrics_report.py` | 生成指标报表 | `python scripts/metrics_report.py` |
| `package_release.py` | 打包离线部署包 | `python scripts/package_release.py` |

## 离线部署

支持政务、学校、企业内网等无外网环境部署。详细步骤见 [离线部署说明](文档/离线部署说明.md)。

快速流程：

```bash
# 联网机器打包
python scripts/package_release.py

# 联网机器导出镜像
docker compose build
docker save anti-fraud-backend:1.0 anti-fraud-frontend:1.0 -o anti-fraud-images.tar

# 离线服务器部署
docker load -i anti-fraud-images.tar
docker compose up -d
```

## 合规说明

本项目仅用于反诈科普学习，所有场景均为模拟虚构，不涉及真实案件、真实人员、真实账号、真实支付链接或执法数据。如遇真实诈骗，请立即拨打全国反诈专线 **96110**。

部分代码和文案由 AI 辅助生成，图片素材来自项目原型图裁剪与用户提供素材。

## 相关文档

- [场景制作 SOP](文档/场景制作SOP.md) — 场景内容创建与维护流程
- [离线部署说明](文档/离线部署说明.md) — 内网/离线环境部署指南
- [第二阶段开发清单](文档/第二阶段开发清单.md) — V1.0 完整开发任务与验收记录

## License

仅供学习研究使用。
