@echo off
chcp 65001 >nul
title 🔥 AGENTE RENAISSANCE - MODO WHATSAPP
cls

echo.
echo  🔥 INICIANDO SISTEMA PARA TESTE NO WHATSAPP
echo  =============================================
echo.

cd /d "C:\Users\admin\Downloads\Serviço\09 - Agente Cobrança Renaissance"

echo [1/3] Matando processos antigos...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo   OK

echo [2/3] Subindo API local...
start "API" /MIN "" "C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn agente.api:app --host 0.0.0.0 --port 5005
timeout /t 5 /nobreak >nul
echo   ✅ API rodando em http://localhost:5005

echo [3/3] Conectando tunel publico...
echo   O tunel ja esta rodando em outro terminal.
echo   URL: https://3df56c3c989c4a.lhr.life

cls
echo.
echo  ============================================
echo   ✅ SISTEMA PRONTO!
echo  ============================================
echo.
echo   📡 API:     http://localhost:5005
echo   📡 PAINEL:  http://localhost:5005/dashboard
echo.
echo   🔗 WEBHOOK Z-API:
echo   https://3df56c3c989c4a.lhr.life/api/webhook/zapi
echo.
echo   📋 PASSOS:
echo     1. Acesse https://app.z-api.io
echo     2. Login: thaynan.pipoca@useorbio.com
echo     3. Instancias > cobranca > Webhooks
echo     4. Cole a URL em "Ao receber"
echo     5. Salve
echo     6. Envie "Oi" pro chip
echo.
echo   PRESSIONE QUALQUER TECLA PRA ABRIR O PAINEL
pause >nul
start http://localhost:5005/dashboard
