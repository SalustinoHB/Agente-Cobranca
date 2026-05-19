@echo off
chcp 65001 >nul
title 🔬 Teste Rápido - Agente Cobrança
cls

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║     🔬 TESTE RÁPIDO - AGENTE COBRANÇA          ║
echo ╠══════════════════════════════════════════════════╣
echo ║  1. Testar saudacao                             ║
echo ║  2. Testar "Já paguei"                          ║
echo ║  3. Testar "Manda 2ª via"                       ║
echo ║  4. Testar "Quero parcelar"                     ║
echo ║  5. Testar TUDO (7 intencoes)                   ║
echo ║  6. Rodar validacao completa                    ║
echo ║  7. Ver status da API                           ║
echo ║  8. Sair                                         ║
echo ╚══════════════════════════════════════════════════╝
echo.

set /p opcao=Digite o numero: 

cd /d "C:\Users\admin\Downloads\Serviço\09 - Agente Cobrança Renaissance"

if "%opcao%"=="1" python -c "import requests;d=requests.post('http://localhost:5005/api/webhook/zapi',json={'phone':'5584991627655','messageId':'TST','text':'Oi, tudo bem?','fromMe':False},timeout=30).json();print('RESPOSTA:',d.get('resposta_texto','(vazia)')[:200])"
if "%opcao%"=="2" python -c "import requests;d=requests.post('http://localhost:5005/api/webhook/zapi',json={'phone':'5584991627655','messageId':'TST','text':'Já paguei o boleto','fromMe':False},timeout=30).json();print('RESPOSTA:',d.get('resposta_texto','(vazia)')[:200])"
if "%opcao%"=="3" python -c "import requests;d=requests.post('http://localhost:5005/api/webhook/zapi',json={'phone':'5584991627655','messageId':'TST','text':'Manda a 2ª via do boleto','fromMe':False},timeout=30).json();print('PIX:',d.get('resposta_texto','(vazia)')[:200])"
if "%opcao%"=="4" python -c "import requests;d=requests.post('http://localhost:5005/api/webhook/zapi',json={'phone':'5584991627655','messageId':'TST','text':'Quero parcelar','fromMe':False},timeout=30).json();print('RESPOSTA:',d.get('resposta_texto','(vazia)')[:200])"
if "%opcao%"=="5" python teste_final.py
if "%opcao%"=="6" python teste_respostas_completo.py
if "%opcao%"=="7" python -c "import requests;r=requests.get('http://localhost:5005/',timeout=5).json();print(f'Servico: {r.get(\"servico\")}\nModo: {r.get(\"modo\")}')"

echo.
if not "%opcao%"=="8" pause
