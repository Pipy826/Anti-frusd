#!/bin/bash
# ============================================================
# Anti-fraud 服务器端部署脚本
# 
# 前提：.env 文件已通过 deploy.sh 或手动上传到 /opt/anti-fraud/
#
# 使用方式:
#   1. 推荐: 在本地运行 deploy.sh（自动上传 .env 并执行此脚本）
#   2. 手动: SSH 登录服务器后执行 bash /opt/anti-fraud/server-setup.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

REMOTE_DIR="/opt/anti-fraud"
REPO_URL="https://github.com/Pipy826/Anti-frusd.git"

echo ""
echo "============================================"
echo "  Anti-fraud 服务器部署脚本"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# ─── 1. 安装 Docker ─────────────────────────────────────────
if command -v docker &> /dev/null; then
    log "Docker 已安装: $(docker --version)"
else
    warn "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    log "Docker 安装完成"
fi

# ─── 2. 安装 Docker Compose 插件 ────────────────────────────
if docker compose version &> /dev/null; then
    log "Docker Compose 已安装: $(docker compose version)"
else
    warn "安装 Docker Compose 插件..."
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
    log "Docker Compose 安装完成"
fi

# ─── 3. 安装 Git ────────────────────────────────────────────
if command -v git &> /dev/null; then
    log "Git 已安装"
else
    warn "安装 Git..."
    apt-get update -qq && apt-get install -y -qq git
    log "Git 安装完成"
fi

# ─── 4. 获取代码 ────────────────────────────────────────────
if [ -d "${REMOTE_DIR}/.git" ]; then
    log "项目已存在，拉取最新代码..."
    cd ${REMOTE_DIR}
    git fetch origin main
    git reset --hard origin/main
else
    warn "克隆项目到 ${REMOTE_DIR}..."
    rm -rf ${REMOTE_DIR}
    git clone ${REPO_URL} ${REMOTE_DIR}
fi
cd ${REMOTE_DIR}
log "代码就绪: $(git log --oneline -1)"

# ─── 5. 检查 .env 文件 ──────────────────────────────────────
if [ ! -f "${REMOTE_DIR}/.env" ]; then
    warn ".env 文件不存在，从 .env.example 创建模板..."
    if [ -f "${REMOTE_DIR}/backend/.env.example" ]; then
        cp ${REMOTE_DIR}/backend/.env.example ${REMOTE_DIR}/.env
        # 追加生产必需配置
        echo -e "\nFRONTEND_PORT=8080" >> ${REMOTE_DIR}/.env
        echo "JWT_SECRET=anti_fraud_prod_secret_2024_secure" >> ${REMOTE_DIR}/.env
        echo "JWT_EXPIRE_HOURS=72" >> ${REMOTE_DIR}/.env
        echo "ADMIN_USERNAME=admin" >> ${REMOTE_DIR}/.env
        echo "ADMIN_PASSWORD=admin123" >> ${REMOTE_DIR}/.env
    else
        err ".env 文件缺失且无法找到模板，请先上传 .env 文件到 ${REMOTE_DIR}/"
    fi
    warn "请编辑 ${REMOTE_DIR}/.env 填入正确的 API Key 后重新运行此脚本"
fi
log ".env 配置文件就绪"

# ─── 6. 确保 .env 有生产必需字段 ────────────────────────────
grep -q "FRONTEND_PORT" ${REMOTE_DIR}/.env || echo -e "\nFRONTEND_PORT=8080" >> ${REMOTE_DIR}/.env
grep -q "JWT_SECRET" ${REMOTE_DIR}/.env || echo -e "\nJWT_SECRET=anti_fraud_prod_secret_2024_secure" >> ${REMOTE_DIR}/.env
grep -q "JWT_EXPIRE_HOURS" ${REMOTE_DIR}/.env || echo -e "\nJWT_EXPIRE_HOURS=72" >> ${REMOTE_DIR}/.env
grep -q "ADMIN_USERNAME" ${REMOTE_DIR}/.env || echo -e "\nADMIN_USERNAME=admin" >> ${REMOTE_DIR}/.env
grep -q "ADMIN_PASSWORD" ${REMOTE_DIR}/.env || echo -e "\nADMIN_PASSWORD=admin123" >> ${REMOTE_DIR}/.env

# ─── 6.5 生成自签名 SSL 证书（用于 HTTPS）──────────────────
SSL_DIR="${REMOTE_DIR}/ssl"
if [ ! -f "${SSL_DIR}/server.crt" ]; then
    warn "生成自签名 SSL 证书..."
    mkdir -p ${SSL_DIR}
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout ${SSL_DIR}/server.key \
        -out ${SSL_DIR}/server.crt \
        -subj "/C=CN/ST=China/L=Beijing/O=AntiFraud/CN=8.139.255.130" \
        -addext "subjectAltName=IP:8.139.255.130" \
        2>/dev/null
    chmod 600 ${SSL_DIR}/server.key
    log "SSL 证书生成完成（有效期10年）"
else
    log "SSL 证书已存在"
fi

# ─── 7. 构建并启动服务 ──────────────────────────────────────
log "停止旧服务..."
docker compose down 2>/dev/null || true

log "构建 Docker 镜像（首次约3-5分钟）..."
docker compose build

log "启动服务..."
docker compose up -d

# ─── 8. 健康检查 ────────────────────────────────────────────
log "等待服务启动..."
sleep 8

RETRY=0
MAX_RETRY=5
until curl -sf http://localhost:8080/api/health > /dev/null 2>&1 || [ $RETRY -ge $MAX_RETRY ]; do
    RETRY=$((RETRY+1))
    warn "等待后端就绪... ($RETRY/$MAX_RETRY)"
    sleep 3
done

echo ""
echo "─── 容器状态 ───────────────────────────────"
docker compose ps
echo ""

RUNNING=$(docker compose ps | grep -c "Up" || echo "0")
if [ "$RUNNING" -ge 2 ]; then
    log "所有服务运行正常！"
else
    warn "部分服务可能未完全启动，请检查日志："
    echo "  docker compose logs -f"
fi

# ─── 9. 配置防火墙 ─────────────────────────────────────────
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8080/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
elif command -v ufw &> /dev/null; then
    ufw allow 8080/tcp 2>/dev/null || true
fi

# ─── 完成 ────────────────────────────────────────────────────
echo ""
echo "============================================"
echo -e "  ${GREEN}部署完成！${NC}"
echo ""
echo "  HTTP  访问: http://8.139.255.130:8080"
echo "  HTTPS 访问: https://8.139.255.130:8443"
echo "  (手机请用 HTTPS 地址以启用麦克风)"
echo ""
echo "  管理账号: admin"
echo "  管理密码: admin123"
echo ""
echo "  ⚠ 阿里云用户请确认安全组已放行 8080 和 8443 端口"
echo "  ⚠ 首次用 HTTPS 访问时浏览器会提示证书不受信任"
echo "    点击「高级」→「继续访问」即可"
echo ""
echo "  运维命令:"
echo "    查看日志:  cd /opt/anti-fraud && docker compose logs -f"
echo "    仅看后端:  cd /opt/anti-fraud && docker compose logs -f backend"
echo "    重启服务:  cd /opt/anti-fraud && docker compose restart"
echo "    停止服务:  cd /opt/anti-fraud && docker compose down"
echo "    更新部署:  cd /opt/anti-fraud && git pull && docker compose up -d --build"
echo "============================================"
echo ""
