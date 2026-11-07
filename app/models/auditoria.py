from datetime import datetime

from ..extensions import db

ACOES = {
    "LOGIN": "Login",
    "LOGIN_FALHOU": "Falha de login",
    "LOGOUT": "Logout",
    "CRIAR": "Criação",
    "EDITAR": "Edição",
    "EXCLUIR": "Exclusão",
    "RENUMERAR": "Renumeração",
    "RESERVAR": "Reserva de número",
    "LIBERAR": "Liberação de número",
    "EXPORTAR": "Exportação",
    "CONFIG": "Configuração",
}


class LogAuditoria(db.Model):
    """Trilha de auditoria: quem fez o quê, quando e de onde."""

    __tablename__ = "log_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), index=True)
    usuario_email = db.Column(db.String(160))
    acao = db.Column(db.String(30), nullable=False, index=True)
    entidade = db.Column(db.String(40))
    entidade_id = db.Column(db.Integer)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    detalhes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    usuario = db.relationship("Usuario")

    @property
    def acao_nome(self) -> str:
        return ACOES.get(self.acao, self.acao)

    def __repr__(self) -> str:
        return f"<LogAuditoria {self.acao} {self.entidade}:{self.entidade_id}>"
