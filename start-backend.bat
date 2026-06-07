@echo off
chcp 65001 >nul
title 认知破壁机 V6.0 · 后端 API
cd /d "F:\cognitive-wallbreaker\backend"

echo ==========================================
echo   认知破壁机 V6.0 · Cognitive Wallbreaker
echo   公共个人决策推演平台
echo ==========================================
echo.
echo   API: http://localhost:8920
echo   Docs: http://localhost:8920/docs
echo   Public Submit: POST /api/public/submit
echo   Public Events: GET /api/public/events
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8920 --reload
pause
