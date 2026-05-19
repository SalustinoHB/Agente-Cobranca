"""
dashboard.py — Página HTML única para acompanhar a operação de cobrança.

Monta em /dashboard (router FastAPI). Sem build, sem React.
Apenas vanilla JS chamando os endpoints REST do mesmo serviço.

Tema escuro, acentos verdes (WhatsApp).
"""

import os
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from loguru import logger


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


BASE_PATH = os.getenv("BASE_JSON_PATH", "/data/renaissance.json")


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard_html():
    """Serve o dashboard HTML estático."""
    return HTMLResponse(content=HTML_PAGE)


# ─── Endpoint auxiliar pro dashboard ler os inadimplentes sem token ───
# (mantemos o /dashboard inteiro sem auth pra simplificar — em produção,
# proteja com basic auth do nginx ou similar)

@router.get("/data/conversas", include_in_schema=False)
def dashboard_conversas():
    """Conversas recentes pro painel (sem token — listagem leve)."""
    try:
        from agente.state import State
        db_path = os.getenv("DATABASE_PATH", "/data/state.db")
        state = State(db_path)
        return {
            "conversas": state.listar_conversas(50),
        }
    except Exception as e:
        logger.error(f"Dashboard: erro carregando conversas: {e}")
        return {"conversas": [], "erro": str(e)}


@router.get("/data/conversa/{telefone}", include_in_schema=False)
def dashboard_conversa_detalhe(telefone: str):
    """Historico completo de uma conversa."""
    try:
        from agente.state import State
        db_path = os.getenv("DATABASE_PATH", "/data/state.db")
        state = State(db_path)
        return {
            "telefone": telefone,
            "historico": state.historico_conversa(telefone, 100),
        }
    except Exception as e:
        logger.error(f"Dashboard: erro carregando conversa {telefone}: {e}")
        return {"telefone": telefone, "historico": [], "erro": str(e)}


@router.get("/data/inadimplentes", include_in_schema=False)
def dashboard_inadimplentes():
    """Retorna inadimplentes (boletos pendentes) sumarizados por unidade."""
    try:
        with open(BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"atualizado_em": None, "inadimplentes": []}
    except Exception as e:
        logger.error(f"Dashboard: erro lendo base: {e}")
        return {"atualizado_em": None, "inadimplentes": [], "erro": str(e)}

    boletos = data.get("boletos", [])
    # Agrupa por unidade
    por_unidade: dict = {}
    for b in boletos:
        if b.get("status", "").lower() in ("pago", "baixado", "quitado"):
            continue
        u = b.get("unidade") or "?"
        slot = por_unidade.setdefault(u, {
            "unidade": u,
            "nome": b.get("nome"),
            "whatsapp": b.get("whatsapp"),
            "valor_total": 0.0,
            "boletos": 0,
            "dias_atraso_max": 0,
            "juridico": False,
            "acordo": False,
        })
        slot["valor_total"] += float(b.get("valor") or 0)
        slot["boletos"] += 1
        if (b.get("dias_atraso") or 0) > slot["dias_atraso_max"]:
            slot["dias_atraso_max"] = b.get("dias_atraso") or 0
        slot["juridico"] = slot["juridico"] or bool(b.get("juridico"))
        slot["acordo"] = slot["acordo"] or bool(b.get("acordo"))

    return {
        "atualizado_em": data.get("atualizado_em"),
        "inadimplentes": list(por_unidade.values()),
    }


# ============================================================
# HTML
# ============================================================
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cobrança Renaissance — Painel</title>
  <style>
    :root {
      --bg: #0a0a0a;
      --bg-card: #141414;
      --bg-elev: #1c1c1c;
      --border: #262626;
      --text: #e5e5e5;
      --text-dim: #888;
      --green: #25D366;
      --green-dim: #128C7E;
      --red: #ef4444;
      --yellow: #eab308;
      --blue: #3b82f6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 24px;
      line-height: 1.5;
    }
    h1 { font-size: 22px; margin-bottom: 4px; }
    h2 { font-size: 16px; margin: 24px 0 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }
    .sub { color: var(--text-dim); font-size: 13px; margin-bottom: 24px; }

    /* Header status */
    .status-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
      padding: 16px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .status-item {
      display: flex; flex-direction: column; gap: 4px;
    }
    .status-label { color: var(--text-dim); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
    .status-value { font-size: 14px; font-weight: 600; }
    .pill {
      display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px;
      font-weight: 600;
    }
    .pill.green { background: rgba(37,211,102,0.15); color: var(--green); }
    .pill.red { background: rgba(239,68,68,0.15); color: var(--red); }
    .pill.yellow { background: rgba(234,179,8,0.15); color: var(--yellow); }
    .pill.blue { background: rgba(59,130,246,0.15); color: var(--blue); }

    /* Actions */
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
    button {
      background: var(--bg-elev);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.15s;
    }
    button:hover { border-color: var(--green); color: var(--green); }
    button.primary {
      background: var(--green);
      color: #000;
      border-color: var(--green);
      font-weight: 600;
    }
    button.primary:hover { background: var(--green-dim); color: #fff; }
    button.danger:hover { border-color: var(--red); color: var(--red); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Cards */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 12px;
    }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 12px;
    }
    .card-title { font-weight: 600; font-size: 15px; }
    .card-unit { color: var(--text-dim); font-size: 12px; }
    .card-row {
      display: flex; justify-content: space-between;
      font-size: 13px; padding: 4px 0;
    }
    .card-row .k { color: var(--text-dim); }
    .card-row .v { color: var(--text); font-weight: 500; }
    .valor { color: var(--green); font-weight: 600; }
    .atraso-alto { color: var(--red); font-weight: 600; }

    .msg-preview {
      display: none;
      margin-top: 12px;
      padding: 12px;
      background: var(--bg-elev);
      border-radius: 6px;
      font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      font-size: 12px;
      white-space: pre-wrap;
      color: #d4d4d4;
      max-height: 280px;
      overflow-y: auto;
      border-left: 3px solid var(--green);
    }
    .msg-preview.show { display: block; }
    .card-actions { display: flex; gap: 6px; margin-top: 12px; }
    .card-actions button { padding: 6px 10px; font-size: 12px; flex: 1; }

    /* Histórico */
    .hist {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0;
      overflow: hidden;
    }
    .hist-row {
      display: grid;
      grid-template-columns: 130px 70px 100px 1fr 50px;
      gap: 12px;
      padding: 10px 16px;
      border-bottom: 1px solid var(--border);
      font-size: 12px;
      align-items: center;
    }
    .hist-row:last-child { border-bottom: none; }
    .hist-row.head { background: var(--bg-elev); color: var(--text-dim); font-weight: 600; }
    .hist-time { color: var(--text-dim); font-family: ui-monospace, monospace; }

    .empty { color: var(--text-dim); text-align: center; padding: 32px; font-size: 13px; }

    /* Conversas */
    .conv-head, .conv-row {
      display: grid;
      grid-template-columns: 130px 130px 60px 1fr 100px 90px !important;
      gap: 12px;
      padding: 10px 16px;
      border-bottom: 1px solid var(--border);
      font-size: 12px;
      align-items: center;
    }
    .conv-row { cursor: pointer; transition: background 0.1s; }
    .conv-row:hover { background: var(--bg-elev); }
    .conv-row:last-child { border-bottom: none; }
    .conv-row .truncate {
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .conv-row button.btn-detalhe {
      padding: 4px 8px; font-size: 11px;
    }

    /* Modal */
    .conv-modal {
      display: none;
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.7);
      z-index: 2000;
      align-items: flex-start;
      justify-content: center;
      padding: 40px 20px;
      overflow-y: auto;
    }
    .conv-modal.show { display: flex; }
    .conv-modal-content {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      max-width: 720px;
      width: 100%;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
    }
    .conv-modal-header {
      padding: 16px;
      border-bottom: 1px solid var(--border);
      display: flex; justify-content: space-between; align-items: center;
      font-weight: 600;
    }
    .conv-modal-close {
      background: transparent; border: none; color: var(--text-dim);
      font-size: 24px; cursor: pointer; padding: 0 8px;
    }
    .conv-modal-close:hover { color: var(--text); }
    #conv-modal-body {
      padding: 16px;
      overflow-y: auto;
      flex: 1;
    }
    .msg-bubble {
      padding: 10px 14px;
      margin-bottom: 8px;
      border-radius: 8px;
      max-width: 80%;
      font-size: 13px;
      line-height: 1.4;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .msg-bubble.recebida {
      background: var(--bg-elev); border-left: 3px solid var(--blue);
      margin-right: auto;
    }
    .msg-bubble.enviada {
      background: rgba(37,211,102,0.1); border-left: 3px solid var(--green);
      margin-left: auto;
    }
    .msg-bubble .meta {
      display: block;
      font-size: 11px;
      color: var(--text-dim);
      margin-bottom: 4px;
    }

    .toast {
      position: fixed;
      bottom: 24px; right: 24px;
      padding: 12px 16px;
      background: var(--bg-card);
      border: 1px solid var(--green);
      color: var(--green);
      border-radius: 6px;
      font-size: 13px;
      z-index: 1000;
      display: none;
    }
    .toast.show { display: block; animation: slidein 0.2s ease; }
    .toast.error { border-color: var(--red); color: var(--red); }
    @keyframes slidein { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

    .footer { margin-top: 32px; color: var(--text-dim); font-size: 11px; text-align: center; }

    .token-bar {
      margin-bottom: 16px;
      padding: 12px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 6px;
      display: flex; gap: 8px; align-items: center;
    }
    .token-bar input {
      flex: 1;
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-family: ui-monospace, monospace;
    }
    .token-bar label { font-size: 12px; color: var(--text-dim); }
  </style>
</head>
<body>
  <h1>Cobrança Renaissance</h1>
  <div class="sub">Painel operacional — Pratika Administradora</div>

  <div class="token-bar">
    <label>API Token:</label>
    <input id="api-token" type="password" placeholder="cole o API_TOKEN do .env (deixe vazio se desabilitado)" />
    <button onclick="salvarToken()">Salvar</button>
  </div>

  <!-- Status -->
  <div class="status-bar" id="status-bar">
    <div class="status-item"><span class="status-label">WhatsApp</span><span class="status-value" id="s-wpp">--</span></div>
    <div class="status-item"><span class="status-label">Sender</span><span class="status-value" id="s-sender">--</span></div>
    <div class="status-item"><span class="status-label">Modo</span><span class="status-value" id="s-modo">--</span></div>
    <div class="status-item"><span class="status-label">Enviados hoje</span><span class="status-value" id="s-enviados">--</span></div>
    <div class="status-item"><span class="status-label">Base atualizada</span><span class="status-value" id="s-base">--</span></div>
    <div class="status-item"><span class="status-label">Último scraper</span><span class="status-value" id="s-scraper">--</span></div>
  </div>

  <!-- Actions -->
  <div class="actions">
    <button class="primary" onclick="rodarPreview()">Rodar régua (dry-run)</button>
    <button onclick="sincronizar()">Sincronizar Superlógica</button>
    <button onclick="refresh()">Atualizar agora</button>
    <button onclick="confirmarTodos()" id="btn-conf-todos" style="display:none">Aprovar TODOS pendentes</button>
  </div>

  <h2>Inadimplentes</h2>
  <div class="grid" id="cards"></div>

  <h2>Conversas (auto-responder — últimas 50)</h2>
  <div class="hist" id="conversas">
    <div class="hist-row head conv-head">
      <div>Atualizado</div><div>Telefone</div><div>Apto</div><div>Última mensagem</div><div>Status</div>
    </div>
    <div id="conversas-body"></div>
  </div>

  <!-- Modal de detalhe de conversa -->
  <div id="conv-modal" class="conv-modal">
    <div class="conv-modal-content">
      <div class="conv-modal-header">
        <span id="conv-modal-title">Conversa</span>
        <button class="conv-modal-close" onclick="fecharConversa()">×</button>
      </div>
      <div id="conv-modal-body"></div>
    </div>
  </div>

  <h2>Histórico (últimos 30 envios)</h2>
  <div class="hist" id="hist">
    <div class="hist-row head">
      <div>Quando</div><div>Etapa</div><div>Unidade</div><div>Nome</div><div></div>
    </div>
    <div id="hist-body"></div>
  </div>

  <div class="footer">Auto-refresh a cada 30s — Pratika / Renaissance</div>
  <div class="toast" id="toast"></div>

<script>
  // ─── Token storage ───
  const TOKEN_KEY = "cobranca_api_token";
  let API_TOKEN = localStorage.getItem(TOKEN_KEY) || "";
  document.getElementById("api-token").value = API_TOKEN;

  function salvarToken() {
    API_TOKEN = document.getElementById("api-token").value.trim();
    localStorage.setItem(TOKEN_KEY, API_TOKEN);
    toast("Token salvo");
    refresh();
  }

  function headers() {
    const h = { "Content-Type": "application/json" };
    if (API_TOKEN) h["Authorization"] = "Bearer " + API_TOKEN;
    return h;
  }

  async function api(path, options = {}) {
    options.headers = Object.assign({}, headers(), options.headers || {});
    const r = await fetch(path, options);
    if (!r.ok) {
      const txt = await r.text();
      throw new Error("HTTP " + r.status + ": " + txt);
    }
    return r.json();
  }

  // ─── Toast ───
  function toast(msg, err) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.toggle("error", !!err);
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 3000);
  }

  // ─── Status ───
  async function carregarStatus() {
    try {
      const s = await api("/api/status");
      document.getElementById("s-modo").innerHTML = s.modo === "REAL"
        ? '<span class="pill red">REAL</span>'
        : '<span class="pill yellow">DRY-RUN</span>';
      document.getElementById("s-sender").textContent = s.sender_backend || "--";
      const wpp = s.whatsapp_conectado;
      document.getElementById("s-wpp").innerHTML = wpp === true
        ? '<span class="pill green">conectado</span>'
        : wpp === false
        ? '<span class="pill red">desconectado</span>'
        : '<span class="pill yellow">N/A (dry-run)</span>';
      document.getElementById("s-enviados").textContent = s.enviados_hoje ?? 0;
      document.getElementById("s-base").textContent = s.base_atualizada_em
        ? new Date(s.base_atualizada_em).toLocaleString("pt-BR")
        : "--";
      const sr = s.scraper_ultima_run;
      document.getElementById("s-scraper").textContent = sr
        ? (sr.sucesso ? "OK" : "FALHOU") + " — " + (sr.iniciado_em || "")
        : "nunca";
    } catch (e) {
      document.getElementById("s-modo").innerHTML = '<span class="pill red">erro</span>';
      console.error(e);
    }
  }

  // ─── Cards de inadimplentes ───
  async function carregarCards() {
    try {
      const d = await fetch("/dashboard/data/inadimplentes").then(r => r.json());
      const grid = document.getElementById("cards");
      const lista = (d.inadimplentes || []).sort((a, b) => b.dias_atraso_max - a.dias_atraso_max);

      if (!lista.length) {
        grid.innerHTML = '<div class="empty">Sem inadimplentes na base atual</div>';
        return;
      }

      grid.innerHTML = lista.map(i => `
        <div class="card" data-unit="${i.unidade}">
          <div class="card-header">
            <div>
              <div class="card-title">${escapeHtml(i.nome || "—")}</div>
              <div class="card-unit">Apto ${escapeHtml(i.unidade)}</div>
            </div>
            <div>
              ${i.juridico ? '<span class="pill red">JURÍDICO</span>' : ""}
              ${i.acordo ? '<span class="pill blue">ACORDO</span>' : ""}
            </div>
          </div>
          <div class="card-row"><span class="k">Valor total</span><span class="v valor">${formatBRL(i.valor_total)}</span></div>
          <div class="card-row"><span class="k">Boletos abertos</span><span class="v">${i.boletos}</span></div>
          <div class="card-row"><span class="k">Atraso máximo</span><span class="v ${i.dias_atraso_max > 30 ? 'atraso-alto' : ''}">${i.dias_atraso_max} dias</span></div>
          <div class="card-row"><span class="k">WhatsApp</span><span class="v">${escapeHtml(i.whatsapp || "—")}</span></div>
          <div class="msg-preview" id="msg-${i.unidade}"></div>
          <div class="card-actions">
            <button onclick="verMensagem('${i.unidade}')">Ver mensagem</button>
            <button class="primary" onclick="aprovarUnidade('${i.unidade}')">Aprovar envio</button>
          </div>
        </div>
      `).join("");
    } catch (e) {
      document.getElementById("cards").innerHTML = '<div class="empty">Erro carregando inadimplentes</div>';
      console.error(e);
    }
  }

  // ─── Pendentes (cache local) ───
  let pendentes = [];

  async function carregarPendentes() {
    try {
      const d = await api("/api/aprovacao/pendentes");
      pendentes = d.candidatos || [];
      document.getElementById("btn-conf-todos").style.display = pendentes.length ? "" : "none";
      if (pendentes.length) {
        document.getElementById("btn-conf-todos").textContent =
          `Aprovar TODOS pendentes (${pendentes.length})`;
      }
    } catch (e) {
      pendentes = [];
    }
  }

  function pendenteDaUnidade(unidade) {
    return pendentes.find(p => p.unidade === unidade);
  }

  function verMensagem(unidade) {
    const div = document.getElementById("msg-" + unidade);
    const p = pendenteDaUnidade(unidade);
    if (!p) {
      div.textContent = "Nenhuma mensagem pendente. Rode 'Rodar régua (dry-run)' primeiro.";
      div.classList.add("show");
      return;
    }
    div.textContent = `[${p.etapa_codigo}] ${p.etapa_descricao}\n\n${p.texto}`;
    div.classList.toggle("show");
  }

  async function aprovarUnidade(unidade) {
    const p = pendenteDaUnidade(unidade);
    if (!p) {
      toast("Sem pendente pra esta unidade. Rode a régua primeiro.", true);
      return;
    }
    if (!confirm(`Confirmar envio de [${p.etapa_codigo}] para ${p.nome} (Apto ${unidade})?`)) return;

    try {
      const r = await api("/api/aprovacao/confirmar", {
        method: "POST",
        body: JSON.stringify({ ids: [p.boleto_id], todos: false }),
      });
      toast(`Enviados: ${r.enviados} | Falhas: ${r.falhas}`);
      refresh();
    } catch (e) {
      toast("Erro: " + e.message, true);
    }
  }

  async function confirmarTodos() {
    if (!confirm(`Confirmar envio de TODOS os ${pendentes.length} pendentes?`)) return;
    try {
      const r = await api("/api/aprovacao/confirmar", {
        method: "POST",
        body: JSON.stringify({ ids: [], todos: true }),
      });
      toast(`Enviados: ${r.enviados} | Falhas: ${r.falhas}`);
      refresh();
    } catch (e) {
      toast("Erro: " + e.message, true);
    }
  }

  // ─── Ações ───
  async function rodarPreview() {
    toast("Rodando régua em dry-run...");
    try {
      const r = await api("/api/aprovacao/preview", { method: "POST" });
      toast(`${r.total} candidato(s) gerados`);
      await carregarPendentes();
      await carregarCards();
    } catch (e) {
      toast("Erro: " + e.message, true);
    }
  }

  async function sincronizar() {
    if (!confirm("Rodar scraper Superlógica agora? Pode demorar 30-60s.")) return;
    toast("Sincronizando...");
    try {
      const r = await api("/api/sincronizar", { method: "POST" });
      toast(`Sincronizado: ${r.boletos_coletados} boletos`);
      refresh();
    } catch (e) {
      toast("Erro: " + e.message, true);
    }
  }

  // ─── Histórico ───
  async function carregarHistorico() {
    try {
      const d = await api("/api/historico?limit=30");
      const body = document.getElementById("hist-body");
      const envios = d.envios || [];
      if (!envios.length) {
        body.innerHTML = '<div class="empty">Sem envios registrados</div>';
        return;
      }
      body.innerHTML = envios.map(e => `
        <div class="hist-row">
          <div class="hist-time">${formatTime(e.enviado_em)}</div>
          <div><span class="pill ${e.dry_run ? 'yellow' : (e.sucesso ? 'green' : 'red')}">${e.etapa_codigo}</span></div>
          <div>${escapeHtml(e.unidade || "—")}</div>
          <div>${escapeHtml(e.nome || "—")}</div>
          <div>${e.sucesso ? "OK" : "FAIL"}</div>
        </div>
      `).join("");
    } catch (e) {
      document.getElementById("hist-body").innerHTML = '<div class="empty">Erro carregando histórico</div>';
    }
  }

  // ─── Helpers ───
  function formatBRL(v) {
    return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }
  function formatTime(s) {
    if (!s) return "--";
    try { return new Date(s.replace(" ", "T") + "Z").toLocaleString("pt-BR"); }
    catch (e) { return s; }
  }
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, c => ({
      "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
    }[c]));
  }

  // ─── Conversas (auto-responder) ───
  async function carregarConversas() {
    try {
      const d = await fetch("/dashboard/data/conversas").then(r => r.json());
      const body = document.getElementById("conversas-body");
      const lista = d.conversas || [];
      if (!lista.length) {
        body.innerHTML = '<div class="empty">Nenhuma conversa registrada ainda</div>';
        return;
      }
      body.innerHTML = lista.map(c => {
        const escalado = c.escalado_humano;
        const aguardandoComp = c.aguardando_comprovante;
        let statusPill;
        if (escalado) {
          statusPill = '<span class="pill red">escalado</span>';
        } else if (aguardandoComp) {
          statusPill = '<span class="pill yellow">aguardando comp.</span>';
        } else {
          statusPill = '<span class="pill green">auto</span>';
        }
        return `
          <div class="hist-row conv-row" onclick="verConversa('${c.telefone}', '${escapeHtml(c.nome || c.telefone)}')">
            <div class="hist-time">${formatTime(c.atualizado_em || c.ultima_mensagem_em)}</div>
            <div>${escapeHtml(c.telefone)}</div>
            <div>${escapeHtml(c.unidade || "—")}</div>
            <div class="truncate">${escapeHtml((c.ultima_mensagem || "—").slice(0, 80))}</div>
            <div><span class="pill blue">${escapeHtml(c.ultimo_intent || "?")}</span></div>
            <div>${statusPill}</div>
          </div>
        `;
      }).join("");
    } catch (e) {
      console.error("Erro carregando conversas:", e);
      document.getElementById("conversas-body").innerHTML =
        '<div class="empty">Erro carregando conversas</div>';
    }
  }

  async function verConversa(telefone, titulo) {
    document.getElementById("conv-modal-title").textContent = `Conversa: ${titulo}`;
    const body = document.getElementById("conv-modal-body");
    body.innerHTML = '<div class="empty">Carregando...</div>';
    document.getElementById("conv-modal").classList.add("show");
    try {
      const d = await fetch("/dashboard/data/conversa/" + encodeURIComponent(telefone))
        .then(r => r.json());
      const hist = (d.historico || []).reverse();  // mais antigos primeiro
      if (!hist.length) {
        body.innerHTML = '<div class="empty">Sem mensagens registradas</div>';
        return;
      }
      body.innerHTML = hist.map(m => {
        const cls = m.direcao === "enviada" ? "enviada" : "recebida";
        const label = m.direcao === "enviada" ? "Pratika ->" : "<- Cliente";
        const intent = m.intencao ? ` · ${escapeHtml(m.intencao)}` : "";
        return `
          <div class="msg-bubble ${cls}">
            <span class="meta">${label} ${formatTime(m.quando)}${intent}</span>
            ${escapeHtml(m.texto || "")}
          </div>
        `;
      }).join("");
    } catch (e) {
      body.innerHTML = '<div class="empty">Erro carregando historico</div>';
    }
  }

  function fecharConversa() {
    document.getElementById("conv-modal").classList.remove("show");
  }
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") fecharConversa();
  });

  // ─── Refresh loop ───
  async function refresh() {
    await Promise.all([
      carregarStatus(),
      carregarPendentes(),
      carregarHistorico(),
      carregarConversas(),
    ]);
    await carregarCards();
  }

  refresh();
  setInterval(refresh, 30000);
</script>
</body>
</html>
"""
