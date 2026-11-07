"""Endpoints JSON usados pelos gráficos (todos exigem login)."""

from flask import Blueprint, jsonify, request, url_for

from ...seguranca import exigir_login
from ...services import relatorios
from ...services.oficios import periodo_do_mes

bp = Blueprint("api", __name__, url_prefix="/api")
bp.before_request(exigir_login)


def _periodo():
    periodo = periodo_do_mes(request.args.get("mes", ""))
    return periodo if periodo else (None, None)


def _resumo(o) -> dict:
    return {
        "id": o.id,
        "numero": o.numero,
        "assunto": o.assunto,
        "secretaria": o.departamento.sigla if o.departamento else "",
        "status": o.status,
        "url": url_for("oficios.detalhe", oficio_id=o.id),
    }


@bp.get("/graficos")
def graficos():
    inicio, fim = _periodo()
    return jsonify(relatorios.dados_graficos(inicio, fim))


@bp.get("/oficios-por-assessor")
def oficios_por_assessor():
    nome = (request.args.get("nome") or "").strip()
    if not nome:
        return jsonify(oficios=[])
    inicio, fim = _periodo()
    return jsonify(oficios=[_resumo(o) for o in relatorios.oficios_do_assessor(nome, inicio, fim)])


@bp.get("/oficios-por-secretaria")
def oficios_por_secretaria():
    sigla = (request.args.get("sigla") or "").strip()
    inicio, fim = _periodo()
    dep, oficios = relatorios.oficios_da_secretaria(sigla, inicio, fim)
    if not dep:
        return jsonify(erro="Secretaria não encontrada."), 404
    return jsonify(secretaria={"sigla": dep.sigla, "nome": dep.nome},
                   oficios=[_resumo(o) for o in oficios])
