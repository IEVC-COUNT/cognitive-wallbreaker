@echo off
chcp 65001 >nul
title 认知破壁机 V5.0 · Docker 停止
cd /d F:\cognitive-wallbreaker
docker compose down
echo.
echo 认知破壁机 V5.0 已停止
pause
