@echo off
chcp 65001 >nul
title 认知破壁机 V5.0 · 后端 API
cd /d "F:\cognitive-wallbreaker\backend"

echo ==========================================
echo   认知破壁机 V5.0 · Cognitive Wallbreaker
echo   多智能体对抗推演引擎
echo ==========================================
echo.
echo   API: http://localhost:8920
echo   Docs: http://localhost:8920/docs
echo   V5 Full (7 Agent): POST /api/simulate/v5
echo   V5 Fast (3 Agent): POST /api/simulate/v5/fast
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8920 --reload
pause
