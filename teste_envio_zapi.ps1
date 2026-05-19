# Script de teste - Envio Z-API para contatos Renaissance
# Uso: .\teste_envio_zapi.ps1

$instance = "3F3504716F44324E0D095EE982B712E3"
$instanceToken = "EB69BCFE629B94E3AAC8D8E9"
$clientToken = "F45886bf7d2c54c2385c46c92e3c5c259S"
$base = "https://api.z-api.io/instances/$instance/token/$instanceToken"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TESTE Z-API - Agente Renaissance" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Carregar dados
$json = Get-Content -Path "agente/data/renaissance.json" -Raw | ConvertFrom-Json
$boletos = $json.boletos | Where-Object { $_.status -ne "pago" -and $_.whatsapp -ne $null }

Write-Host "Inadimplentes com WhatsApp: $($boletos.Count)" -ForegroundColor Yellow
Write-Host ""

# Perguntar quantos enviar
$quantidade = Read-Host "Quantos envios de teste? (1-$($boletos.Count), ou 0 para cancelar)"

if ($quantidade -eq "0") {
    Write-Host "Cancelado." -ForegroundColor Red
    exit
}

$limite = [Math]::Min([int]$quantidade, $boletos.Count)

# Enviar mensagens
for ($i = 0; $i -lt $limite; $i++) {
    $boleto = $boletos[$i]
    $nome = $boleto.nome
    $whatsapp = $boleto.whatsapp
    $unidade = $boleto.unidade
    $valor = $boleto.valor
    $dias = $boleto.dias_atraso
    
    $mensagem = @"
Oi, tudo bem?

Sou da Pratika Administradora do Condomínio Renaissance.

Verificamos que o boleto do apartamento $unidade está com $dias dias de atraso. Valor: R$ $valor,00.

Se precisar de 2ª via ou quiser negociar, pode me chamar por aqui.

Obrigado!
"@
    
    Write-Host "[$($i+1)/$limite] Enviando para $nome ($whatsapp)..." -ForegroundColor Cyan
    
    try {
        $body = @{
            phone = $whatsapp
            message = $mensagem
            delayMessage = 2
        } | ConvertTo-Json
        
        $r = Invoke-WebRequest -Uri "$base/send-text" -Method POST `
            -Headers @{"Client-Token"=$clientToken; "Content-Type"="application/json"} `
            -Body $body -UseBasicParsing
        
        $resp = $r.Content | ConvertFrom-Json
        Write-Host "  ✅ Enviado! ID: $($resp.messageId)" -ForegroundColor Green
        
        # Aguardar 3 segundos entre envios
        if ($i -lt $limite - 1) {
            Start-Sleep -Seconds 3
        }
    } catch {
        Write-Host "  ❌ Erro: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TESTE CONCLUÍDO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
