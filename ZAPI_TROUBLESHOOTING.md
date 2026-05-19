# 🔧 Troubleshooting Z-API — Agente Cobrança Renaissance

> Data: 18/05/2026
> Problema: Z-API retornando erro 400 (Bad Request)

---

## ❌ Erro atual

```
Status: 400 Bad Request
Endpoint: /status e /send-text
```

Isso significa que a **instância Z-API existe, mas o WhatsApp não está conectado**.

---

## ✅ Passo a passo para resolver

### 1. Acessar o painel Z-API

Abra no navegador:
```
https://z-api.io
```

Faça login com sua conta.

---

### 2. Localizar sua instância

No painel, procure a instância:
- **ID:** `3F3504716F44324E0D095EE982B712E3`
- **Token:** `EB69BCFE629B94E3AAC8D8E9`

---

### 3. Conectar o chip WhatsApp

1. No painel da instância, clique em **"Conectar"** ou **"QR Code"**
2. Vai aparecer um **QR Code** na tela
3. Abra o WhatsApp no celular
4. Vá em: **Configurações → Aparelhos conectados → Conectar aparelho**
5. Escaneie o QR Code
6. Aguarde a conexão (pode levar 30s)

---

### 4. Verificar se conectou

Depois de conectar, o status no painel deve mudar para:
```
"connected": true
"state": "CONNECTED"
```

---

### 5. Testar envio

Rode este comando no PowerShell pra testar:

```powershell
$headers = @{
    "Client-Token" = "EB69BCFE629B94E3AAC8D8E9"
    "Content-Type" = "application/json"
}
$body = @{
    phone = "5584991627655"
    message = "Teste Z-API — Agente Renaissance"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.z-api.io/instances/3F3504716F44324E0D095EE982B712E3/token/EB69BCFE629B94E3AAC8D8E9/send-text" -Method POST -Headers $headers -Body $body
```

Se retornar algo como:
```json
{
  "messageId": "...",
  "phone": "5584991627655",
  "zaapId": "..."
}
```

→ **Funcionou!** Pode fazer o deploy.

---

## 🔍 Outras causas possíveis do erro 400

| Causa | Como verificar | Solução |
|---|---|---|
| Chip não conectado | Painel Z-API mostra "Desconectado" | Conectar via QR Code |
| Client-Token errado | Comparar com painel | Copiar token correto do painel |
| Instância expirada | Verificar data de vencimento | Renovar assinatura (R$ 67/mês) |
| Número banido pelo WhatsApp | Tentar enviar mensagem manual | Usar outro chip |
| IP bloqueado | Testar de outra rede | Contatar suporte Z-API |

---

## 📞 Suporte Z-API

- **Site:** https://z-api.io
- **Email:** suporte@z-api.io
- **WhatsApp:** (11) 94320-3638
- **Documentação:** https://developer.z-api.io

---

## 🚀 Depois de conectar

1. Testar envio (comando acima)
2. Se funcionou: executar `deploy_aws.bat`
3. Acessar `http://IP_EC2:5000/dashboard`
4. Aprovar mensagens e enviar
