"""Controle de acesso: login obrigatório e permissões por perfil."""

from functools import wraps

from flask import abort, request
from flask_login import current_user

from .extensions import login_manager

# Matriz de permissões (perfil -> ações)
PODE_EDITAR = ("admin", "assessor")
SO_ADMIN = ("admin",)


def exigir_login():
    """Use em `bp.before_request` para proteger o blueprint inteiro."""
    if not current_user.is_authenticated:
        if request.path.startswith("/api/") or request.is_json:
            abort(401)
        return login_manager.unauthorized()
    return None


def requer_perfil(*perfis: str):
    def decorador(func):
        @wraps(func)
        def envolvida(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_user.tem_perfil(*perfis):
                abort(403)
            return func(*args, **kwargs)

        return envolvida

    return decorador
