from datetime import datetime
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField
from wtforms.validators import DataRequired, Email, Length

from ...extensions import db, limiter
from ...models import Usuario
from ...services import auditoria

bp = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    email = EmailField("E-mail", validators=[DataRequired(), Email(), Length(max=160)],
                       filters=[lambda v: v.strip() if isinstance(v, str) else v])
    senha = PasswordField("Senha", validators=[DataRequired(), Length(max=128)])
    lembrar = BooleanField("Manter conectado")


def _destino_seguro(destino: str | None) -> str:
    """Evita open redirect: só aceita caminhos relativos do próprio sistema."""
    if destino:
        partes = urlsplit(destino)
        if not partes.netloc and not partes.scheme and destino.startswith("/") \
                and not destino.startswith("//"):
            return destino
    return url_for("main.dashboard")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.ativo and usuario.checar_senha(form.senha.data):
            login_user(usuario, remember=form.lembrar.data)
            usuario.ultimo_login = datetime.now()
            db.session.commit()
            auditoria.registrar("LOGIN", "usuario", usuario.id, usuario=usuario)
            return redirect(_destino_seguro(request.args.get("next")))

        # mensagem genérica: não revela se o e-mail existe
        auditoria.registrar("LOGIN_FALHOU", "usuario", getattr(usuario, "id", None),
                            email=email, usuario=False)
        flash("E-mail ou senha inválidos.", "danger")

    return render_template("auth/login.html", form=form)


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        auditoria.registrar("LOGOUT", "usuario", current_user.id)
        logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))
