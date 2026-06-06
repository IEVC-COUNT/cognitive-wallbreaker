@echo off
chcp 65001 >nul
title 认知破壁机 · 前端
cd /d "F:\cognitive-wallbreaker\frontend"

echo ==========================================
echo   认知破壁机 · Cognitive Wallbreaker
echo   前端启动中...
echo ==========================================
echo.
echo   首次运行请先执行: npm install
echo   前端: http://localhost:3000
echo.

npm run dev
pause
