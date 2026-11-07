from datetime import datetime

from ..extensions import db


class TemplateOficio(db.Model):
    """Modelo de texto com placeholders, ex.: [ENDEREÇO], [BAIRRO]."""

    __tablename__ = "template_oficio"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    assunto = db.Column(db.String(300), nullable=False)
    corpo_texto = db.Column(db.Text, nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey("departamento.id"), nullable=False)

    departamento = db.relationship("Departamento")

    def __repr__(self) -> str:
        return f"<TemplateOficio {self.titulo}>"


class Oficio(db.Model):
    __tablename__ = "oficio"
    __table_args__ = (
        db.UniqueConstraint("ano", "sequencial", name="uq_oficio_ano_sequencial"),
        db.Index("ix_oficio_assessor_nome", "assessor_nome"),
    )

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False, unique=True)
    ano = db.Column(db.Integer, index=True)
    sequencial = db.Column(db.Integer)

    assunto = db.Column(db.String(300), nullable=False)
    destinatario = db.Column(db.String(100), nullable=False, default="")
    cargo_destinatario = db.Column(db.String(100))
    orgao_destinatario = db.Column(db.String(100))

    endereco = db.Column(db.String(200))
    numero_endereco = db.Column(db.String(20))
    bairro = db.Column(db.String(100))
    em_frente = db.Column(db.String(200))

    # Controle interno / atendimento
    assessor_nome = db.Column(db.String(100))
    municipe_nome = db.Column(db.String(120))
    municipe_telefone = db.Column(db.String(30))
    municipe_tratamento = db.Column(db.String(20))
    executado = db.Column(db.Boolean, nullable=False, default=False)

    corpo_oficio = db.Column(db.Text)
    nome_responsavel = db.Column(db.String(100))
    cargo_responsavel = db.Column(db.String(100))

    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    departamento_id = db.Column(
        db.Integer, db.ForeignKey("departamento.id"), nullable=False, index=True
    )
    secretario_id = db.Column(db.Integer, db.ForeignKey("secretario.id"))
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))

    departamento = db.relationship("Departamento")
    secretario = db.relationship("Secretario")
    criado_por = db.relationship("Usuario")

    @property
    def status(self) -> str:
        return "Executado" if self.executado else "Pendente"

    def __repr__(self) -> str:
        return f"<Oficio {self.numero}>"
