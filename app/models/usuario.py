from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, login_manager

PERFIS = {
    "admin": "Administrador",
    "assessor": "Assessor",
    "leitura": "Somente leitura",
}


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="assessor")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_login = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def set_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_active(self) -> bool:  # usado pelo Flask-Login
        return bool(self.ativo)

    @property
    def perfil_nome(self) -> str:
        return PERFIS.get(self.perfil, self.perfil)

    @property
    def iniciais(self) -> str:
        partes = [p for p in (self.nome or "").split() if p]
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    def tem_perfil(self, *perfis: str) -> bool:
        return self.perfil in perfis

    def __repr__(self) -> str:
        return f"<Usuario {self.email}>"


@login_manager.user_loader
def carregar_usuario(user_id: str):
    return db.session.get(Usuario, int(user_id))
