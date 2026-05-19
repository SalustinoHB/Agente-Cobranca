"""
state.py — Log e idempotência via SQLite.

Garante que:
- Cada mensagem enviada fica registrada (auditoria)
- A mesma etapa não é enviada 2x pro mesmo boleto (idempotência)
- Histórico permite saber: qual cliente recebeu o que, quando, com qual texto
"""

import os
import sqlite3
from datetime import datetime, date
from typing import Optional
from contextlib import contextmanager

from loguru import logger


SCHEMA = """
CREATE TABLE IF NOT EXISTS envios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    boleto_id TEXT NOT NULL,
    nome TEXT NOT NULL,
    unidade TEXT,
    whatsapp TEXT NOT NULL,
    etapa_codigo TEXT NOT NULL,          -- D-3, D-0, D+1, D+7, D+15, D+30
    etapa_descricao TEXT,
    dias_atraso INTEGER,
    valor REAL,
    vencimento TEXT,
    texto_enviado TEXT NOT NULL,
    dry_run BOOLEAN NOT NULL DEFAULT 0,
    sucesso BOOLEAN NOT NULL DEFAULT 0,
    evolution_message_id TEXT,
    evolution_response TEXT,
    erro TEXT,
    enviado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(boleto_id, etapa_codigo)      -- mesma etapa não envia 2x
);

CREATE INDEX IF NOT EXISTS idx_envios_data ON envios(enviado_em);
CREATE INDEX IF NOT EXISTS idx_envios_whatsapp ON envios(whatsapp);
CREATE INDEX IF NOT EXISTS idx_envios_boleto ON envios(boleto_id);

CREATE TABLE IF NOT EXISTS scraper_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    concluido_em TIMESTAMP,
    sucesso BOOLEAN NOT NULL DEFAULT 0,
    boletos_coletados INTEGER,
    erro TEXT
);

CREATE TABLE IF NOT EXISTS blacklist (
    whatsapp TEXT PRIMARY KEY,
    motivo TEXT,
    adicionado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensagens_recebidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    sender_name TEXT,
    texto_recebido TEXT NOT NULL,
    intencao TEXT,
    resposta_texto TEXT,
    acao TEXT,
    confianca REAL,
    respondido_automaticamente BOOLEAN DEFAULT 0,
    escalado_humano BOOLEAN DEFAULT 0,
    recebido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mensagens_recebidas_phone ON mensagens_recebidas(phone);
CREATE INDEX IF NOT EXISTS idx_mensagens_recebidas_recebido ON mensagens_recebidas(recebido_em);

-- ─── Auto-responder: contexto por telefone ───
CREATE TABLE IF NOT EXISTS conversas (
    telefone TEXT PRIMARY KEY,
    nome TEXT,
    unidade TEXT,
    ultimo_intent TEXT,
    ultima_mensagem TEXT,
    ultima_mensagem_em TIMESTAMP,
    aguardando_comprovante BOOLEAN DEFAULT 0,
    escalado_humano BOOLEAN DEFAULT 0,
    motivo_escalacao TEXT,
    boleto_id_aberto TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversas_atualizado ON conversas(atualizado_em);
CREATE INDEX IF NOT EXISTS idx_conversas_escalado ON conversas(escalado_humano);

-- ─── Auto-responder: comprovantes recebidos (OCR + validacao) ───
CREATE TABLE IF NOT EXISTS comprovantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone TEXT NOT NULL,
    arquivo TEXT NOT NULL,                  -- path local
    intent TEXT NOT NULL DEFAULT 'comprovante',
    valido BOOLEAN DEFAULT 0,
    valor_extraido REAL,
    data_extraida TEXT,
    boleto_id_associado TEXT,
    raw_text TEXT,
    motivo TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comprovantes_telefone ON comprovantes(telefone);
CREATE INDEX IF NOT EXISTS idx_comprovantes_criado ON comprovantes(criado_em);
"""


class State:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._cursor() as c:
            for stmt in SCHEMA.split(";"):
                if stmt.strip():
                    c.execute(stmt)
        logger.info(f"State DB inicializado: {self.db_path}")

    @contextmanager
    def _cursor(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ─── Idempotência ───

    def ja_enviado(self, boleto_id: str, etapa_codigo: str) -> bool:
        """Retorna True se essa combinação boleto+etapa já foi enviada com sucesso."""
        with self._cursor() as c:
            c.execute(
                "SELECT 1 FROM envios WHERE boleto_id=? AND etapa_codigo=? AND sucesso=1",
                (boleto_id, etapa_codigo),
            )
            return c.fetchone() is not None

    # ─── Log de envio ───

    def registrar_envio(
        self,
        boleto: dict,
        etapa_codigo: str,
        etapa_descricao: str,
        texto: str,
        dry_run: bool,
        sucesso: bool,
        evolution_message_id: Optional[str] = None,
        evolution_response: Optional[str] = None,
        erro: Optional[str] = None,
    ):
        with self._cursor() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO envios (
                    boleto_id, nome, unidade, whatsapp,
                    etapa_codigo, etapa_descricao,
                    dias_atraso, valor, vencimento,
                    texto_enviado, dry_run, sucesso,
                    evolution_message_id, evolution_response, erro
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    boleto.get("id") or boleto.get("boleto_id") or boleto.get("recibo_id"),
                    boleto["nome"],
                    boleto.get("unidade"),
                    boleto["whatsapp"],
                    etapa_codigo,
                    etapa_descricao,
                    boleto.get("dias_atraso"),
                    boleto.get("valor"),
                    boleto.get("vencimento"),
                    texto,
                    1 if dry_run else 0,
                    1 if sucesso else 0,
                    evolution_message_id,
                    evolution_response,
                    erro,
                ),
            )

    # ─── Cap diário ───

    def enviados_hoje(self) -> int:
        with self._cursor() as c:
            c.execute(
                """SELECT COUNT(*) FROM envios
                   WHERE date(enviado_em) = date('now', 'localtime')
                   AND sucesso = 1 AND dry_run = 0"""
            )
            return c.fetchone()[0]

    def total_envios(self) -> int:
        with self._cursor() as c:
            c.execute("SELECT COUNT(*) FROM envios WHERE sucesso = 1 AND dry_run = 0")
            return c.fetchone()[0]

    # ─── Blacklist ───

    def esta_na_blacklist(self, whatsapp: str) -> bool:
        with self._cursor() as c:
            c.execute("SELECT 1 FROM blacklist WHERE whatsapp = ?", (whatsapp,))
            return c.fetchone() is not None

    def adicionar_blacklist(self, whatsapp: str, motivo: str = ""):
        with self._cursor() as c:
            c.execute(
                "INSERT OR REPLACE INTO blacklist (whatsapp, motivo) VALUES (?, ?)",
                (whatsapp, motivo),
            )

    def remover_blacklist(self, whatsapp: str):
        with self._cursor() as c:
            c.execute("DELETE FROM blacklist WHERE whatsapp = ?", (whatsapp,))

    def listar_blacklist(self) -> list:
        with self._cursor() as c:
            c.execute("SELECT whatsapp FROM blacklist ORDER BY adicionado_em DESC")
            return [r[0] for r in c.fetchall()]

    def total_blacklist(self) -> int:
        with self._cursor() as c:
            c.execute("SELECT COUNT(*) FROM blacklist")
            return c.fetchone()[0]

    # ─── Scraper runs ───

    def registrar_scraper_inicio(self) -> int:
        with self._cursor() as c:
            c.execute("INSERT INTO scraper_runs (sucesso) VALUES (0)")
            return c.lastrowid

    def registrar_scraper_fim(self, run_id: int, sucesso: bool, boletos: int = 0, erro: str = None):
        with self._cursor() as c:
            c.execute(
                """UPDATE scraper_runs
                   SET concluido_em=CURRENT_TIMESTAMP, sucesso=?, boletos_coletados=?, erro=?
                   WHERE id=?""",
                (1 if sucesso else 0, boletos, erro, run_id),
            )

    # ─── Relatórios ───

    def envios_recentes(self, limit: int = 20) -> list:
        with self._cursor() as c:
            c.execute(
                """SELECT enviado_em, nome, unidade, etapa_codigo, sucesso, dry_run, erro
                   FROM envios
                   ORDER BY enviado_em DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(r) for r in c.fetchall()]

    # ─── Mensagens recebidas (webhook auto-responder) ───

    def ja_processou(self, message_id: str) -> bool:
        """Retorna True se já registrou essa message_id (idempotência do webhook)."""
        if not message_id:
            return False
        with self._cursor() as c:
            c.execute(
                "SELECT 1 FROM mensagens_recebidas WHERE message_id = ?",
                (message_id,),
            )
            return c.fetchone() is not None

    def registrar_mensagem_recebida(
        self,
        message_id: str,
        phone: str,
        sender_name: Optional[str],
        texto: str,
        classificacao: Optional[dict] = None,
    ):
        """
        Registra mensagem recebida + resultado da classificação.

        classificacao = {
            "intencao": str,
            "resposta_texto": str | None,
            "acao": str,            # "responder_auto" | "escalar_humano" | "ignorar"
            "confianca": float,
        }
        """
        cls = classificacao or {}
        acao = cls.get("acao") or ""
        respondido_auto = 1 if acao == "responder_auto" else 0
        escalado = 1 if acao == "escalar_humano" else 0
        with self._cursor() as c:
            c.execute(
                """
                INSERT OR IGNORE INTO mensagens_recebidas (
                    message_id, phone, sender_name, texto_recebido,
                    intencao, resposta_texto, acao, confianca,
                    respondido_automaticamente, escalado_humano
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    phone,
                    sender_name,
                    texto,
                    cls.get("intencao"),
                    cls.get("resposta_texto"),
                    acao,
                    cls.get("confianca"),
                    respondido_auto,
                    escalado,
                ),
            )

    def conversas_recentes(self, limit: int = 50) -> list:
        """Últimas mensagens recebidas + resposta auto (mais recentes primeiro)."""
        with self._cursor() as c:
            c.execute(
                """SELECT id, message_id, phone, sender_name, texto_recebido,
                          intencao, resposta_texto, acao, confianca,
                          respondido_automaticamente, escalado_humano, recebido_em
                   FROM mensagens_recebidas
                   ORDER BY recebido_em DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(r) for r in c.fetchall()]

    # ─── Conversas (contexto por telefone) ───

    def upsert_conversa(
        self,
        telefone: str,
        ultimo_intent: Optional[str] = None,
        ultima_mensagem: Optional[str] = None,
        nome: Optional[str] = None,
        unidade: Optional[str] = None,
        aguardando_comprovante: Optional[bool] = None,
        boleto_id_aberto: Optional[str] = None,
    ):
        """
        Cria ou atualiza a linha de conversa pra um telefone. Mantem os campos
        que ja existem se passar None.
        """
        if not telefone:
            return
        with self._cursor() as c:
            c.execute("SELECT telefone FROM conversas WHERE telefone = ?", (telefone,))
            existe = c.fetchone() is not None

            if not existe:
                c.execute(
                    """
                    INSERT INTO conversas (
                        telefone, nome, unidade, ultimo_intent,
                        ultima_mensagem, ultima_mensagem_em,
                        aguardando_comprovante, boleto_id_aberto,
                        criado_em, atualizado_em
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?,
                              CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        telefone,
                        nome,
                        unidade,
                        ultimo_intent,
                        ultima_mensagem,
                        1 if aguardando_comprovante else 0,
                        boleto_id_aberto,
                    ),
                )
                return

            # Update parcial — so atualiza o que foi passado
            campos = ["ultima_mensagem_em = CURRENT_TIMESTAMP", "atualizado_em = CURRENT_TIMESTAMP"]
            valores = []
            if ultimo_intent is not None:
                campos.append("ultimo_intent = ?")
                valores.append(ultimo_intent)
            if ultima_mensagem is not None:
                campos.append("ultima_mensagem = ?")
                valores.append(ultima_mensagem)
            if nome is not None:
                campos.append("nome = ?")
                valores.append(nome)
            if unidade is not None:
                campos.append("unidade = ?")
                valores.append(unidade)
            if aguardando_comprovante is not None:
                campos.append("aguardando_comprovante = ?")
                valores.append(1 if aguardando_comprovante else 0)
            if boleto_id_aberto is not None:
                campos.append("boleto_id_aberto = ?")
                valores.append(boleto_id_aberto)

            valores.append(telefone)
            c.execute(f"UPDATE conversas SET {', '.join(campos)} WHERE telefone = ?", valores)

    # Alias mais explicitos pra compat com spec
    def criar_conversa(self, telefone: str, **kwargs):
        return self.upsert_conversa(telefone, **kwargs)

    def atualizar_conversa(self, telefone: str, **kwargs):
        return self.upsert_conversa(telefone, **kwargs)

    def marcar_conversa_escalada(self, telefone: str, motivo: str = ""):
        """Marca uma conversa como escalada pra humano."""
        if not telefone:
            return
        with self._cursor() as c:
            c.execute("SELECT telefone FROM conversas WHERE telefone = ?", (telefone,))
            if not c.fetchone():
                c.execute(
                    """INSERT INTO conversas (telefone, escalado_humano, motivo_escalacao,
                                              criado_em, atualizado_em)
                       VALUES (?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                    (telefone, motivo),
                )
            else:
                c.execute(
                    """UPDATE conversas
                       SET escalado_humano = 1, motivo_escalacao = ?,
                           atualizado_em = CURRENT_TIMESTAMP
                       WHERE telefone = ?""",
                    (motivo, telefone),
                )

    def listar_conversas(self, limit: int = 50) -> list:
        """Conversas mais recentes (last 50 por padrao)."""
        with self._cursor() as c:
            c.execute(
                """SELECT telefone, nome, unidade, ultimo_intent, ultima_mensagem,
                          ultima_mensagem_em, aguardando_comprovante, escalado_humano,
                          motivo_escalacao, boleto_id_aberto, atualizado_em
                   FROM conversas
                   ORDER BY atualizado_em DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(r) for r in c.fetchall()]

    def historico_conversa(self, telefone: str, limit: int = 100) -> list:
        """Historico completo de mensagens (recebidas + enviadas) de um telefone."""
        with self._cursor() as c:
            c.execute(
                """SELECT 'recebida' AS direcao, recebido_em AS quando,
                          texto_recebido AS texto, intencao, acao,
                          escalado_humano, resposta_texto
                   FROM mensagens_recebidas
                   WHERE phone = ?
                   UNION ALL
                   SELECT 'enviada' AS direcao, enviado_em AS quando,
                          texto_enviado AS texto, etapa_codigo AS intencao,
                          NULL AS acao, NULL AS escalado_humano, NULL AS resposta_texto
                   FROM envios
                   WHERE whatsapp = ?
                   ORDER BY quando DESC
                   LIMIT ?""",
                (telefone, telefone, limit),
            )
            return [dict(r) for r in c.fetchall()]

    # ─── Comprovantes ───

    def registrar_comprovante(
        self,
        telefone: str,
        arquivo: str,
        intent: str = "comprovante",
        valido: bool = False,
        valor_extraido: Optional[float] = None,
        data_extraida: Optional[str] = None,
        boleto_id_associado: Optional[str] = None,
        raw_text: str = "",
        motivo: str = "",
    ):
        with self._cursor() as c:
            c.execute(
                """
                INSERT INTO comprovantes (
                    telefone, arquivo, intent, valido,
                    valor_extraido, data_extraida,
                    boleto_id_associado, raw_text, motivo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telefone,
                    arquivo,
                    intent,
                    1 if valido else 0,
                    valor_extraido,
                    data_extraida,
                    boleto_id_associado,
                    (raw_text or "")[:5000],
                    motivo,
                ),
            )

    def comprovantes_recentes(self, limit: int = 50) -> list:
        with self._cursor() as c:
            c.execute(
                """SELECT id, telefone, arquivo, intent, valido,
                          valor_extraido, data_extraida, boleto_id_associado,
                          motivo, criado_em
                   FROM comprovantes
                   ORDER BY criado_em DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(r) for r in c.fetchall()]

    def resumo_diario(self, dia: Optional[date] = None) -> dict:
        dia = dia or date.today()
        with self._cursor() as c:
            c.execute(
                """SELECT
                    SUM(CASE WHEN sucesso=1 AND dry_run=0 THEN 1 ELSE 0 END) AS enviados,
                    SUM(CASE WHEN sucesso=0 AND dry_run=0 THEN 1 ELSE 0 END) AS falhas,
                    SUM(CASE WHEN dry_run=1 THEN 1 ELSE 0 END) AS dry_run,
                    COUNT(*) AS total
                   FROM envios
                   WHERE date(enviado_em) = ?""",
                (dia.isoformat(),),
            )
            return dict(c.fetchone() or {})


# ─── CLI de inspeção ───
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    state = State(os.getenv("DATABASE_PATH", "./data/state.db"))

    cmd = sys.argv[1] if len(sys.argv) > 1 else "--recent"

    if cmd == "--recent":
        envios = state.envios_recentes(20)
        print(f"\n📋 Últimos {len(envios)} envios:")
        print("-" * 80)
        for e in envios:
            status = "✅" if e["sucesso"] else "❌"
            dr = " [DRY]" if e["dry_run"] else ""
            print(f"{e['enviado_em']} {status}{dr} | {e['etapa_codigo']:5} | {e['nome']} ({e['unidade']})")
            if e["erro"]:
                print(f"   ⚠️  {e['erro']}")

    elif cmd == "--hoje":
        resumo = state.resumo_diario()
        print(f"\n📊 Resumo de hoje:")
        print(f"   Enviados (real):  {resumo.get('enviados') or 0}")
        print(f"   Falhas:           {resumo.get('falhas') or 0}")
        print(f"   DRY-RUN:          {resumo.get('dry_run') or 0}")
        print(f"   Total registros:  {resumo.get('total') or 0}")

    else:
        print(f"Comando desconhecido: {cmd}")
        print("Use: --recent | --hoje")
