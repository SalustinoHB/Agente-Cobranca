"""
api.py — API REST do Agente Cobrança Renaissance.

Endpoints expostos:
  GET    /                              → info da API + healthcheck
  GET    /api/boletos                    → lista boletos pendentes (com filtros)
  GET    /api/boletos/{id}               → detalhe de um boleto
  GET    /api/unidades                   → lista todas unidades + contatos
  GET    /api/unidades/{numero}          → detalhe de uma unidade
  POST   /api/mensagem                   → envia mensagem WhatsApp (manual)
  POST   /api/sincronizar                → força scraper Superlógica
  POST   /api/regua/executar             → roda 1 ciclo da régua (com flag dry_run)
  GET    /api/historico                  → últimos envios
  GET    /api/historico/hoje             → resumo de hoje
  GET    /api/status                     → status geral (WhatsApp + scraper + agente)
  GET    /api/whatsapp/status            → status detalhado do sender
  POST   /api/blacklist                  → adicionar número à blacklist
  DELETE /api/blacklist/{whatsapp}       → remover da blacklist
  POST   /api/aprovacao/preview          → roda régua em dry-run e grava pendentes
  GET    /api/aprovacao/pendentes        → lista candidatos aguardando aprovação
  POST   /api/aprovacao/confirmar        → envia os pendentes aprovados
  GET    /dashboard                      → painel HTML de operação

Auth: Bearer token via header `Authorization: Bearer <API_TOKEN>` ou query `?token=`.

Rodar local:
    uvicorn agente.api:app --host 0.0.0.0 --port 5000 --reload

Docs interativas:
    http://localhost:5000/docs       (Swagger UI)
    http://localhost:5000/redoc      (ReDoc)
"""

import os
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

from agente.state import State
from agente.sender import BaseSender, make_sender
from agente import regua, scraper, templates as tpl

load_dotenv()

# Logs centralizados (best-effort — se ainda não foi inicializado)
try:
    from agente.logging_config import setup_logging
    setup_logging()
except Exception:
    pass


# ─── Config ───
API_TOKEN = os.getenv("API_TOKEN", "")
BASE_PATH = os.getenv("BASE_JSON_PATH", "/data/renaissance.json")
CONTATOS_PATH = os.getenv("CONTATOS_PATH", "/data/contatos.json")
DB_PATH = os.getenv("DATABASE_PATH", "/data/state.db")
ENVIAR_DE_VERDADE = os.getenv("ENVIAR_DE_VERDADE", "false").lower() == "true"


# ─── Dependências ───
def get_state() -> State:
    return State(DB_PATH)


def get_sender() -> BaseSender:
    """Constrói o sender configurado em SENDER_TYPE (baileys | zapi | evolution | dryrun)."""
    return make_sender()


# Caminho do arquivo de aprovações pendentes (entre /preview e /confirmar)
PENDENTES_PATH = os.getenv("PENDENTES_PATH", "/data/pendentes.json")


def require_token(authorization: Optional[str] = Header(None), token: Optional[str] = Query(None)):
    if not API_TOKEN:
        return  # sem token configurado, libera tudo (apenas dev)

    received = None
    if authorization and authorization.startswith("Bearer "):
        received = authorization.replace("Bearer ", "").strip()
    elif token:
        received = token

    if received != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")


# ─── Models ───
class Boleto(BaseModel):
    boleto_id: str
    unidade: str
    nome: str
    whatsapp: Optional[str] = None
    vencimento: str
    valor: float
    dias_atraso: int
    status: str
    competencia: Optional[str] = None
    juridico: bool = False
    acordo: bool = False
    parcela: Optional[str] = None
    observacao: Optional[str] = None


class MensagemRequest(BaseModel):
    whatsapp: str = Field(..., description="Número com DDD: +5584999999999 ou 84999999999")
    texto: str = Field(..., min_length=1, max_length=4000)
    forcar_envio: bool = Field(False, description="Se true, ignora DRY-RUN (use com cautela)")


class MensagemResposta(BaseModel):
    sucesso: bool
    message_id: Optional[str] = None
    erro: Optional[str] = None
    dry_run: bool


class ReguaRequest(BaseModel):
    dry_run: bool = Field(True, description="True = não envia, só simula")
    forcar: bool = Field(False, description="Ignorar janela horária")


class BlacklistRequest(BaseModel):
    whatsapp: str
    motivo: str = ""


class ConfirmacaoRequest(BaseModel):
    ids: List[str] = Field(default_factory=list, description="IDs de boletos a aprovar (boleto_id)")
    todos: bool = Field(False, description="Se true, aprova todos os pendentes")


# ─── App ───
app = FastAPI(
    title="Agente Cobrança Renaissance — API",
    description="API REST para coletar boletos e enviar mensagens de cobrança via Evolution/WhatsApp.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ───

@app.get("/", tags=["health"])
def root():
    """Healthcheck básico — não requer auth."""
    return {
        "servico": "Agente Cobrança Renaissance",
        "versao": "0.2.0",
        "modo": "REAL" if ENVIAR_DE_VERDADE else "DRY-RUN",
        "data_atual": datetime.now().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "boletos": "GET /api/boletos",
            "enviar": "POST /api/mensagem",
            "sincronizar": "POST /api/sincronizar",
            "historico": "GET /api/historico",
            "status": "GET /api/status",
        },
    }


@app.get("/api/status", tags=["status"], dependencies=[Depends(require_token)])
def status():
    """Status geral: WhatsApp conectado? Scraper rodou hoje? Quantos enviados hoje?"""
    state = get_state()
    sender = get_sender()

    return {
        "modo": "REAL" if ENVIAR_DE_VERDADE else "DRY-RUN",
        "sender_backend": getattr(sender, "nome_backend", "desconhecido"),
        "whatsapp_conectado": sender.esta_conectado() if not sender.dry_run else None,
        # mantém chave legada por compat com clientes antigos
        "evolution_conectado": sender.esta_conectado() if not sender.dry_run else None,
        "whatsapp_conectado": sender.esta_conectado() if not sender.dry_run else None,
        "enviados_hoje": state.enviados_hoje(),
        "base_atualizada_em": _data_base(),
        "scraper_ultima_run": _ultima_scraper_run(state),
    }


@app.get("/api/whatsapp/status", tags=["status"], dependencies=[Depends(require_token)])
def whatsapp_status():
    """Status detalhado da conexão WhatsApp do sender configurado."""
    sender = get_sender()
    try:
        raw = sender.status_instancia()
    except Exception as e:
        raw = {"erro": str(e)}
    return {
        "backend": getattr(sender, "nome_backend", "desconhecido"),
        "dry_run": getattr(sender, "dry_run", False),
        "conectado": sender.esta_conectado() if not getattr(sender, "dry_run", False) else True,
        "detalhes": raw,
    }


def _data_base():
    try:
        with open(BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("atualizado_em")
    except Exception:
        return None


def _ultima_scraper_run(state: State):
    with state._cursor() as c:
        c.execute("SELECT iniciado_em, sucesso, boletos_coletados, erro FROM scraper_runs ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        return dict(row) if row else None


@app.get("/api/boletos", tags=["boletos"], dependencies=[Depends(require_token)])
def listar_boletos(
    status: Optional[str] = Query(None, description="vencido | a_vencer | pago | todos"),
    unidade: Optional[str] = Query(None, description="Filtrar por unidade (ex: 0602)"),
    apenas_juridico: bool = Query(False),
    apenas_acordo: bool = Query(False),
):
    """Lista todos os boletos pendentes (ou filtrados)."""
    try:
        with open(BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, "Base não encontrada. Rode /api/sincronizar primeiro.")

    boletos = data.get("boletos", [])

    # Filtros
    if status and status != "todos":
        boletos = [b for b in boletos if b.get("status") == status]
    if unidade:
        boletos = [b for b in boletos if b.get("unidade") == unidade]
    if apenas_juridico:
        boletos = [b for b in boletos if b.get("juridico")]
    if apenas_acordo:
        boletos = [b for b in boletos if b.get("acordo")]

    return {
        "total": len(boletos),
        "atualizado_em": data.get("atualizado_em"),
        "resumo": data.get("resumo", {}),
        "boletos": boletos,
    }


@app.get("/api/boletos/{boleto_id}", tags=["boletos"], dependencies=[Depends(require_token)])
def detalhe_boleto(boleto_id: str):
    """Detalhe de um boleto específico + render preview da mensagem que seria enviada."""
    try:
        with open(BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, "Base não encontrada")

    for b in data.get("boletos", []):
        if str(b.get("boleto_id")) == str(boleto_id) or str(b.get("nn")) == str(boleto_id):
            # Render preview
            preview = tpl.renderizar(b)
            return {"boleto": b, "preview_mensagem": preview}

    raise HTTPException(404, f"Boleto {boleto_id} não encontrado")


@app.get("/api/unidades", tags=["unidades"], dependencies=[Depends(require_token)])
def listar_unidades():
    """Lista todas as 29 unidades do condomínio com seus contatos."""
    base_completa_path = "/data/base_completa_moacyr_maia.json"
    try:
        with open(base_completa_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback: contatos.json (só os inadimplentes)
        try:
            with open(CONTATOS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise HTTPException(404, "Base de unidades não disponível")


@app.get("/api/unidades/{numero}", tags=["unidades"], dependencies=[Depends(require_token)])
def detalhe_unidade(numero: str):
    """Detalhe de uma unidade específica."""
    base_completa_path = "/data/base_completa_moacyr_maia.json"
    try:
        with open(base_completa_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, "Base não disponível")

    for u in data.get("unidades", []):
        if u.get("unidade") == numero:
            return u

    raise HTTPException(404, f"Unidade {numero} não encontrada")


@app.post("/api/mensagem", tags=["envio"], response_model=MensagemResposta, dependencies=[Depends(require_token)])
def enviar_mensagem(req: MensagemRequest):
    """
    Envia mensagem WhatsApp manual.

    Em DRY-RUN: retorna que enviaria, mas não envia.
    Pra forçar envio real (ignorando DRY-RUN), passe `forcar_envio: true` — use com EXTREMA cautela.
    """
    state = get_state()
    sender = get_sender()

    # Modo
    dry = sender.dry_run
    if req.forcar_envio:
        sender.dry_run = False
        dry = False
        logger.warning(f"⚠️ Envio FORÇADO via API para {req.whatsapp}")

    # Blacklist check
    if state.esta_na_blacklist(req.whatsapp):
        raise HTTPException(403, f"Número {req.whatsapp} está na blacklist")

    # Envia
    resultado = sender.enviar_texto(numero_whatsapp=req.whatsapp, texto=req.texto)

    # Log
    state.registrar_envio(
        boleto={
            "id": f"MANUAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "nome": "MANUAL",
            "whatsapp": req.whatsapp,
            "valor": 0,
            "vencimento": None,
            "dias_atraso": 0,
        },
        etapa_codigo="MANUAL",
        etapa_descricao="Envio manual via API",
        texto=req.texto,
        dry_run=dry,
        sucesso=resultado["sucesso"],
        evolution_message_id=resultado["message_id"],
        evolution_response=str(resultado["raw_response"])[:500],
        erro=resultado["erro"],
    )

    return MensagemResposta(
        sucesso=resultado["sucesso"],
        message_id=resultado["message_id"],
        erro=resultado["erro"],
        dry_run=dry,
    )


@app.post("/api/sincronizar", tags=["scraper"], dependencies=[Depends(require_token)])
def sincronizar_superlogica():
    """Força execução do scraper Superlógica agora (atualiza base)."""
    state = get_state()
    url = os.getenv("SUPERLOGICA_URL", "https://admin109865.superlogica.net")
    cookies = os.getenv("COOKIES_PATH", "/data/superlogica_cookies.json")
    condominio_id = int(os.getenv("SUPERLOGICA_CONDOMINIO_ID", "29"))
    lote = os.getenv("SUPERLOGICA_LOTE_MES", "auto")

    run_id = state.registrar_scraper_inicio()
    try:
        boletos = scraper.coletar_boletos(url, cookies, condominio_id, lote, headless=True)
        boletos = scraper.cruzar_com_contatos(boletos, CONTATOS_PATH)
        scraper.salvar_base(boletos, BASE_PATH)
        state.registrar_scraper_fim(run_id, sucesso=True, boletos=len(boletos))
        return {"sucesso": True, "boletos_coletados": len(boletos)}
    except Exception as e:
        state.registrar_scraper_fim(run_id, sucesso=False, erro=str(e))
        raise HTTPException(500, f"Scraper falhou: {e}")


@app.post("/api/regua/executar", tags=["regua"], dependencies=[Depends(require_token)])
def executar_regua(req: ReguaRequest):
    """Roda 1 ciclo da régua de cobrança. Por padrão em DRY-RUN."""
    state = get_state()
    sender = get_sender()

    if not req.dry_run and not ENVIAR_DE_VERDADE:
        raise HTTPException(403, "Para envio real, ENVIAR_DE_VERDADE precisa ser true no .env")

    sender.dry_run = req.dry_run

    resultado = regua.executar(
        base_path=BASE_PATH,
        state=state,
        sender=sender,
        intervalo_segundos=int(os.getenv("INTERVALO_ENTRE_ENVIOS_SEGUNDOS", "180")),
        soft_cap=int(os.getenv("SOFT_CAP_DIARIO", "50")),
        horario_inicio=os.getenv("HORARIO_INICIO_ENVIO", "09:00"),
        horario_fim=os.getenv("HORARIO_FIM_ENVIO", "18:00"),
        enviar_sab=os.getenv("ENVIAR_SABADO", "false").lower() == "true",
        enviar_dom=os.getenv("ENVIAR_DOMINGO", "false").lower() == "true",
        dry_run=req.dry_run,
        forcar=req.forcar,
    )
    return resultado


@app.get("/api/historico", tags=["historico"], dependencies=[Depends(require_token)])
def historico(limit: int = Query(50, ge=1, le=500)):
    """Últimos envios registrados."""
    state = get_state()
    return {"envios": state.envios_recentes(limit)}


@app.get("/api/historico/hoje", tags=["historico"], dependencies=[Depends(require_token)])
def historico_hoje():
    """Resumo do que rolou hoje."""
    state = get_state()
    return state.resumo_diario()


@app.post("/api/blacklist", tags=["blacklist"], dependencies=[Depends(require_token)])
def adicionar_blacklist(req: BlacklistRequest):
    """Adiciona número à blacklist (não receberá mensagens automáticas)."""
    state = get_state()
    state.adicionar_blacklist(req.whatsapp, req.motivo)
    return {"sucesso": True, "whatsapp": req.whatsapp}


@app.delete("/api/blacklist/{whatsapp}", tags=["blacklist"], dependencies=[Depends(require_token)])
def remover_blacklist(whatsapp: str):
    """Remove número da blacklist."""
    state = get_state()
    with state._cursor() as c:
        c.execute("DELETE FROM blacklist WHERE whatsapp = ?", (whatsapp,))
    return {"sucesso": True, "removido": whatsapp}


# ─── Workflow de aprovação ───

def _carregar_pendentes() -> dict:
    """Lê pendentes.json (ou retorna estrutura vazia)."""
    try:
        with open(PENDENTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"gerado_em": None, "candidatos": []}
    except Exception as e:
        logger.error(f"Erro lendo pendentes: {e}")
        return {"gerado_em": None, "candidatos": [], "erro": str(e)}


def _salvar_pendentes(payload: dict):
    """Escreve pendentes.json (cria pasta se preciso)."""
    p = Path(PENDENTES_PATH)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


@app.post("/api/aprovacao/preview", tags=["aprovacao"], dependencies=[Depends(require_token)])
def aprovacao_preview():
    """
    Roda a régua em modo DRY-RUN e devolve a lista de candidatos a envio
    (com mensagens renderizadas). Grava o resultado em `data/pendentes.json`
    pra revisão manual antes de confirmar.
    """
    state = get_state()
    boletos = regua.carregar_base(BASE_PATH)
    if not boletos:
        raise HTTPException(404, "Base vazia ou não encontrada. Rode /api/sincronizar.")

    candidatos = regua.filtrar_para_envio_hoje(boletos, state)

    # Serializa de forma limpa
    saida = []
    for item in candidatos:
        b = item["boleto"]
        r = item["resultado"]
        boleto_id = b.get("id") or b.get("boleto_id") or b.get("recibo_id")
        saida.append({
            "boleto_id": str(boleto_id) if boleto_id else None,
            "nome": b.get("nome"),
            "unidade": b.get("unidade"),
            "whatsapp": b.get("whatsapp"),
            "valor": b.get("valor"),
            "vencimento": b.get("vencimento"),
            "dias_atraso": b.get("dias_atraso"),
            "etapa_codigo": r.get("etapa_codigo"),
            "etapa_descricao": r.get("etapa_descricao"),
            "texto": r.get("texto"),
            "_boleto": b,  # cópia completa pra confirmação
        })

    payload = {
        "gerado_em": datetime.now().isoformat(),
        "total": len(saida),
        "candidatos": saida,
    }
    _salvar_pendentes(payload)
    logger.info(f"Preview gerado: {len(saida)} candidatos -> {PENDENTES_PATH}")

    # Retorna sem o _boleto completo (mais limpo pro cliente)
    return {
        "gerado_em": payload["gerado_em"],
        "total": payload["total"],
        "candidatos": [{k: v for k, v in c.items() if k != "_boleto"} for c in saida],
    }


@app.get("/api/aprovacao/pendentes", tags=["aprovacao"], dependencies=[Depends(require_token)])
def aprovacao_pendentes():
    """Retorna o conteúdo atual de pendentes.json (último preview gerado)."""
    payload = _carregar_pendentes()
    return {
        "gerado_em": payload.get("gerado_em"),
        "total": len(payload.get("candidatos", [])),
        "candidatos": [
            {k: v for k, v in c.items() if k != "_boleto"}
            for c in payload.get("candidatos", [])
        ],
    }


@app.post("/api/aprovacao/confirmar", tags=["aprovacao"], dependencies=[Depends(require_token)])
def aprovacao_confirmar(req: ConfirmacaoRequest):
    """
    Confirma envio dos candidatos aprovados (do último preview).

    Body:
      {"ids": ["123", "456"], "todos": false}
      ou {"todos": true}
    """
    if not req.todos and not req.ids:
        raise HTTPException(400, "Informe `ids` ou `todos: true`")

    payload = _carregar_pendentes()
    candidatos = payload.get("candidatos", [])
    if not candidatos:
        raise HTTPException(404, "Sem pendentes. Rode /api/aprovacao/preview primeiro.")

    selecionados = candidatos if req.todos else [
        c for c in candidatos if str(c.get("boleto_id")) in [str(i) for i in req.ids]
    ]

    if not selecionados:
        raise HTTPException(404, "Nenhum candidato bateu com os IDs informados")

    state = get_state()
    sender = get_sender()
    resultados = []
    enviados = 0
    falhas = 0

    for c in selecionados:
        boleto = c.get("_boleto") or {
            "id": c["boleto_id"],
            "nome": c["nome"],
            "unidade": c.get("unidade"),
            "whatsapp": c["whatsapp"],
            "valor": c.get("valor"),
            "vencimento": c.get("vencimento"),
            "dias_atraso": c.get("dias_atraso"),
        }

        # Blacklist guard
        if state.esta_na_blacklist(boleto.get("whatsapp", "")):
            resultados.append({
                "boleto_id": c["boleto_id"],
                "sucesso": False,
                "erro": "blacklist",
            })
            falhas += 1
            continue

        envio = sender.enviar_texto(
            numero_whatsapp=boleto["whatsapp"],
            texto=c["texto"],
        )
        state.registrar_envio(
            boleto=boleto,
            etapa_codigo=c["etapa_codigo"],
            etapa_descricao=c["etapa_descricao"],
            texto=c["texto"],
            dry_run=getattr(sender, "dry_run", False),
            sucesso=envio["sucesso"],
            evolution_message_id=envio["message_id"],
            evolution_response=str(envio["raw_response"])[:500],
            erro=envio["erro"],
        )

        if envio["sucesso"]:
            enviados += 1
        else:
            falhas += 1

        resultados.append({
            "boleto_id": c["boleto_id"],
            "nome": c["nome"],
            "etapa": c["etapa_codigo"],
            "sucesso": envio["sucesso"],
            "message_id": envio["message_id"],
            "erro": envio["erro"],
        })

    # Remove confirmados de pendentes.json (mantém os não selecionados)
    if req.todos:
        novos_candidatos = []
    else:
        ids_set = {str(i) for i in req.ids}
        novos_candidatos = [c for c in candidatos if str(c.get("boleto_id")) not in ids_set]

    payload["candidatos"] = novos_candidatos
    payload["total"] = len(novos_candidatos)
    payload["ultima_confirmacao"] = datetime.now().isoformat()
    _salvar_pendentes(payload)

    return {
        "enviados": enviados,
        "falhas": falhas,
        "total": len(selecionados),
        "resultados": resultados,
        "pendentes_restantes": len(novos_candidatos),
    }


# ─── Webhook auto-responder ───
try:
    from agente import webhook
    app.include_router(webhook.router)
    _webhook_port = os.getenv("API_PORT", "5000")
    _webhook_host = os.getenv("WEBHOOK_PUBLIC_HOST", "http://15.228.231.24")
    logger.info(
        f"Webhook auto-responder ativo em "
        f"{_webhook_host}:{_webhook_port}/api/webhook/zapi "
        f"(configure no painel Z-API → 'On message received'). "
        f"Endpoint manual de teste: POST {_webhook_host}:{_webhook_port}/api/webhook/testar"
    )
except Exception as e:
    logger.warning(f"Webhook não carregado: {e}")


# ─── Dashboard (HTML) ───
try:
    from agente import dashboard
    app.include_router(dashboard.router)
except Exception as e:
    logger.warning(f"Dashboard não carregado: {e}")


# ─── Tratamento de erros ───
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception(f"Erro não tratado: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "tipo": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agente.api:app", host="0.0.0.0", port=5000, reload=True)
