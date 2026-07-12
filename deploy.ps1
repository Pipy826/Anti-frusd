# ============================================================
# Anti-fraud 一键部署脚本 (PowerShell)
# 
# 使用方式: 右键此文件 -> "使用 PowerShell 运行"
# 或在终端中: powershell -ExecutionPolicy Bypass -File deploy.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$SERVER = "8.139.255.130"
$USER = "root"
$PASS = "T8y2x62006"
$REMOTE_DIR = "/opt/anti-fraud"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Anti-fraud 一键部署" -ForegroundColor Cyan
Write-Host "  目标服务器: $SERVER" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ─── 检查并安装 sshpass 替代方案 ────────────────────────────
# Windows 下使用 ssh + 自动输入密码的方式

# 生成 SSH Key（如果不存在）
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa"
if (-not (Test-Path "$sshKeyPath.pub")) {
    Write-Host "[1/6] 生成 SSH 密钥..." -ForegroundColor Yellow
    ssh-keygen -t rsa -b 4096 -f $sshKeyPath -N '""' -q
    Write-Host "[OK] SSH 密钥已生成" -ForegroundColor Green
} else {
    Write-Host "[1/6] SSH 密钥已存在" -ForegroundColor Green
}

# 读取公钥
$pubKey = Get-Content "$sshKeyPath.pub" -Raw

Write-Host ""
Write-Host "─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  接下来需要输入服务器密码（共需3次）" -ForegroundColor Yellow
Write-Host "  密码: $PASS" -ForegroundColor Yellow  
Write-Host "─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# ─── 配置免密登录 ───────────────────────────────────────────
Write-Host "[2/6] 配置 SSH 免密登录（输入密码）..." -ForegroundColor Yellow
$pubKeyTrimmed = $pubKey.Trim()
ssh -o StrictHostKeyChecking=no "${USER}@${SERVER}" "mkdir -p ~/.ssh && echo '$pubKeyTrimmed' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys && echo 'SSH_KEY_OK'"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[x] SSH 连接失败，请检查密码和网络" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
Write-Host "[OK] 免密登录配置完成（后续无需再输入密码）" -ForegroundColor Green

# ─── 测试免密连接 ───────────────────────────────────────────
Write-Host "[3/6] 验证免密连接..." -ForegroundColor Yellow
$testResult = ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no "${USER}@${SERVER}" "echo connected" 2>&1
if ($testResult -match "connected") {
    Write-Host "[OK] 免密连接成功！" -ForegroundColor Green
} else {
    Write-Host "[!] 免密可能未生效，继续尝试..." -ForegroundColor Yellow
}

# ─── 上传文件 ───────────────────────────────────────────────
Write-Host "[4/6] 上传配置和脚本..." -ForegroundColor Yellow

# 创建远程目录
ssh -o StrictHostKeyChecking=no "${USER}@${SERVER}" "mkdir -p ${REMOTE_DIR}"

# 上传 .env
if (Test-Path "backend\.env") {
    scp -o StrictHostKeyChecking=no "backend\.env" "${USER}@${SERVER}:${REMOTE_DIR}/.env"
    Write-Host "  .env 已上传" -ForegroundColor Gray
} else {
    Write-Host "[x] backend\.env 不存在！请先配置" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

# 上传部署脚本
scp -o StrictHostKeyChecking=no "server-setup.sh" "${USER}@${SERVER}:${REMOTE_DIR}/server-setup.sh"
Write-Host "  server-setup.sh 已上传" -ForegroundColor Gray
Write-Host "[OK] 文件上传完成" -ForegroundColor Green

# ─── 执行远程部署 ───────────────────────────────────────────
Write-Host ""
Write-Host "[5/6] 执行远程部署（首次约5-10分钟）..." -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

ssh -o StrictHostKeyChecking=no "${USER}@${SERVER}" "bash ${REMOTE_DIR}/server-setup.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[x] 部署过程出错，请查看上方日志" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

# ─── 完成 ────────────────────────────────────────────────────
Write-Host ""
Write-Host "[6/6] 部署完成！" -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  访问地址: http://${SERVER}:8080" -ForegroundColor White
Write-Host "  管理账号: admin" -ForegroundColor White
Write-Host "  管理密码: admin123" -ForegroundColor White
Write-Host "" 
Write-Host "  阿里云安全组请放行 8080 端口" -ForegroundColor Yellow
Write-Host ""
Write-Host "  后续更新只需再次运行此脚本即可" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车退出"
