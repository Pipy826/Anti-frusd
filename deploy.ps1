# ============================================================
# Anti-fraud One-Click Deploy (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File deploy.ps1
# ============================================================

$SERVER = "8.139.255.130"
$USER = "root"
$REMOTE_DIR = "/opt/anti-fraud"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Anti-fraud Deploy" -ForegroundColor Cyan
Write-Host "  Server: $SERVER" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check backend\.env exists
if (-not (Test-Path "backend\.env")) {
    Write-Host "[FAIL] backend\.env not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Read public key
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa"
if (-not (Test-Path "$sshKeyPath.pub")) {
    Write-Host "[FAIL] SSH key not found. Run: ssh-keygen -t rsa -N ''" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
$pubKey = (Get-Content "$sshKeyPath.pub" -Raw).Trim()

# Build a single remote script that does everything
$envContent = (Get-Content "backend\.env" -Raw) -replace "'", "'\''"
$serverScript = (Get-Content "server-setup.sh" -Raw) -replace "'", "'\''"

# Create a combined script to minimize SSH connections
$remoteScript = @"
#!/bin/bash
set -e

# Setup SSH key
mkdir -p ~/.ssh
echo '$pubKey' >> ~/.ssh/authorized_keys
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Create project dir and write .env
mkdir -p $REMOTE_DIR
cat > $REMOTE_DIR/.env << 'ENVEOF'
$envContent
ENVEOF

# Add production fields if missing
grep -q "FRONTEND_PORT" $REMOTE_DIR/.env || echo "FRONTEND_PORT=8080" >> $REMOTE_DIR/.env
grep -q "JWT_SECRET" $REMOTE_DIR/.env || echo "JWT_SECRET=anti_fraud_prod_secret_2024_secure" >> $REMOTE_DIR/.env
grep -q "JWT_EXPIRE_HOURS" $REMOTE_DIR/.env || echo "JWT_EXPIRE_HOURS=72" >> $REMOTE_DIR/.env
grep -q "ADMIN_USERNAME" $REMOTE_DIR/.env || echo "ADMIN_USERNAME=admin" >> $REMOTE_DIR/.env
grep -q "ADMIN_PASSWORD" $REMOTE_DIR/.env || echo "ADMIN_PASSWORD=admin123" >> $REMOTE_DIR/.env

echo "ENV_READY"

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Install Docker Compose
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose..."
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
fi

# Install Git
if ! command -v git &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq git
fi

echo "DEPS_READY"

# Clone or update code
if [ -d "$REMOTE_DIR/.git" ]; then
    cd $REMOTE_DIR
    git fetch origin main
    git reset --hard origin/main
else
    rm -rf $REMOTE_DIR/.git
    cd $REMOTE_DIR
    git init
    git remote add origin https://github.com/Pipy826/Anti-frusd.git
    git fetch origin main
    git reset --hard origin/main
fi

echo "CODE_READY"

# Restore .env (git reset may have removed it)
cat > $REMOTE_DIR/.env << 'ENVEOF2'
$envContent
ENVEOF2
grep -q "FRONTEND_PORT" $REMOTE_DIR/.env || echo "FRONTEND_PORT=8080" >> $REMOTE_DIR/.env
grep -q "JWT_SECRET" $REMOTE_DIR/.env || echo "JWT_SECRET=anti_fraud_prod_secret_2024_secure" >> $REMOTE_DIR/.env
grep -q "JWT_EXPIRE_HOURS" $REMOTE_DIR/.env || echo "JWT_EXPIRE_HOURS=72" >> $REMOTE_DIR/.env
grep -q "ADMIN_USERNAME" $REMOTE_DIR/.env || echo "ADMIN_USERNAME=admin" >> $REMOTE_DIR/.env
grep -q "ADMIN_PASSWORD" $REMOTE_DIR/.env || echo "ADMIN_PASSWORD=admin123" >> $REMOTE_DIR/.env

# Build and start
cd $REMOTE_DIR
docker compose down 2>/dev/null || true
docker compose build
docker compose up -d

sleep 8
echo ""
echo "=== Container Status ==="
docker compose ps
echo ""
echo "DEPLOY_DONE"
echo "Access: http://8.139.255.130:8080"
echo "Admin: admin / admin123"
"@

Write-Host "Connecting to server..." -ForegroundColor Yellow
Write-Host "Enter password: T8y2x62006" -ForegroundColor Magenta
Write-Host "(Only needed ONCE - after this, key-based auth is configured)" -ForegroundColor Gray
Write-Host ""

# Write script to temp file and pipe it via SSH (single connection)
$tempFile = [System.IO.Path]::GetTempFileName()
$remoteScript | Set-Content -Path $tempFile -Encoding UTF8 -NoNewline

Get-Content $tempFile -Raw | ssh -o StrictHostKeyChecking=no "$USER@$SERVER" "bash -s"
$exitCode = $LASTEXITCODE

Remove-Item $tempFile -Force -ErrorAction SilentlyContinue

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[FAIL] Deploy error. Check logs above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DEPLOY COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "  URL: https://${SERVER}:8080" -ForegroundColor White
Write-Host "  (same link for PC and mobile)" -ForegroundColor Gray
Write-Host "  Admin: admin / admin123" -ForegroundColor White
Write-Host ""
Write-Host "  Open port 8080 in Alibaba Cloud Security Group" -ForegroundColor Yellow
Write-Host "  First visit shows cert warning - tap Advanced" -ForegroundColor Gray
Write-Host "  Re-run this script anytime to update." -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
