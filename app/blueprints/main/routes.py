from flask import Blueprint, render_template

from ...models import Oficio
from ...seguranca import exigir_login
from ...services import relatorios

bp = Blueprint("main", __name__)
bp.before_request(exigir_login)


@bp.get("/")
def dashboard():
    ultimos = Oficio.query.order_by(Oficio.data_criacao.desc()).limit(8).all()
    return render_template(
        "main/dashboard.html",
        kpi=relatorios.indicadores(),
        serie=relatorios.serie_mensal(12),
        secretarias=relatorios.por_secretaria()[:8],
        ultimos=ultimos,
    )
