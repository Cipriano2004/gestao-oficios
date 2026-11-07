from flask import Blueprint, flash, redirect, render_template, request, url_for

from ...seguranca import SO_ADMIN, exigir_login, requer_perfil
from ...services import auditoria, numeracao

bp = Blueprint("numeracao", __name__, url_prefix="/numeracao")
bp.before_request(exigir_login)


def _ano_param() -> int:
    ano = request.values.get("ano", type=int)
    return ano if ano and 2000 <= ano <= 2100 else numeracao.ano_atual()


@bp.get("/")
def controle():
    return render_template("numeracao/controle.html", mapa=numeracao.mapa_do_ano(_ano_param()),
                           ano_atual=numeracao.ano_atual())


@bp.post("/proximo")
@requer_perfil(*SO_ADMIN)
def definir_proximo():
    ano = _ano_param()
    valor = request.form.get("novo_proximo", type=int)
    try:
        numeracao.definir_proximo_desejado(ano, valor or 0)
    except numeracao.NumeroInvalido as erro:
        flash(str(erro), "danger")
    else:
        auditoria.registrar("CONFIG", "numeracao", None, {"ano": ano, "proximo": valor})
        flash(f"Próximo número ajustado para {numeracao.formatar_numero(valor, ano)}.", "success")
    return redirect(url_for("numeracao.controle", ano=ano))


@bp.post("/reservar")
@requer_perfil(*SO_ADMIN)
def reservar():
    ano = _ano_param()
    seq = request.form.get("sequencial", type=int) or 0
    try:
        numeracao.reservar(ano, seq, (request.form.get("motivo") or "").strip())
    except numeracao.NumeroInvalido as erro:
        flash(str(erro), "danger")
    else:
        auditoria.registrar("RESERVAR", "numeracao", None, {"numero": f"{seq:03d}/{ano}"})
        flash(f"Número {seq:03d}/{ano} marcado como usado fora do sistema.", "success")
    return redirect(url_for("numeracao.controle", ano=ano))


@bp.post("/liberar")
@requer_perfil(*SO_ADMIN)
def liberar():
    ano = _ano_param()
    seq = request.form.get("sequencial", type=int) or 0
    if numeracao.liberar(ano, seq):
        auditoria.registrar("LIBERAR", "numeracao", None, {"numero": f"{seq:03d}/{ano}"})
        flash(f"Reserva do número {seq:03d}/{ano} removida.", "success")
    else:
        flash("Reserva não encontrada.", "warning")
    return redirect(url_for("numeracao.controle", ano=ano))
