"""Agregações para dashboard, gráficos e fechamento mensal."""

import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy import func

from ..extensions import db
from ..models import Departamento, Oficio
from .formatacao import nome_mes

SEM_ASSESSOR = "Sem assessor"
SIMILARIDADE_MINIMA = 0.82


def canonizar_assessor(nome: str | None) -> str:
    """Remove acentos e espaços extras; vazio vira 'Sem assessor'."""
    if not nome or not str(nome).strip():
        return SEM_ASSESSOR
    texto = unicodedata.normalize("NFKD", str(nome).strip()).encode("ASCII", "ignore").decode()
    return " ".join(texto.split())


def _parecidos(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return a == b or a in b or b in a or SequenceMatcher(None, a, b).ratio() >= SIMILARIDADE_MINIMA


def agrupar_assessores(contagens: dict[str, int]) -> list[dict]:
    """Junta variações do mesmo nome (ex.: 'Joao Silva' e 'João  Silva')."""
    agrupado: list[list] = []
    for nome, qtd in sorted(contagens.items(), key=lambda x: -x[1]):
        if nome == SEM_ASSESSOR:
            agrupado.append([nome, qtd])
            continue
        for item in agrupado:
            if item[0] != SEM_ASSESSOR and _parecidos(nome, item[0]):
                item[1] += qtd
                break
        else:
            agrupado.append([nome, qtd])
    return [{"nome": n, "count": c} for n, c in sorted(agrupado, key=lambda x: -x[1])]


def _filtrar_periodo(q, inicio=None, fim=None):
    if inicio:
        q = q.filter(Oficio.data_criacao >= inicio)
    if fim:
        q = q.filter(Oficio.data_criacao < fim)
    return q


def por_secretaria(inicio=None, fim=None) -> list[dict]:
    contagem = dict(
        _filtrar_periodo(
            db.session.query(Oficio.departamento_id, func.count(Oficio.id)), inicio, fim
        ).group_by(Oficio.departamento_id).all()
    )
    return sorted(
        [{"sigla": d.sigla, "nome": d.nome, "count": int(contagem.get(d.id, 0))}
         for d in Departamento.query.order_by(Departamento.nome).all()],
        key=lambda x: (-x["count"], x["sigla"]),
    )


def por_assessor(inicio=None, fim=None) -> list[dict]:
    q = _filtrar_periodo(
        db.session.query(Oficio.assessor_nome, func.count(Oficio.id)), inicio, fim
    ).group_by(Oficio.assessor_nome)
    contagens: dict[str, int] = {}
    for nome, qtd in q.all():
        chave = canonizar_assessor(nome)
        contagens[chave] = contagens.get(chave, 0) + int(qtd)
    return agrupar_assessores(contagens)


def dados_graficos(inicio=None, fim=None) -> dict:
    return {"secretarias": por_secretaria(inicio, fim), "assessores": por_assessor(inicio, fim)}


def _somar_mes(ano: int, mes: int, delta: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + delta
    return total // 12, total % 12 + 1


def serie_mensal(meses: int = 12, referencia: datetime | None = None) -> dict:
    """Quantidade de ofícios por mês nos últimos N meses (inclui meses vazios)."""
    ref = referencia or datetime.now()
    ano_ini, mes_ini = _somar_mes(ref.year, ref.month, -(meses - 1))
    inicio = datetime(ano_ini, mes_ini, 1)
    datas = db.session.query(Oficio.data_criacao, Oficio.executado).filter(
        Oficio.data_criacao >= inicio
    ).all()

    chaves = [_somar_mes(ano_ini, mes_ini, i) for i in range(meses)]
    total = dict.fromkeys(chaves, 0)
    executados = dict.fromkeys(chaves, 0)
    for data, exec_ in datas:
        chave = (data.year, data.month)
        if chave in total:
            total[chave] += 1
            executados[chave] += 1 if exec_ else 0

    return {
        "labels": [f"{nome_mes(m)[:3].capitalize()}/{str(a)[2:]}" for a, m in chaves],
        "total": [total[c] for c in chaves],
        "executados": [executados[c] for c in chaves],
    }


def _contar_mes(ano: int, mes: int) -> tuple[int, int]:
    inicio = datetime(ano, mes, 1)
    fa, fm = _somar_mes(ano, mes, 1)
    fim = datetime(fa, fm, 1)
    q = _filtrar_periodo(Oficio.query, inicio, fim)
    return q.count(), q.filter(Oficio.executado.is_(True)).count()


def indicadores(referencia: datetime | None = None) -> dict:
    ref = referencia or datetime.now()
    total_mes, exec_mes = _contar_mes(ref.year, ref.month)
    ant_ano, ant_mes = _somar_mes(ref.year, ref.month, -1)
    total_ant, _ = _contar_mes(ant_ano, ant_mes)

    total_geral = Oficio.query.count()
    pendentes = Oficio.query.filter(Oficio.executado.is_(False)).count()
    executados = total_geral - pendentes

    variacao = None
    if total_ant:
        variacao = round((total_mes - total_ant) / total_ant * 100)

    return {
        "mes_nome": nome_mes(ref.month, capitalizar=True),
        "total_mes": total_mes,
        "executados_mes": exec_mes,
        "variacao_mes": variacao,
        "total_geral": total_geral,
        "pendentes": pendentes,
        "executados": executados,
        "taxa_execucao": round(executados / total_geral * 100) if total_geral else 0,
    }


def meses_disponiveis() -> list[tuple[int, int]]:
    datas = db.session.query(Oficio.data_criacao).all()
    meses = {(d.year, d.month) for (d,) in datas if d}
    hoje = datetime.now()
    meses.add((hoje.year, hoje.month))
    return sorted(meses, reverse=True)


def fechamento_mensal(ano: int, mes: int) -> dict:
    inicio = datetime(ano, mes, 1)
    fa, fm = _somar_mes(ano, mes, 1)
    fim = datetime(fa, fm, 1)
    oficios = (
        _filtrar_periodo(Oficio.query, inicio, fim)
        .order_by(Oficio.sequencial.desc(), Oficio.data_criacao.desc())
        .all()
    )

    total = len(oficios)
    executados = sum(1 for o in oficios if o.executado)
    pendentes = total - executados

    def pct(n):
        return round(n / total * 100, 1) if total else 0

    secretarias = [s | {"percentage": pct(s["count"])}
                   for s in por_secretaria(inicio, fim) if s["count"]]
    assessores = [a | {"percentage": pct(a["count"])} for a in por_assessor(inicio, fim)]
    municipes = {" ".join(o.municipe_nome.upper().split())
                 for o in oficios if o.municipe_nome and o.municipe_nome.strip()}

    resumo = (
        f"Em {nome_mes(mes)} de {ano} foram registrados {total} ofício(s), "
        f"dos quais {executados} ({pct(executados)}%) já foram executados e "
        f"{pendentes} ({pct(pendentes)}%) seguem pendentes."
    )
    if secretarias:
        top = secretarias[0]
        resumo += (f" A secretaria mais demandada foi {top['nome']} ({top['sigla']}), "
                   f"com {top['count']} pedido(s).")
    if municipes:
        resumo += f" Foram atendidos {len(municipes)} munícipe(s) diferentes."

    return {
        "ano": ano,
        "mes": mes,
        "nome_mes": nome_mes(mes, capitalizar=True),
        "oficios": oficios,
        "total": total,
        "executados": executados,
        "pendentes": pendentes,
        "pct_executados": pct(executados),
        "pct_pendentes": pct(pendentes),
        "secretarias": secretarias,
        "assessores": assessores,
        "total_municipes": len(municipes),
        "resumo": resumo,
    }


def oficios_do_assessor(nome: str, inicio=None, fim=None) -> list[Oficio]:
    q = _filtrar_periodo(Oficio.query, inicio, fim)
    if nome == SEM_ASSESSOR:
        q = q.filter((Oficio.assessor_nome.is_(None)) | (Oficio.assessor_nome == ""))
    else:
        nomes = [n for (n,) in db.session.query(Oficio.assessor_nome).distinct()
                 if n and _parecidos(canonizar_assessor(n), nome)]
        if not nomes:
            return []
        q = q.filter(Oficio.assessor_nome.in_(nomes))
    return q.order_by(Oficio.ano.desc(), Oficio.sequencial.desc()).limit(300).all()


def oficios_da_secretaria(sigla: str, inicio=None, fim=None) -> tuple[Departamento | None, list]:
    dep = Departamento.query.filter(func.lower(Departamento.sigla) == sigla.lower()).first()
    if not dep:
        return None, []
    q = _filtrar_periodo(Oficio.query.filter_by(departamento_id=dep.id), inicio, fim)
    return dep, q.order_by(Oficio.ano.desc(), Oficio.sequencial.desc()).limit(300).all()
