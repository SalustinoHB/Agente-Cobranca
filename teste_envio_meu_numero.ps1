# Script de teste - Envio Z-API para seu número
# Uso: .\teste_envio_meu_numero.ps1

$instance = "3F3504716F44324E0D095EE982B712E3"
$instanceToken = "EB69BCFE629B94E3AAC8D8E9"
$clientToken = "F45886bf7d2c54c2385c46c92e3c5c259S"
$base = "https://api.z-api.io/instances/$instance/token/$instanceToken"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TESTE Z-API - Seu Número" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Seu número
$meuNumero = "5584991627655"

# Mensagem de teste
$mensagem = @"
🧪 *TESTE Z-API - Agente Renaissance*

Este é um teste do sistema de cobrança.

Se você recebeu esta mensagem, a Z-API está funcionando perfeitamente! ✅

---
Pratika Administradora
"@

Write-Host "Enviando mensagem de teste para seu número ($meuNumero)..." -ForegroundColor Cyan
Write-Host ""

try {
    $body = @{
        phone = $meuNumero
        message = $mensagem
        delayMessage = 1
    } | ConvertTo-Json
    
    $r = Invoke-WebRequest -Uri "$base/send-text" -Method POST `
        -Headers @{"Client-Token"=$clientToken; "Content-Type"="application/json"} `
        -Body $body -UseBasicParsing
    
    $resp = $r.Content | ConvertFrom-Json
    Write-Host "✅ MENSAGEM ENVIADA COM SUCESSO!" -ForegroundColor Green
    Write-Host "   ID: $($resp.messageId)" -ForegroundColor Green
    Write-Host "   ZaapID: $($resp.zaapId)" -ForegroundColor Green
} catch {
    Write-Host "❌ ERRO AO ENVIAR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        Write-Host "   Resposta: $($reader.ReadToEnd())" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verifique seu WhatsApp!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
