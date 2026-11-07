from datetime import datetime

from flask import Blueprint, render_template, request, send_file

from ...seguranca import exigir_login
from ...services import auditoria, exportacao, relatorios
from ...services import oficios as svc
from ...services.formatacao import nome_mes

bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")
bp.before_request(exigir_login)


@bp.get("/")
def graficos():
    meses = relatorios.meses_disponiveis()
    return render_template(
        "relatorios/graficos.html",
        meses=[(f"{a}-{m:02d}", f"{nome_mes(m, True)}/{a}") for a, m in meses],
        mes=request.args.get("mes", ""),
    )


@bp.get("/fechamento")
def fechamento():
    hoje = datetime.now()
    ano = request.args.get("ano", hoje.year, type=int)
    mes = request.args.get("mes", hoje.month, type=int)
    if not (1 <= mes <= 12 and 2000 <= ano <= 2100):
        ano, mes = hoje.year, hoje.month
    return render_template(
        "relatorios/fechamento.html",
        r=relatorios.fechamento_mensal(ano, mes),
        meses=relatorios.meses_disponiveis(),
        nome_mes=nome_mes,
        gerado_em=hoje,
    )


@bp.get("/exportar")
def exportar():
    filtros = svc.Filtros.de_args(request.args)
    oficios = svc.consultar(filtros).all()
    sufixo = f"_{filtros.mes}" if filtros.mes else ""
    auditoria.registrar("EXPORTAR", "oficio", None,
                        {"quantidade": len(oficios), "filtros": request.args.to_dict()})
    return send_file(
        exportacao.gerar_planilha(oficios),
        as_attachment=True,
        download_name=exportacao.nome_planilha(sufixo),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
