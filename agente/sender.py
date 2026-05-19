"""
sender.py — Senders polimórficos pra mensageria WhatsApp.

Backends suportados:
  - BaileysSender   → POST pra servidor Baileys local/AWS
  - ZAPISender      → POST pra Z-API
  - EvolutionSender → Evolution API (legado, mantido por compat)
  - DryRunSender    → não envia, só logga + escreve em data/dryrun_log.jsonl

Todos compartilham a mesma interface BaseSender. Use `make_sender()`
pra construir o backend correto via .env (SENDER_TYPE).

Forma de retorno padrão de `enviar_texto()`:
    {
        "sucesso": bool,
        "message_id": str | None,
        "erro": str | None,
        "raw_response": dict
    }
"""

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from loguru import logger


# ============================================================
# BASE
# ============================================================
class BaseSender:
    """
    Interface comum para todos os senders.

    Subclasses devem implementar:
      - status_instancia() -> dict
      - esta_conectado() -> bool
      - enviar_texto(numero_whatsapp, texto, delay_ms) -> dict
    """

    nome_backend: str = "base"
    dry_run: bool = False

    def status_instancia(self) -> dict:
        raise NotImplementedError

    def esta_conectado(self) -> bool:
        raise NotImplementedError

    def enviar_texto(
        self,
        numero_whatsapp: str,
        texto: str,
        delay_ms: int = 1200,
    ) -> dict:
        raise NotImplementedError

    # ─── Util compartilhado ───
    @staticmethod
    def normalizar_numero(whatsapp: str) -> str:
        """
        Normaliza pra formato 13 dígitos: 5584999999999

        Aceita:
          - +55 84 99999-9999
          - (84) 99999-9999
          - 5584999999999
          - 84999999999
        """
        numero = re.sub(r"\D", "", whatsapp)
        numero = numero.lstrip("0")

        if len(numero) == 11:
            numero = "55" + numero
        elif len(numero) == 10:
            numero = "55" + numero
        elif len(numero) == 13 and numero.startswith("55"):
            pass
        elif len(numero) == 12 and numero.startswith("55"):
            numero = numero[:4] + "9" + numero[4:]
        else:
            logger.warning(f"Número com formato suspeito: '{whatsapp}' -> '{numero}'")

        return numero


# ============================================================
# BAILEYS
# ============================================================
class BaileysSender(BaseSender):
    """
    Cliente HTTP para um servidor Baileys (Node) self-hosted.

    Espera endpoints:
      GET  {base_url}/status            -> {"connected": bool, ...}
      POST {base_url}/api/send          -> body {"number": "...", "text": "..."}

    Autenticação: header `X-Api-Key`.
    """

    nome_backend = "baileys"

    def __init__(self, base_url: str, api_key: str, dry_run: bool = False):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dry_run = dry_run

        if self.dry_run:
            logger.warning("BaileysSender em DRY-RUN (não envia mensagens reais)")

    def _headers(self) -> dict:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def status_instancia(self) -> dict:
        url = f"{self.base_url}/status"
        try:
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Erro status Baileys: {e}")
            return {"connected": False, "erro": str(e)}

    def esta_conectado(self) -> bool:
        try:
            status = self.status_instancia()
            # Baileys padrão devolve {"connected": true}
            return bool(status.get("connected"))
        except Exception as e:
            logger.error(f"Erro ao checar conexão Baileys: {e}")
            return False

    def enviar_texto(
        self,
        numero_whatsapp: str,
        texto: str,
        delay_ms: int = 1200,
    ) -> dict:
        if self.dry_run:
            logger.info(f"[DRY-RUN/Baileys] NÃO enviado pra {numero_whatsapp}")
            return {
                "sucesso": True,
                "message_id": f"DRYRUN-{int(time.time())}",
                "erro": None,
                "raw_response": {"dry_run": True, "backend": "baileys"},
            }

        numero = self.normalizar_numero(numero_whatsapp)
        url = f"{self.base_url}/api/send"
        payload = {
            "number": numero,
            "text": texto,
            "delay": delay_ms,
        }

        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            r.raise_for_status()
            data = r.json()

            message_id = (
                data.get("key", {}).get("id")
                or data.get("messageId")
                or data.get("id")
            )
            logger.success(f"[Baileys] Enviado pra {numero_whatsapp} ({message_id})")
            return {
                "sucesso": True,
                "message_id": message_id,
                "erro": None,
                "raw_response": data,
            }
        except requests.HTTPError as e:
            erro = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"[Baileys] Falha pra {numero_whatsapp}: {erro}")
            return {
                "sucesso": False,
                "message_id": None,
                "erro": erro,
                "raw_response": {"erro": str(e)},
            }
        except Exception as e:
            logger.error(f"[Baileys] Erro inesperado pra {numero_whatsapp}: {e}")
            return {
                "sucesso": False,
                "message_id": None,
                "erro": str(e),
                "raw_response": {"erro": str(e)},
            }


# ============================================================
# Z-API
# ============================================================
class ZAPISender(BaseSender):
    """
    Cliente Z-API (https://z-api.io).

    URL no padrão: https://api.z-api.io/instances/{INSTANCE}/token/{TOKEN}
    Endpoints usados:
      GET  {instance_url}/status                  -> {"connected": bool}
      POST {instance_url}/send-text               -> body {"phone": "...", "message": "..."}

    O Z-API pede `Client-Token` (a "Token de Segurança da Conta") no header.
    """

    nome_backend = "zapi"

    def __init__(
        self,
        instance_url: str,
        client_token: str = "",
        dry_run: bool = False,
    ):
        self.instance_url = instance_url.rstrip("/")
        self.client_token = client_token
        self.dry_run = dry_run

        if self.dry_run:
            logger.warning("ZAPISender em DRY-RUN (não envia mensagens reais)")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.client_token:
            h["Client-Token"] = self.client_token
        return h

    def status_instancia(self) -> dict:
        url = f"{self.instance_url}/status"
        try:
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Erro status Z-API: {e}")
            return {"connected": False, "erro": str(e)}

    def esta_conectado(self) -> bool:
        try:
            status = self.status_instancia()
            return bool(status.get("connected"))
        except Exception as e:
            logger.error(f"Erro ao checar conexão Z-API: {e}")
            return False

    def enviar_texto(
        self,
        numero_whatsapp: str,
        texto: str,
        delay_ms: int = 1200,
    ) -> dict:
        """
        Envia mensagem via Z-API com delay natural e retry.
        
        Inspirado nos agentes de captação (messenger.py / whatsapp.py):
        - Delay de digitação humano (1200ms padrão, configurável)
        - Retry automático em caso de falha transitória
        - Logging detalhado
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN/Z-API] NÃO enviado pra {numero_whatsapp}")
            return {
                "sucesso": True,
                "message_id": f"DRYRUN-{int(time.time())}",
                "erro": None,
                "raw_response": {"dry_run": True, "backend": "zapi"},
            }

        # Verifica conexão antes de enviar (padrão dos outros agentes)
        if not self.esta_conectado():
            logger.warning("[Z-API] WhatsApp desconectado — cancelando envio")
            return {
                "sucesso": False,
                "message_id": None,
                "erro": "WhatsApp desconectado no painel Z-API",
                "raw_response": {"erro": "disconnected"},
            }

        numero = self.normalizar_numero(numero_whatsapp)
        url = f"{self.instance_url}/send-text"
        # Z-API tem delayMessage em segundos
        payload = {
            "phone": numero,
            "message": texto,
            "delayMessage": max(1, int(delay_ms / 1000)),
        }

        # Retry com backoff (até 3 tentativas)
        max_retries = 3
        for tentativa in range(1, max_retries + 1):
            try:
                r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
                r.raise_for_status()
                data = r.json()

                message_id = data.get("messageId") or data.get("id") or data.get("zaapId")
                logger.success(
                    f"[Z-API] Enviado pra {numero_whatsapp} ({message_id}) "
                    f"— delay={delay_ms}ms | tentativa={tentativa}"
                )
                return {
                    "sucesso": True,
                    "message_id": message_id,
                    "erro": None,
                    "raw_response": data,
                }
            except requests.HTTPError as e:
                status = e.response.status_code
                erro = f"HTTP {status}: {e.response.text[:200]}"
                
                # Retry em 429 (rate limit) ou 5xx (erro servidor)
                if status in (429, 500, 502, 503, 504) and tentativa < max_retries:
                    wait = tentativa * 2  # backoff exponencial
                    logger.warning(
                        f"[Z-API] Falha {status} (tentativa {tentativa}/{max_retries}) — "
                        f"aguardando {wait}s antes de retry..."
                    )
                    time.sleep(wait)
                    continue
                
                logger.error(f"[Z-API] Falha definitiva pra {numero_whatsapp}: {erro}")
                return {
                    "sucesso": False,
                    "message_id": None,
                    "erro": erro,
                    "raw_response": {"erro": str(e)},
                }
            except Exception as e:
                if tentativa < max_retries:
                    wait = tentativa * 2
                    logger.warning(
                        f"[Z-API] Erro (tentativa {tentativa}/{max_retries}): {e} — "
                        f"retry em {wait}s..."
                    )
                    time.sleep(wait)
                    continue
                
                logger.error(f"[Z-API] Erro inesperado pra {numero_whatsapp}: {e}")
                return {
                    "sucesso": False,
                    "message_id": None,
                    "erro": str(e),
                    "raw_response": {"erro": str(e)},
                }


# ============================================================
# EVOLUTION (legado)
# ============================================================
class EvolutionSender(BaseSender):
    """
    Cliente Evolution API (mantido para compat).

    URL no padrão: http://evolution:8080
    Endpoints usados:
      GET  {base_url}/instance/connectionState/{instance}
      POST {base_url}/message/sendText/{instance}
    """

    nome_backend = "evolution"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        instance: str,
        dry_run: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance
        self.dry_run = dry_run

        if self.dry_run:
            logger.warning("EvolutionSender em DRY-RUN (não envia mensagens reais)")

    def _headers(self) -> dict:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def status_instancia(self) -> dict:
        url = f"{self.base_url}/instance/connectionState/{self.instance}"
        try:
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Erro status Evolution: {e}")
            return {"instance": {"state": "closed"}, "erro": str(e)}

    def esta_conectado(self) -> bool:
        try:
            status = self.status_instancia()
            return status.get("instance", {}).get("state") == "open"
        except Exception as e:
            logger.error(f"Erro ao checar conexão Evolution: {e}")
            return False

    def enviar_texto(
        self,
        numero_whatsapp: str,
        texto: str,
        delay_ms: int = 1200,
    ) -> dict:
        if self.dry_run:
            logger.info(f"[DRY-RUN/Evolution] NÃO enviado pra {numero_whatsapp}")
            logger.info(f"[DRY-RUN/Evolution] Texto:\n{texto}\n")
            return {
                "sucesso": True,
                "message_id": f"DRYRUN-{int(time.time())}",
                "erro": None,
                "raw_response": {"dry_run": True, "backend": "evolution"},
            }

        numero_e164 = self.normalizar_numero(numero_whatsapp)
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": f"{numero_e164}@s.whatsapp.net",
            "text": texto,
            "delay": delay_ms,
        }

        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            r.raise_for_status()
            data = r.json()

            message_id = (
                data.get("key", {}).get("id")
                or data.get("messageId")
                or data.get("id")
            )
            logger.success(f"[Evolution] Enviado pra {numero_whatsapp} ({message_id})")
            return {
                "sucesso": True,
                "message_id": message_id,
                "erro": None,
                "raw_response": data,
            }
        except requests.HTTPError as e:
            erro = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"[Evolution] Falha pra {numero_whatsapp}: {erro}")
            return {
                "sucesso": False,
                "message_id": None,
                "erro": erro,
                "raw_response": {"erro": str(e)},
            }
        except Exception as e:
            logger.error(f"[Evolution] Erro inesperado pra {numero_whatsapp}: {e}")
            return {
                "sucesso": False,
                "message_id": None,
                "erro": str(e),
                "raw_response": {"erro": str(e)},
            }


# ============================================================
# DRY-RUN
# ============================================================
class DryRunSender(BaseSender):
    """
    Sender que NUNCA envia. Apenas logga e grava em data/dryrun_log.jsonl.

    Útil pra testes E2E e modo de revisão antes de produção.
    """

    nome_backend = "dryrun"
    dry_run = True

    def __init__(self, log_path: str = "./data/dryrun_log.jsonl"):
        self.log_path = Path(log_path)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"DryRunSender: não consegui criar pasta de log: {e}")
        logger.warning(f"DryRunSender ativo — logs em {self.log_path}")

    def status_instancia(self) -> dict:
        return {"backend": "dryrun", "connected": True, "fake": True}

    def esta_conectado(self) -> bool:
        return True

    def _gravar_log(self, entry: dict):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"DryRunSender: falha gravando log: {e}")

    def enviar_texto(
        self,
        numero_whatsapp: str,
        texto: str,
        delay_ms: int = 1200,
    ) -> dict:
        msg_id = f"DRYRUN-{int(time.time() * 1000)}"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "numero": numero_whatsapp,
            "numero_normalizado": self.normalizar_numero(numero_whatsapp),
            "texto": texto,
            "delay_ms": delay_ms,
            "message_id": msg_id,
        }
        self._gravar_log(entry)

        logger.info(f"[DRY-RUN] -> {numero_whatsapp} ({len(texto)} chars) [{msg_id}]")
        return {
            "sucesso": True,
            "message_id": msg_id,
            "erro": None,
            "raw_response": {"dry_run": True, "backend": "dryrun", "log": str(self.log_path)},
        }


# ============================================================
# FACTORY
# ============================================================
def make_sender(sender_type: Optional[str] = None) -> BaseSender:
    """
    Constrói o sender adequado lendo .env.

    Variável: SENDER_TYPE = baileys | zapi | evolution | dryrun
    Default: dryrun (mais seguro).

    Cada backend lê suas próprias variáveis de configuração.
    """
    sender_type = (sender_type or os.getenv("SENDER_TYPE", "dryrun")).strip().lower()
    enviar_de_verdade = os.getenv("ENVIAR_DE_VERDADE", "false").lower() == "true"
    dry_run_flag = not enviar_de_verdade

    if sender_type == "baileys":
        return BaileysSender(
            base_url=os.getenv("BAILEYS_URL", "http://localhost:3000"),
            api_key=os.getenv("BAILEYS_API_KEY", ""),
            dry_run=dry_run_flag,
        )

    if sender_type == "zapi":
        return ZAPISender(
            instance_url=os.getenv("ZAPI_INSTANCE_URL", ""),
            client_token=os.getenv("ZAPI_TOKEN", ""),
            dry_run=dry_run_flag,
        )

    if sender_type == "evolution":
        return EvolutionSender(
            base_url=os.getenv("EVOLUTION_URL", "http://evolution:8080"),
            api_key=os.getenv("EVOLUTION_API_KEY", ""),
            instance=os.getenv("EVOLUTION_INSTANCE", "cobranca-renaissance"),
            dry_run=dry_run_flag,
        )

    if sender_type == "dryrun":
        return DryRunSender(
            log_path=os.getenv("DRYRUN_LOG_PATH", "./data/dryrun_log.jsonl"),
        )

    logger.warning(f"SENDER_TYPE desconhecido: '{sender_type}' — caindo em DryRunSender")
    return DryRunSender()


# ─── Test rápido ───
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    sender = make_sender()
    print(f"Backend: {sender.nome_backend} | dry_run={sender.dry_run}")
    print("Status:", sender.status_instancia())

    # Teste normalização
    testes = [
        "+55 84 99999-9999",
        "(84) 99999-9999",
        "84999999999",
        "5584999999999",
        "84 9 9999-9999",
    ]
    for t in testes:
        print(f"  {t!r:30} -> {BaseSender.normalizar_numero(t)}")
