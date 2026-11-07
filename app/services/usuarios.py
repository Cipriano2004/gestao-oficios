"""Criação e validação de usuários."""

import re

from ..extensions import db
from ..models import PERFIS, Usuario

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAMANHO_MINIMO_SENHA = 10


class UsuarioInvalido(ValueError):
    pass


def validar_senha(senha: str) -> None:
    if len(senha or "") < TAMANHO_MINIMO_SENHA:
        raise UsuarioInvalido(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
    if not (re.search(r"[A-Za-z]", senha) and re.search(r"\d", senha)):
        raise UsuarioInvalido("A senha precisa ter letras e números.")


def criar_usuario(nome: str, email: str, senha: str, perfil: str = "assessor") -> Usuario:
    nome, email = (nome or "").strip(), (email or "").strip().lower()
    if not nome:
        raise UsuarioInvalido("Informe o nome.")
    if not _RE_EMAIL.match(email):
        raise UsuarioInvalido("Informe um e-mail válido.")
    if perfil not in PERFIS:
        raise UsuarioInvalido("Perfil inválido.")
    if Usuario.query.filter_by(email=email).first():
        raise UsuarioInvalido("Já existe um usuário com este e-mail.")
    validar_senha(senha)

    usuario = Usuario(nome=nome, email=email, perfil=perfil, ativo=True)
    usuario.set_senha(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario
