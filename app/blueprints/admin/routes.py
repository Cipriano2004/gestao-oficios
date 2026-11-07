"""Administração: usuários e trilha de auditoria (somente admin)."""

from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ...extensions import db
from ...models import ACOES, PERFIS, LogAuditoria, Usuario
from ...seguranca import SO_ADMIN, exigir_login, requer_perfil
from ...services import auditoria
from ...services.usuarios import UsuarioInvalido, criar_usuario, validar_senha

bp = Blueprint("admin", __name__, url_prefix="/admin")
bp.before_request(exigir_login)


@bp.before_request
def _somente_admin():
    if current_user.is_authenticated and not current_user.tem_perfil(*SO_ADMIN):
        abort(403)


@bp.route("/usuarios", methods=["GET", "POST"])
@requer_perfil(*SO_ADMIN)
def usuarios():
    if request.method == "POST":
        try:
            novo = criar_usuario(
                nome=request.form.get("nome", ""),
                email=request.form.get("email", ""),
                senha=request.form.get("senha", ""),
                perfil=request.form.get("perfil", "assessor"),
            )
        except UsuarioInvalido as erro:
            flash(str(erro), "danger")
        else:
            auditoria.registrar("CRIAR", "usuario", novo.id,
                                {"email": novo.email, "perfil": novo.perfil})
            flash(f"Usuário {novo.email} criado.", "success")
            return redirect(url_for("admin.usuarios"))
    return render_template("admin/usuarios.html",
                           usuarios=Usuario.query.order_by(Usuario.nome).all(), perfis=PERFIS)


@bp.post("/usuarios/<int:usuario_id>/alterar")
@requer_perfil(*SO_ADMIN)
def alterar_usuario(usuario_id: int):
    usuario = db.session.get(Usuario, usuario_id) or abort(404)
    acao = request.form.get("acao")

    if usuario.id == current_user.id and acao in ("desativar", "perfil"):
        flash("Você não pode desativar nem rebaixar o próprio usuário.", "warning")
        return redirect(url_for("admin.usuarios"))

    detalhes = {"email": usuario.email, "acao": acao}
    if acao == "desativar":
        usuario.ativo = False
    elif acao == "ativar":
        usuario.ativo = True
    elif acao == "perfil" and request.form.get("perfil") in PERFIS:
        usuario.perfil = request.form["perfil"]
        detalhes["perfil"] = usuario.perfil
    elif acao == "senha":
        try:
            validar_senha(request.form.get("senha", ""))
        except UsuarioInvalido as erro:
            flash(str(erro), "danger")
            return redirect(url_for("admin.usuarios"))
        usuario.set_senha(request.form["senha"])
    else:
        abort(400)

    auditoria.registrar("EDITAR", "usuario", usuario.id, detalhes, commit=False)
    db.session.commit()
    flash("Usuário atualizado.", "success")
    return redirect(url_for("admin.usuarios"))


@bp.get("/auditoria")
@requer_perfil(*SO_ADMIN)
def log_auditoria():
    q = LogAuditoria.query
    acao = request.args.get("acao", "")
    usuario_id = request.args.get("usuario_id", type=int)
    dias = request.args.get("dias", 30, type=int)

    if acao in ACOES:
        q = q.filter(LogAuditoria.acao == acao)
    if usuario_id:
        q = q.filter(LogAuditoria.usuario_id == usuario_id)
    if dias and dias > 0:
        q = q.filter(LogAuditoria.criado_em >= datetime.now() - timedelta(days=dias))

    paginacao = q.order_by(LogAuditoria.criado_em.desc()).paginate(
        page=request.args.get("pagina", 1, type=int), per_page=40, error_out=False)
    falhas_24h = LogAuditoria.query.filter(
        LogAuditoria.acao == "LOGIN_FALHOU",
        LogAuditoria.criado_em >= datetime.now() - timedelta(hours=24),
    ).count()
    return render_template(
        "admin/auditoria.html", paginacao=paginacao, acoes=ACOES, acao=acao,
        usuarios=Usuario.query.order_by(Usuario.nome).all(), usuario_id=usuario_id,
        dias=dias, falhas_24h=falhas_24h,
    )
