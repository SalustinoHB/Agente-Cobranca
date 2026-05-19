# 🔍 Diagnóstico Z-API — Erro 400

> Data: 18/05/2026

## ❌ Problema

A Z-API retorna **erro 400 (Bad Request)** ao tentar acessar qualquer endpoint.

## 🔬 Testes realizados

### Teste 1: URL com token na URL + Client-Token no header
```
GET https://api.z-api.io/instances/3F3504716F44324E0D095EE982B712E3/token/EB69BCFE629B94E3AAC8D8E9/status
Header: Client-Token: EB69BCFE629B94E3AAC8D8E9
```
**Resultado:** ❌ 400 Bad Request

### Teste 2: URL SEM token na URL + Client-Token no header
```
GET https://api.z-api.io/instances/3F3504716F44324E0D095EE982B712E3/status
Header: Client-Token: EB69BCFE629B94E3AAC8D8E9
```
**Resultado:** ⚠️ 200 OK, mas retorna `{"error":"NOT_FOUND"}`

### Teste 3: URL com token na URL SEM header
```
GET https://api.z-api.io/instances/3F3504716F44324E0D095EE982B712E3/token/EB69BCFE629B94E3AAC8D8E9/status
```
**Resultado:** ❌ 400 Bad Request

## 🎯 Conclusão

O **token na URL está causando o erro 400**. Quando removemos o token da URL e usamos apenas no header, a API responde (embora diga NOT_FOUND).

## 🔧 Possíveis causas

1. **Token incorreto:** O token `EB69BCFE629B94E3AAC8D8E9` pode não ser o token de API correto
2. **Instância em outro servidor:** A instância pode estar em `api.z-api.io` ou outro subdomínio
3. **Token expirado:** O token pode ter expirado ou sido revogado
4. **Instância não ativada:** A instância pode precisar de ativação no painel

## ✅ O que precisa verificar no painel Z-API

Acesse https://app.z-api.io e verifique:

1. **O token está correto?** No painel, vá em:
   - Instâncias → clique na instância "cobranca"
   - Verifique se o token mostrado é exatamente: `EB69BCFE629B94E3AAC8D8E9`

2. **Há um "Token de API" diferente?** Algumas versões da Z-API usam:
   - "Client Token" (para o header)
   - "API Token" ou "Instance Token" (para a URL)

3. **A instância está ativa?** Verifique se:
   - Status está "Conectada" ✅
   - Não há mensagens de erro no painel
   - A assinatura está paga

4. **Qual é a URL base correta?** No painel, procure por:
   - "URL da API" ou "Endpoint"
   - Pode ser algo como: `https://api.z-api.io/instances/ID/token/TOKEN`
   - Ou: `https://api.z-api.io/v1/instances/ID/...`

## 📞 Contato suporte Z-API

Se não conseguir resolver, entre em contato:
- WhatsApp: (11) 94320-3638
- Email: suporte@z-api.io
