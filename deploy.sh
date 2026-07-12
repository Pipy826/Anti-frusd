#!/bin/bash
# ============================================================
# Anti-fraud 一键部署脚本（本地执行）
# 
# 使用方式: 在项目根目录运行（Git Bash / WSL / Mac / Linux）
#   bash deploy.sh
#
# 前提: 本地 backend/.env 已配置好所有 API Key
# ============================================================

set -e

# ─── 配置区 ─────────────────────────────────────────────────
SERVER_IP="8.139.255.130"
SERVER_USER="root"
REMOTE_DIR="/opt/anti-fraud"
# ─────────────────────────────────────────────────────────────

echo "============================================"
echo "  Anti-fraud 一键部署"
echo "  目标服务器: ${SERVER_IP}"
echo "============================================"
echo ""

# 检查本地 .env 是否存在
if [ ! -f "backend/.env" ]; then
    echo "[x] 错误: backend/.env 文件不存在！"
    echo "    请先从 backend/.env.example 复制并填入 API Key"
    exit 1
fi

SSH_OPTS="-o StrictHostKeyChecking=no"

echo "[1/5] 确保服务器目标目录存在..."
ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_IP} "mkdir -p ${REMOTE_DIR}"

echo "[2/5] 上传 .env 配置文件..."
scp ${SSH_OPTS} backend/.env ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/.env
echo ">>> .env 上传完成"

echo "[3/5] 上传部署脚本..."
scp ${SSH_OPTS} server-setup.sh ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/server-setup.sh
echo ">>> 脚本上传完成"

echo "[4/5] 执行远程部署（首次约5-10分钟，请耐心等待）..."
echo "─────────────────────────────────────────────"
echo ""

ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_IP} "bash ${REMOTE_DIR}/server-setup.sh"

echo ""
echo "[5/5] 部署结束！"
echo ""
echo "============================================"
echo "  访问地址: http://${SERVER_IP}:8080"
echo "  管理账号: admin / admin123"
echo ""
echo "  如无法访问请在阿里云安全组放行 8080 端口"
echo "============================================"
