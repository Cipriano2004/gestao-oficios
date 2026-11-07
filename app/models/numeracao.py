from datetime import datetime

from ..extensions import db


class NumeroReserva(db.Model):
    """Número marcado como usado fora do sistema, para a numeração pular."""

    __tablename__ = "numero_reserva"
    __table_args__ = (
        db.UniqueConstraint("ano", "sequencial", name="uq_numero_reserva_ano_seq"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ano = db.Column(db.Integer, nullable=False, index=True)
    sequencial = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(200))
    criado_em = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self) -> str:
        return f"<NumeroReserva {self.sequencial:03d}/{self.ano}>"


class NumeracaoConfig(db.Model):
    """Configuração por ano. `offset` guarda o próximo número desejado (valor absoluto).

    A linha do ano também funciona como trava (SELECT ... FOR UPDATE) na geração de números.
    """

    __tablename__ = "numeracao_config"

    id = db.Column(db.Integer, primary_key=True)
    ano = db.Column(db.Integer, nullable=False, unique=True, index=True)
    offset = db.Column(db.Integer, nullable=False, default=0)
    atualizado_em = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<NumeracaoConfig ano={self.ano} proximo={self.offset}>"
