from ..extensions import db


class Departamento(db.Model):
    """Secretaria municipal que recebe os ofícios."""

    __tablename__ = "departamento"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    sigla = db.Column(db.String(10), nullable=False, unique=True)

    secretarios = db.relationship("Secretario", back_populates="departamento", lazy="select")

    def __repr__(self) -> str:
        return f"<Departamento {self.sigla}>"


class Secretario(db.Model):
    __tablename__ = "secretario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey("departamento.id"), nullable=False)

    departamento = db.relationship("Departamento", back_populates="secretarios")

    def __repr__(self) -> str:
        return f"<Secretario {self.nome}>"


class AssessorPadrao(db.Model):
    """Assessores do gabinete (sugestões no formulário de ofício)."""

    __tablename__ = "assessor_padrao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey("departamento.id"))

    def __repr__(self) -> str:
        return f"<AssessorPadrao {self.nome}>"
