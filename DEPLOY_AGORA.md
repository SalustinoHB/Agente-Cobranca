# 🚀 Deploy AGORA — 3 comandos no PowerShell

> **Status atual:** Servidor AWS criado, portas abertas, chave SSH baixada.
> **Falta:** Subir o Docker com Evolution no servidor (5-10 min).
> **Resultado final:** Evolution rodando, pronto pra receber o chip WhatsApp depois.

---

## ✅ Pré-condições (já estão prontas)

- ✅ Lightsail criado: `cobranca` (Ubuntu 24.04, 1GB RAM, 40GB SSD)
- ✅ IP público: **`32.197.47.159`**
- ✅ Portas abertas: 22 (SSH), 80 (HTTP), 5000 (API), 8080 (Evolution)
- ✅ Chave SSH baixada em: `C:\Users\admin\Downloads\LightsailDefaultKey-us-east-1.pem`
- ✅ Script de instalação pronto: `install_aws.sh` (nesta pasta)

---

## 🎯 Os 3 comandos

Abra o **PowerShell** (tecla Windows → digitar "powershell" → Enter) e cole **um por vez**:

### 📌 Comando 1: Proteger a chave SSH (1x só)

```powershell
icacls "C:\Users\admin\Downloads\LightsailDefaultKey-us-east-1.pem" /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

> Isso reduz as permissões da chave (SSH exige). Roda 1 vez só.

---

### 📌 Comando 2: Enviar o script pro servidor

```powershell
scp -o StrictHostKeyChecking=no -i "C:\Users\admin\Downloads\LightsailDefaultKey-us-east-1.pem" "C:\Users\admin\Downloads\Serviço\09 - Agente Cobrança Renaissance\install_aws.sh" ubuntu@32.197.47.159:~/
```

> Transfere `install_aws.sh` pro servidor.

---

### 📌 Comando 3: Conectar SSH e executar

```powershell
ssh -o StrictHostKeyChecking=no -i "C:\Users\admin\Downloads\LightsailDefaultKey-us-east-1.pem" ubuntu@32.197.47.159 "chmod +x install_aws.sh && bash install_aws.sh"
```

> Conecta no servidor e roda o script. **Demora 5-10 min** (instala Docker, sobe containers).

---

## ⏱️ O que vai acontecer

```
[1/6] Atualizando sistema...        (~1 min)
[2/6] Instalando Docker...          (~2 min)
[3/6] Criando swap...               (~30s)
[4/6] Criando estrutura...          (~5s)
[5/6] docker-compose.yml + tokens... (~5s)
[6/6] Subindo Evolution + Postgres + Redis... (~3 min)

✅ DEPLOY CONCLUÍDO!
```

Quando terminar, o script imprime os tokens gerados automaticamente. **GUARDE com cuidado** (cole num gerenciador de senhas).

---

## 🌐 Após o deploy: testar

Abra no navegador:

**http://32.197.47.159:8080/manager**

Vai pedir API Key — use a `EVOLUTION_API_KEY` que apareceu nos tokens.

Você verá o painel da Evolution. Crie uma instância chamada `cobranca-renaissance`. Quando o chip estiver pronto, você só escaneia o QR.

---

## 🚨 Se der erro

| Erro | Solução |
|---|---|
| "Permission denied (publickey)" | Comando 1 não foi rodado. Rode o comando 1 primeiro. |
| "ssh: connect to host 32.197.47.159 port 22: Connection refused" | Servidor não tá pronto. Espere 2 min e tenta de novo. |
| "scp: command not found" | OpenSSH não instalado. Vá em Configurações Windows → Apps → Recursos opcionais → instalar "OpenSSH Client". |
| Travou no `apt-get` | Aguarde — primeira vez demora. Não cancele. |

---

## 📋 Após "✅ DEPLOY CONCLUÍDO"

Ainda no terminal SSH, rode pra ver os tokens:

```bash
cat tokens.txt
```

Copie e me passa (ou guarde) os 3 valores:
- `EVOLUTION_API_KEY=...`
- `POSTGRES_PASSWORD=...`
- `API_TOKEN=...`

Esses vão pro `.env` quando subirmos o agente Python (fase 2).

---

## 🤔 E quando vou conectar o chip?

Quando quiser. O Evolution fica rodando esperando. Quando você decidir:

1. Abre `http://32.197.47.159:8080/manager`
2. Cria instância "cobranca-renaissance" (se não criou)
3. Clica em **QR Code**
4. No celular com o chip:
   - WhatsApp → ⋮ → Aparelhos conectados → Conectar um aparelho
   - Escaneia o QR
5. Pronto — chip conectado

Depois disso, posso adicionar o agente Python pra rodar a régua automática.

---

## 💰 Custo

Lembrete: **90 dias grátis no plano $7**. Depois disso, ~R$ 40-45/mês (instância + transferência + chip pré-pago).

---

*Atualizado: 12/05/2026*
