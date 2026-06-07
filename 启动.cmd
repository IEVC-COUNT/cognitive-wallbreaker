@echo off
chcp 65001 >nul
title 认知破壁机 V5.0 · Docker 启动
cd /d F:\cognitive-wallbreaker
docker compose up -d
echo.
echo 认知破壁机 V5.0 已启动
echo 前端: http://localhost:3000
echo 后端: http://localhost:8920
pause
