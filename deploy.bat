@echo off
:: Anti-fraud 一键部署 - 启动器
:: 双击此文件即可开始部署
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
