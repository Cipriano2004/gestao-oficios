"""Copia os dados do sistema antigo (SQLite) para o banco novo (MySQL/MariaDB).

Uso pessoal — este script não envia nada para lugar nenhum, só lê o arquivo .db antigo
e grava no banco configurado em DATABASE_URL (.env).

    python scripts/migrar_sqlite_para_mysql.py caminho/para/gestao_oficios.db
    python scripts/migrar_sqlite_para_mysql.py caminho/para/gestao_oficios.db --limpar

Antes: rode `flask db upgrade` para criar as tabelas no banco novo.
--limpar apaga os dados de ofícios, modelos e secretarias do banco novo antes de copiar.
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    AssessorPadrao,
    Departamento,
    NumeracaoConfig,
    NumeroReserva,
    Oficio,
    Secretario,
    TemplateOficio,
)
from app.services.numeracao import formatar_numero, parse_numero  # noqa: E402

TABELAS = [Oficio, TemplateOficio, Secretario, AssessorPadrao, NumeroReserva,
           NumeracaoConfig, Departamento]


def _linhas(con: sqlite3.Connection, tabela: str) -> list[dict]:
    existe = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                         (tabela,)).fetchone()
    if not existe:
        return []
    return [dict(r) for r in con.execute(f"SELECT * FROM {tabela}")]  # noqa: S608


def _data(valor) -> datetime | None:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(valor), fmt)
        except ValueError:
            continue
    return None


def _cortar(valor, limite):
    return (valor or "")[:limite] if valor is not None else None


def migrar(caminho_sqlite: str, limpar: bool = False) -> dict:
    con = sqlite3.connect(caminho_sqlite)
    con.row_factory = sqlite3.Row
    resumo = {}

    if limpar:
        for modelo in TABELAS:
            modelo.query.delete()
        db.session.commit()

    # Secretarias (sigla precisa ser única no banco novo)
    siglas = set()
    for r in _linhas(con, "departamento"):
        sigla = (r["sigla"] or f"DEP{r['id']}")[:10]
        while sigla in siglas:
            sigla = f"{sigla[:8]}{r['id']}"[:10]
        siglas.add(sigla)
        db.session.add(Departamento(id=r["id"], nome=r["nome"][:100], sigla=sigla))
    db.session.commit()
    resumo["secretarias"] = len(siglas)

    for r in _linhas(con, "secretario"):
        db.session.add(Secretario(id=r["id"], nome=r["nome"][:100], cargo=r["cargo"][:100],
                                  departamento_id=r["departamento_id"]))
    for r in _linhas(con, "template_oficio"):
        db.session.add(TemplateOficio(id=r["id"], titulo=r["titulo"][:200],
                                      assunto=r["assunto"][:300], corpo_texto=r["corpo_texto"],
                                      departamento_id=r["departamento_id"]))
    for r in _linhas(con, "assessor_padrao"):
        db.session.add(AssessorPadrao(id=r["id"], nome=r["nome"][:100],
                                      departamento_id=r.get("departamento_id")))
    for r in _linhas(con, "numero_reserva"):
        db.session.add(NumeroReserva(ano=r["ano"], sequencial=r["sequencial"],
                                     motivo=_cortar(r.get("motivo"), 200),
                                     criado_em=_data(r.get("criado_em"))))
    for r in _linhas(con, "numeracao_config"):
        db.session.add(NumeracaoConfig(ano=r["ano"], offset=r["offset"] or 0))
    db.session.commit()

    usados: set[tuple[int, int]] = set()
    fora_do_padrao = 0
    oficios = _linhas(con, "oficio")
    for r in oficios:
        partes = parse_numero(r["numero"])
        ano = seq = None
        numero = r["numero"]
        if partes and (partes[1], partes[0]) not in usados:
            seq, ano = partes
            usados.add((ano, seq))
            numero = formatar_numero(seq, ano)
        if ano is None:
            fora_do_padrao += 1
        data = _data(r.get("data_criacao")) or datetime.now()
        db.session.add(Oficio(
            id=r["id"], numero=numero[:50], ano=ano, sequencial=seq,
            assunto=_cortar(r["assunto"], 300), destinatario=_cortar(r["destinatario"], 100),
            cargo_destinatario=_cortar(r.get("cargo_destinatario"), 100),
            orgao_destinatario=_cortar(r.get("orgao_destinatario"), 100),
            endereco=_cortar(r.get("endereco"), 200),
            numero_endereco=_cortar(r.get("numero_endereco"), 20),
            bairro=_cortar(r.get("bairro"), 100), em_frente=_cortar(r.get("em_frente"), 200),
            assessor_nome=_cortar(r.get("assessor_nome"), 100),
            municipe_nome=_cortar(r.get("municipe_nome"), 120),
            municipe_telefone=_cortar(r.get("municipe_telefone"), 30),
            municipe_tratamento=_cortar(r.get("municipe_tratamento"), 20),
            executado=bool(r.get("executado")),
            corpo_oficio=r.get("corpo_oficio"),
            nome_responsavel=_cortar(r.get("nome_responsavel"), 100),
            cargo_responsavel=_cortar(r.get("cargo_responsavel"), 100),
            data_criacao=data, atualizado_em=data,
            departamento_id=r["departamento_id"], secretario_id=r.get("secretario_id"),
        ))
    db.session.commit()
    resumo["oficios"] = len(oficios)
    resumo["oficios_numero_fora_do_padrao"] = fora_do_padrao
    con.close()
    return resumo


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sqlite", help="arquivo .db do sistema antigo")
    parser.add_argument("--limpar", action="store_true", help="limpa os dados do banco novo antes")
    args = parser.parse_args()

    if not Path(args.sqlite).is_file():
        sys.exit(f"Arquivo não encontrado: {args.sqlite}")

    app = create_app()
    with app.app_context():
        resumo = migrar(args.sqlite, limpar=args.limpar)
    print("Migração concluída:", resumo)
    print("Crie o usuário administrador com: flask criar-admin")


if __name__ == "__main__":
    main()
