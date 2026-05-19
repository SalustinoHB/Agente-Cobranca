"""
webhook.py — Receptor de webhooks Z-API + auto-responder.

Endpoints:
  POST /api/webhook/zapi          — recebe payload do Z-API ("On message received")
  GET  /api/webhook/zapi/test     — testa o fluxo manualmente (?phone=...&texto=...)
  GET  /api/webhook/conversas     — últimas conversas (mensagens recebidas + resposta auto)

Política:
  - Ignora mensagens próprias (fromMe=true) e mensagens de grupo (isGroup=true).
  - Idempotente por messageId — não processa mesma msg 2x.
  - Defensivo: qualquer erro vira log + 200 OK (não estoura 500 pro Z-API,
    senão Z-API começa a retentar e enche o log).
  - Configurável quem responde via env WEBHOOK_RESPONDER_AUTO_AO:
      "todos"           → responde a qualquer número (default)
      "so_inadimplentes"→ só responde se número está na base de inadimplentes
      "whitelist"       → só responde números listados em WEBHOOK_WHITELIST
"""

from __future__ import annotations

import os
import re
import json
import random
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from loguru import logger

from pathlib import Path

from agente.state import State
from agente.sender import make_sender
from agente.respostas_auto import classificar_e_responder
from agente import respostas as respostas_v2  # nova api (classificar/gerar_resposta)
from agente import comprovantes as comp
from agente.escalacao import escalar_humano
from agente import superlogica_boleto  # busca PIX/linha digitável no Superlógica
from agente.conversa_memoria import (
    ConversaMemory,
    ajustar_classificacao_por_contexto,
    gerar_resposta_sem_alerta,
)
from agente.respostas_engine import gerar_resposta_personalizada


router = APIRouter(prefix="/api/webhook", tags=["webhook"])


# ─── Config ───
DB_PATH = os.getenv("DATABASE_PATH", "/data/state.db")
BASE_PATH = os.getenv("BASE_JSON_PATH", "/data/renaissance.json")
COMPROVANTES_TMP = os.getenv("COMPROVANTES_TMP_DIR", "/data/comprovantes_tmp")
RESPOSTAS_AUTO_HABILITADAS = (
    os.getenv("RESPOSTAS_AUTO_HABILITADAS", "true").strip().lower() == "true"
)


def _politica_resposta() -> str:
    """Retorna a política configurada: todos | so_inadimplentes | whitelist."""
    return (os.getenv("WEBHOOK_RESPONDER_AUTO_AO", "todos") or "todos").strip().lower()


def _whitelist() -> set[str]:
    raw = os.getenv("WEBHOOK_WHITELIST", "") or ""
    return {n.strip() for n in raw.split(",") if n.strip()}


def _normalizar_phone(phone: str) -> str:
    """Tira tudo que não é dígito."""
    return "".join(c for c in (phone or "") if c.isdigit())


def _carregar_contexto_inadimplente(phone: str) -> Optional[dict]:
    """
    Procura na base de boletos o registro do número informado.
    Retorna o boleto (com valor/vencimento/dias_atraso) ou None se não achou.
    """
    try:
        with open(BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.debug(f"[webhook] base de boletos não disponível: {e}")
        return None

    phone_norm = _normalizar_phone(phone)
    for b in data.get("boletos", []):
        b_phone = _normalizar_phone(b.get("whatsapp", "") or "")
        if b_phone and b_phone.endswith(phone_norm[-11:]):
            return b
    return None


def _deve_responder(phone: str, contexto: Optional[dict]) -> bool:
    """Aplica a política WEBHOOK_RESPONDER_AUTO_AO."""
    politica = _politica_resposta()

    if politica == "todos":
        return True

    if politica == "so_inadimplentes":
        return contexto is not None

    if politica == "whitelist":
        wl = _whitelist()
        phone_norm = _normalizar_phone(phone)
        for w in wl:
            w_norm = _normalizar_phone(w)
            if w_norm and (w_norm == phone_norm or phone_norm.endswith(w_norm[-11:])):
                return True
        return False

    logger.warning(f"[webhook] política '{politica}' desconhecida — default=todos")
    return True


def _extrair_anexos(payload: dict) -> list[dict]:
    """
    Detecta anexos (imagem/documento) no payload Z-API.

    Z-API tipicamente manda:
      payload["image"] = {"imageUrl": "...", "caption": "..."}
      payload["document"] = {"documentUrl": "...", "fileName": "..."}
      payload["audio"] = {"audioUrl": "..."}

    Returns:
        Lista de {"tipo": "image|document|audio", "url": str,
                  "filename": str, "caption": str}
    """
    out = []
    if not isinstance(payload, dict):
        return out

    img = payload.get("image")
    if isinstance(img, dict):
        url = img.get("imageUrl") or img.get("url") or img.get("downloadUrl")
        if url:
            out.append({
                "tipo": "image",
                "url": url,
                "filename": img.get("fileName") or "imagem.jpg",
                "caption": img.get("caption") or "",
            })

    doc = payload.get("document")
    if isinstance(doc, dict):
        url = doc.get("documentUrl") or doc.get("url") or doc.get("downloadUrl")
        if url:
            out.append({
                "tipo": "document",
                "url": url,
                "filename": doc.get("fileName") or doc.get("title") or "documento.pdf",
                "caption": doc.get("caption") or "",
            })

    aud = payload.get("audio")
    if isinstance(aud, dict):
        url = aud.get("audioUrl") or aud.get("url")
        if url:
            out.append({
                "tipo": "audio",
                "url": url,
                "filename": aud.get("fileName") or "audio.ogg",
                "caption": "",
            })

    return out


def _processar_anexo_comprovante(
    phone: str,
    anexo: dict,
    contexto: Optional[dict],
    state: State,
) -> dict:
    """
    Baixa o anexo, roda OCR + validacao, salva evidencia + registra no banco.
    Retorna dict com resumo da operacao.
    """
    resumo = {
        "anexo_url": anexo.get("url"),
        "tipo": anexo.get("tipo"),
        "validacao": None,
        "salvo_em": None,
        "erro": None,
    }
    try:
        tmp_dir = Path(COMPROVANTES_TMP) / re.sub(r"\D", "", phone or "x")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Detecta extensao a partir da URL/filename
        nome_orig = anexo.get("filename") or "anexo"
        ext = Path(nome_orig).suffix.lower() or ""
        if not ext:
            # vai ser corrigido pelo content-type dentro de baixar_anexo
            ext = ".bin"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        tmp_path = tmp_dir / f"{ts}{ext}"

        arquivo = comp.baixar_anexo(anexo["url"], tmp_path)

        # Roda validacao OCR
        validacao = comp.validar_comprovante(arquivo, contexto or {})
        resumo["validacao"] = validacao

        # Move pra pasta definitiva + registra
        boleto_id = None
        if contexto:
            boleto_id = (
                contexto.get("id")
                or contexto.get("boleto_id")
                or contexto.get("recibo_id")
            )

        destino = comp.salvar_evidencia(
            arquivo=arquivo,
            telefone=phone,
            intent="comprovante",
            validacao=validacao,
            state=state,
            boleto_id_associado=str(boleto_id) if boleto_id else None,
        )
        resumo["salvo_em"] = str(destino)
    except Exception as e:
        logger.exception(f"[webhook/anexo] erro processando anexo: {e}")
        resumo["erro"] = str(e)
    return resumo


def _extrair_texto(payload: dict) -> str:
    """
    Z-API manda o texto em diferentes campos dependendo do tipo:
      - texto comum:   payload["text"]["message"]
      - às vezes:      payload["message"]
      - às vezes:      payload["body"]
    """
    if not payload:
        return ""

    text_obj = payload.get("text")
    if isinstance(text_obj, dict):
        msg = text_obj.get("message")
        if msg:
            return str(msg)
    if isinstance(text_obj, str):
        return text_obj

    for k in ("message", "body", "messageText"):
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v

    return ""


# ─── Pipeline central ───
def _processar(
    phone: str,
    texto: str,
    sender_name: Optional[str],
    message_id: str,
    state: State,
    anexos: Optional[list[dict]] = None,
) -> dict:
    """
    Pipeline reutilizado pelo webhook real e pelo /test:
      1. idempotência (mesmo message_id 2x = ignora)
      2. processa anexos (baixa, OCR, valida, salva) se houver
      3. classifica intent (novo modulo respostas.py se houver anexo,
         senao usa respostas_auto.classificar_e_responder)
      4. envia resposta (se cabível pela politica)
      5. escala humano (acordo/reclamacao/comprovante_invalido/desconhecida)
      6. registra tudo no SQLite (mensagens_recebidas + conversas)
    """
    anexos = anexos or []
    resumo = {
        "message_id": message_id,
        "phone": phone,
        "processado": False,
        "intencao": None,
        "acao": None,
        "respondido": False,
        "ja_processado": False,
        "anexos_processados": [],
        "escalado": False,
        "erro": None,
    }

    # 1. Idempotência
    if message_id and state.ja_processou(message_id):
        logger.info(f"[webhook] msg {message_id} já processada — ignorando (idempotente)")
        resumo["ja_processado"] = True
        return resumo

    # Contexto do inadimplente (se conseguir achar na base)
    contexto = _carregar_contexto_inadimplente(phone)
    nome_cliente = (contexto or {}).get("nome") or sender_name
    apto_cliente = (contexto or {}).get("unidade")
    boleto_id = None
    if contexto:
        boleto_id = (
            contexto.get("id")
            or contexto.get("boleto_id")
            or contexto.get("recibo_id")
        )

    # 2. Processa anexos (imagem/PDF = candidato a comprovante)
    anexo_relevante = any(a.get("tipo") in ("image", "document") for a in anexos)
    comprovante_invalido = False
    for a in anexos:
        if a.get("tipo") not in ("image", "document"):
            continue
        res_anexo = _processar_anexo_comprovante(phone, a, contexto, state)
        resumo["anexos_processados"].append(res_anexo)
        val = res_anexo.get("validacao") or {}
        if val and not val.get("valido"):
            # OCR rodou mas valor nao bate (ou nao tem boleto de referencia)
            # Marcamos como invalido apenas se OCR conseguiu extrair algo
            if val.get("motivo", "").startswith("valor_divergente"):
                comprovante_invalido = True

    # 3. Classifica intent
    # Verifica se ja enviou mensagem pra esse numero hoje (evita "Oi" repetido)
    ja_falou_hoje = False
    try:
        conversa = state.get_conversa(phone)
        if conversa and conversa.get("ultima_interacao"):
            from datetime import date
            ultima = datetime.fromisoformat(conversa["ultima_interacao"])
            ja_falou_hoje = ultima.date() == date.today()
    except Exception:
        pass

    # Se veio anexo de imagem/documento, usa o classificador novo com tem_anexo=True
    if anexo_relevante:
        intent_v2 = respostas_v2.classificar(texto or "", tem_anexo=True)
        # Verifica memória de conversa
        memoria = ConversaMemory(state)
        padroes = memoria.get_contexto(phone)["padroes"]
        intent_v2 = ajustar_classificacao_por_contexto(intent_v2, padroes)
        
        resp_v2 = respostas_v2.gerar_resposta(intent_v2, contexto, ja_falou_hoje=ja_falou_hoje)
        classificacao = {
            "intencao": intent_v2,
            "resposta_texto": resp_v2["texto"],
            "acao": "escalar_humano" if resp_v2["escalar_humano"] else "responder_auto",
            "confianca": 0.9,
            "tipo_escalacao": resp_v2.get("tipo_escalacao"),
            "delay_segundos": resp_v2.get("delay_segundos", 3.0),
            "log_extra": {"fonte": "respostas_v2", "anexo": True},
        }
    else:
        try:
            intent_v2 = respostas_v2.classificar(texto or "", tem_anexo=False)

            # ─── MEMÓRIA: Ajusta classificação baseada no histórico ───
            memoria = ConversaMemory(state)
            padroes = memoria.get_contexto(phone)["padroes"]
            
            # Se for desconhecida, tenta deduzir pelo contexto
            if intent_v2 == "desconhecida":
                intent_ajustada = ajustar_classificacao_por_contexto(intent_v2, padroes)
                if intent_ajustada != intent_v2:
                    logger.info(f"[webhook/memoria] Intenção ajustada: {intent_v2} → {intent_ajustada} (baseado em {padroes['total_interacoes']} msgs)")
                    intent_v2 = intent_ajustada

            # ─── ESCALAÇÃO SILENCIOSA ───
            # Se a intenção continua desconhecida após o ajuste,
            # responde educadamente e escala em silêncio
            escalar_silencioso = (intent_v2 == "desconhecida")
            if escalar_silencioso:
                logger.info(f"[webhook/memoria] Intenção desconhecida — escalando em silêncio ({phone})")
            
            # ─── SE PEDIU 2ª VIA: busca boletos no Superlógica ───
            if intent_v2 == "pedido_2via_boleto" and contexto:
                boleto_id = (
                    contexto.get("id")
                    or contexto.get("boleto_id")
                    or contexto.get("recibo_id")
                )
                if boleto_id:
                    try:
                        logger.info(f"[webhook] Pedido de 2ª via detectado — buscando boleto {boleto_id}...")
                        dados_boleto = superlogica_boleto.buscar_e_cachear_boleto(str(boleto_id))
                        if dados_boleto.get("sucesso"):
                            # Enriquece o contexto com dados do boleto
                            if dados_boleto.get("pix"):
                                contexto["pix"] = dados_boleto["pix"]
                            if dados_boleto.get("linha_digitavel"):
                                contexto["linha_digitavel"] = dados_boleto["linha_digitavel"]
                            if dados_boleto.get("link_pdf"):
                                contexto["link_boleto"] = dados_boleto["link_pdf"]
                            if dados_boleto.get("valor"):
                                contexto["valor"] = dados_boleto["valor"]
                            if dados_boleto.get("vencimento"):
                                contexto["vencimento"] = dados_boleto["vencimento"]
                    except Exception as e:
                        logger.warning(f"[webhook] Erro ao buscar boleto: {e}")

            # ─── RESPOSTA PERSONALIZADA EM TEMPO REAL ───
            if escalar_silencioso:
                # Escalação silenciosa: resposta educada genérica
                texto_resposta = gerar_resposta_sem_alerta(intent_v2)
                classificacao = {
                    "intencao": intent_v2,
                    "resposta_texto": texto_resposta,
                    "acao": "responder_auto",
                    "confianca": 0.3,
                    "tipo_escalacao": "desconhecida_silenciosa",
                    "delay_segundos": random.uniform(3.0, 6.0),
                    "log_extra": {"fonte": "engine_personalizado", "anexo": False, "escalado_silencioso": True},
                }
            else:
                # Gera resposta PERSONALIZADA em tempo real com base no contexto
                texto_personalizado = gerar_resposta_personalizada(
                    intent=intent_v2,
                    ctx=contexto or {},
                    historico=padroes,
                    padroes=padroes,
                )
                classificacao = {
                    "intencao": intent_v2,
                    "resposta_texto": texto_personalizado,
                    "acao": "escalar_humano" if intent_v2 in ("pedido_acordo", "reclamacao", "desconhecida") else "responder_auto",
                    "confianca": 0.85,
                    "tipo_escalacao": intent_v2 if intent_v2 in ("pedido_acordo", "reclamacao") else None,
                    "delay_segundos": random.uniform(3.0, 8.0),
                    "log_extra": {"fonte": "engine_personalizado", "anexo": False},
                }
        except Exception as e:
            logger.exception(f"[webhook] erro classificando v2: {e}")
            # Fallback pro legacy
            try:
                classificacao = classificar_e_responder(phone, texto, contexto)
            except Exception as e2:
                logger.exception(f"[webhook] erro classificando legacy: {e2}")
                classificacao = {
                    "intencao": "indefinido",
                    "resposta_texto": None,
                    "acao": "escalar_humano",
                    "confianca": 0.0,
                    "log_extra": {"erro_classificacao": str(e2)},
                }

    # Se comprovante chegou invalido, sobrescreve pra escalar humano
    if comprovante_invalido:
        classificacao = dict(classificacao)
        classificacao["acao"] = "escalar_humano"
        classificacao["intencao"] = classificacao.get("intencao") or "comprovante"
        classificacao["tipo_escalacao"] = "comprovante_invalido"
        classificacao["resposta_texto"] = (
            "Recebi o comprovante mas o valor parece diferente do esperado. "
            "Vou pedir pra Pratika conferir aqui direitinho e ja te retorno."
        )
        classificacao.setdefault("log_extra", {})["comprovante_invalido"] = True

    resumo["intencao"] = classificacao.get("intencao")
    resumo["acao"] = classificacao.get("acao")

    # 4. Envia resposta (com delay natural simulando digitacao humana)
    if RESPOSTAS_AUTO_HABILITADAS and classificacao.get("resposta_texto"):
        # Politica: pra "escalar_humano" tambem mandamos texto de holding pro cliente
        if _deve_responder(phone, contexto):
            try:
                # Delay natural simulando digitacao (3-8 segundos)
                delay = classificacao.get("delay_segundos", random.uniform(3.0, 8.0))
                if delay > 0:
                    logger.info(f"[webhook] aguardando {delay:.1f}s antes de responder (simulando digitacao)...")
                    time.sleep(delay)

                sender = make_sender()
                envio = sender.enviar_texto(
                    numero_whatsapp=phone,
                    texto=classificacao["resposta_texto"],
                )
                resumo["respondido"] = bool(envio.get("sucesso"))
                if not envio.get("sucesso"):
                    resumo["erro"] = envio.get("erro")
                    logger.error(f"[webhook] falha enviando resposta auto: {envio.get('erro')}")
                else:
                    logger.success(
                        f"[webhook] resposta enviada pra {phone} "
                        f"(intencao={classificacao.get('intencao')}, delay={delay:.1f}s)"
                    )
            except Exception as e:
                logger.exception(f"[webhook] erro enviando resposta: {e}")
                resumo["erro"] = str(e)
        else:
            logger.info(
                f"[webhook] política '{_politica_resposta()}' bloqueou resposta pra {phone}"
            )
            classificacao = dict(classificacao)
            classificacao["acao"] = "escalar_humano"
            classificacao.setdefault("log_extra", {})["bloqueado_por_politica"] = _politica_resposta()
            resumo["acao"] = "escalar_humano"

    # 5. Escala humano se necessario (incluindo escalação silenciosa)
    deve_escalar = (
        classificacao.get("acao") == "escalar_humano"
        or classificacao.get("log_extra", {}).get("escalado_silencioso")
    )
    if deve_escalar:
        motivo = (
            classificacao.get("tipo_escalacao")
            or classificacao.get("intencao")
            or "desconhecida"
        )
        # Se for escalação silenciosa, marca no log
        if classificacao.get("log_extra", {}).get("escalado_silencioso"):
            motivo = "silencioso_" + motivo
            logger.info(f"[webhook] 🔇 Escalação SILENCIOSA pra {phone} (motivo: {motivo})")
        
        try:
            esc = escalar_humano(
                telefone=phone,
                nome=nome_cliente,
                motivo=motivo,
                ultima_mensagem=texto or "(somente anexo)",
                apto=apto_cliente,
                state=state,
            )
            resumo["escalado"] = bool(esc.get("notificou_operador"))
            if esc.get("erro"):
                logger.warning(f"[webhook] escalacao com aviso: {esc['erro']}")
        except Exception as e:
            logger.exception(f"[webhook] erro escalando: {e}")

    # 6. Registra mensagem + atualiza conversa
    try:
        state.registrar_mensagem_recebida(
            message_id=message_id,
            phone=phone,
            sender_name=sender_name,
            texto=texto or "(sem texto)",
            classificacao=classificacao,
        )
    except Exception as e:
        logger.exception(f"[webhook] erro registrando msg recebida: {e}")
        resumo["erro"] = (resumo["erro"] or "") + f" | log_db: {e}"

    try:
        # Marca aguardando_comprovante quando o cliente disse que pagou (texto)
        aguardando = None
        if classificacao.get("intencao") in ("confirmacao_pagamento", "ja_paguei"):
            aguardando = True
        elif anexo_relevante and not comprovante_invalido:
            aguardando = False  # ja chegou o comprovante

        state.upsert_conversa(
            telefone=phone,
            ultimo_intent=classificacao.get("intencao"),
            ultima_mensagem=texto or "(anexo)",
            nome=nome_cliente,
            unidade=apto_cliente,
            aguardando_comprovante=aguardando,
            boleto_id_aberto=str(boleto_id) if boleto_id else None,
        )
    except Exception as e:
        logger.exception(f"[webhook] erro atualizando conversa: {e}")

    resumo["processado"] = True
    resumo["resposta_texto"] = classificacao.get("resposta_texto") if classificacao else None
    return resumo


# ─── Endpoints ───

@router.post("/zapi")
async def zapi_webhook(request: Request):
    """
    Recebe webhook do Z-API. Sempre retorna 200 (defensivo).

    Payload Z-API (On message received):
    {
      "phone": "5584999999999",
      "fromMe": false,
      "isGroup": false,
      "type": "ReceivedCallback",
      "messageId": "3EB0...",
      "text": {"message": "ja paguei"},
      "senderName": "Marco Antonio",
      "momment": 1697000000
    }
    """
    try:
        try:
            payload = await request.json()
        except Exception as e:
            logger.warning(f"[webhook] payload não-JSON: {e}")
            return JSONResponse({"ok": False, "motivo": "payload_invalido"}, status_code=200)

        logger.debug(f"[webhook] payload recebido: {json.dumps(payload, ensure_ascii=False)[:500]}")

        # 1. Filtros básicos
        if payload.get("fromMe") is True:
            return JSONResponse({"ok": True, "ignorado": "fromMe"}, status_code=200)

        if payload.get("isGroup") is True:
            return JSONResponse({"ok": True, "ignorado": "isGroup"}, status_code=200)

        # Z-API às vezes manda outros tipos (DeliveryCallback, MessageStatusCallback...)
        tipo = payload.get("type")
        if tipo and tipo != "ReceivedCallback":
            return JSONResponse({"ok": True, "ignorado": f"type={tipo}"}, status_code=200)

        # 2. Extrai campos
        phone = str(payload.get("phone") or "").strip()
        if not phone:
            return JSONResponse({"ok": False, "motivo": "sem_phone"}, status_code=200)

        texto = _extrair_texto(payload)
        anexos = _extrair_anexos(payload)

        # Se nao tem texto NEM anexo, ignora
        if not texto and not anexos:
            return JSONResponse({"ok": True, "ignorado": "sem_conteudo"}, status_code=200)

        message_id = str(
            payload.get("messageId") or payload.get("id") or
            f"NOID-{int(datetime.now().timestamp() * 1000)}"
        )
        sender_name = payload.get("senderName") or payload.get("chatName")

        # 3. Pipeline
        state = State(DB_PATH)
        resumo = _processar(phone, texto, sender_name, message_id, state, anexos=anexos)

        return JSONResponse({"ok": True, **resumo}, status_code=200)

    except Exception as e:
        # NUNCA retorna 500 pro Z-API — só loga e devolve 200
        logger.exception(f"[webhook] erro inesperado: {e}")
        return JSONResponse(
            {"ok": False, "erro": str(e)},
            status_code=200,
        )


@router.get("/zapi/test")
def zapi_webhook_test(
    phone: str = Query(..., description="Número do remetente (5584999999999)"),
    texto: str = Query(..., description="Texto da mensagem a simular"),
    sender_name: Optional[str] = Query(None),
    message_id: Optional[str] = Query(None, description="Se ausente, gera um automático"),
):
    """
    Endpoint manual de teste (GET) — roda o mesmo pipeline do webhook real.
    Útil pra QA via browser/curl sem precisar de Z-API configurado.
    """
    try:
        state = State(DB_PATH)
        msg_id = message_id or f"TEST-{int(datetime.now().timestamp() * 1000)}"
        resumo = _processar(phone, texto, sender_name, msg_id, state)
        return {"ok": True, "test": True, **resumo}
    except Exception as e:
        logger.exception(f"[webhook/test] erro: {e}")
        return {"ok": False, "erro": str(e)}


@router.post("/testar")
async def webhook_testar(request: Request):
    """
    Endpoint POST de teste — recebe payload simulado igual ao do Z-API,
    roda o pipeline e devolve o resumo. Util pra QA E2E.

    Exemplo body (mesmo formato do Z-API):
        {
          "phone": "5584999999999",
          "fromMe": false,
          "messageId": "TEST-123",
          "text": {"message": "ja paguei"},
          "senderName": "João"
        }

    Tambem aceita anexos:
        { ..., "image": {"imageUrl": "http://..."} }
        { ..., "document": {"documentUrl": "http://...", "fileName": "comp.pdf"} }
    """
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        phone = str(payload.get("phone") or "").strip()
        if not phone:
            return {"ok": False, "erro": "campo 'phone' obrigatorio"}

        texto = _extrair_texto(payload)
        anexos = _extrair_anexos(payload)
        message_id = str(
            payload.get("messageId")
            or payload.get("id")
            or f"TESTAR-{int(datetime.now().timestamp() * 1000)}"
        )
        sender_name = payload.get("senderName") or payload.get("chatName")

        state = State(DB_PATH)
        resumo = _processar(phone, texto, sender_name, message_id, state, anexos=anexos)
        return {"ok": True, "test": True, **resumo}
    except Exception as e:
        logger.exception(f"[webhook/testar] erro: {e}")
        return {"ok": False, "erro": str(e)}


@router.get("/conversas")
def conversas(limit: int = Query(50, ge=1, le=500)):
    """
    Lista conversas ativas (1 linha por telefone, da tabela 'conversas')
    + audit log de mensagens recebidas. Util pro dashboard.
    """
    try:
        state = State(DB_PATH)
        return {
            "total": limit,
            "politica_resposta": _politica_resposta(),
            "respostas_auto_habilitadas": RESPOSTAS_AUTO_HABILITADAS,
            "conversas": state.listar_conversas(limit),
            "mensagens": state.conversas_recentes(limit),
        }
    except Exception as e:
        logger.exception(f"[webhook/conversas] erro: {e}")
        return {"ok": False, "erro": str(e), "conversas": [], "mensagens": []}


@router.get("/conversas/{telefone}")
def conversa_detalhe(telefone: str, limit: int = Query(100, ge=1, le=500)):
    """Historico completo de uma conversa especifica (recebidas + enviadas)."""
    try:
        state = State(DB_PATH)
        return {
            "telefone": telefone,
            "historico": state.historico_conversa(telefone, limit),
        }
    except Exception as e:
        logger.exception(f"[webhook/conversa-detalhe] erro: {e}")
        return {"ok": False, "erro": str(e), "historico": []}


@router.get("/comprovantes")
def comprovantes_recentes(limit: int = Query(50, ge=1, le=500)):
    """Lista comprovantes recebidos recentemente (com resultado da validacao)."""
    try:
        state = State(DB_PATH)
        return {"total": limit, "comprovantes": state.comprovantes_recentes(limit)}
    except Exception as e:
        logger.exception(f"[webhook/comprovantes] erro: {e}")
        return {"ok": False, "erro": str(e), "comprovantes": []}
