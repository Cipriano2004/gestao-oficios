"""Application factory do sistema Gestão de Ofícios."""

import os

from flask import Flask, jsonify, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import text

from .config import CONFIGS
from .extensions import csrf, db, limiter, login_manager, migrate

CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "production")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIGS.get(config_name, CONFIGS["production"]))

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY não definida. Configure-a no arquivo .env.")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL não definida. Configure-a no arquivo .env.")

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql"):
        # READ COMMITTED: cada consulta enxerga o último dado confirmado (necessário para a
        # numeração com SELECT ... FOR UPDATE funcionar bem com vários usuários ao mesmo tempo)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            **app.config["SQLALCHEMY_ENGINE_OPTIONS"],
            "isolation_level": "READ COMMITTED",
        }

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    from . import models  # noqa: F401  (registra os models no metadata)

    _registrar_blueprints(app)
    _registrar_handlers(app)
    _registrar_cabecalhos_seguranca(app)
    _registrar_contexto_templates(app)
    _registrar_comandos(app)

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok", db="ok")
        except Exception:
            return jsonify(status="erro", db="indisponivel"), 503

    return app


def _registrar_blueprints(app: Flask) -> None:
    from .blueprints.admin.routes import bp as admin_bp
    from .blueprints.api.routes import bp as api_bp
    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.main.routes import bp as main_bp
    from .blueprints.modelos.routes import bp as modelos_bp
    from .blueprints.numeracao.routes import bp as numeracao_bp
    from .blueprints.oficios.routes import bp as oficios_bp
    from .blueprints.relatorios.routes import bp as relatorios_bp

    for bp in (auth_bp, main_bp, oficios_bp, modelos_bp, numeracao_bp,
               relatorios_bp, admin_bp, api_bp):
        app.register_blueprint(bp)


def _registrar_handlers(app: Flask) -> None:
    def _quer_json() -> bool:
        return request.path.startswith("/api/") or request.is_json

    @app.errorhandler(401)
    def nao_autenticado(_e):
        return jsonify(erro="Autenticação necessária."), 401

    @app.errorhandler(403)
    def proibido(_e):
        if _quer_json():
            return jsonify(erro="Acesso negado."), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def nao_encontrado(_e):
        if _quer_json():
            return jsonify(erro="Não encontrado."), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def metodo_nao_permitido(_e):
        if _quer_json():
            return jsonify(erro="Método não permitido."), 405
        return render_template("errors/404.html"), 405

    @app.errorhandler(429)
    def muitas_tentativas(_e):
        if _quer_json():
            return jsonify(erro="Muitas tentativas. Aguarde um minuto."), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(CSRFError)
    def csrf_invalido(_e):
        if _quer_json():
            return jsonify(erro="Token CSRF inválido ou ausente."), 400
        return render_template("errors/400.html"), 400

    @app.errorhandler(500)
    def erro_interno(_e):
        db.session.rollback()
        if _quer_json():
            return jsonify(erro="Erro interno."), 500
        return render_template("errors/500.html"), 500


def _registrar_cabecalhos_seguranca(app: Flask) -> None:
    @app.after_request
    def cabecalhos(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        resp.headers.setdefault("Content-Security-Policy", CSP)
        if current_user.is_authenticated:
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp


def _registrar_contexto_templates(app: Flask) -> None:
    from .services.formatacao import data_br, data_hora_br, data_por_extenso

    app.jinja_env.filters["data_extenso"] = data_por_extenso
    app.jinja_env.filters["data_br"] = data_br
    app.jinja_env.filters["data_hora_br"] = data_hora_br

    @app.context_processor
    def contexto_global():
        return {"GABINETE_NOME": app.config["GABINETE_NOME"]}


def _registrar_comandos(app: Flask) -> None:
    import click

    @app.cli.command("criar-admin")
    @click.option("--nome", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option("--senha")
    def criar_admin(nome, email, senha):
        """Cria um usuário administrador."""
        from .services.usuarios import criar_usuario

        usuario = criar_usuario(nome=nome, email=email, senha=senha, perfil="admin")
        click.echo(f"Administrador criado: {usuario.email}")

    @app.cli.command("seed")
    @click.option("--oficios", default=180, help="Quantidade de ofícios fictícios.")
    def seed(oficios):
        """Popula o banco com dados FICTÍCIOS para demonstração."""
        from .services.seed import popular

        resumo = popular(qtd_oficios=oficios)
        click.echo(resumo)
