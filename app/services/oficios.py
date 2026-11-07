"""Criação, edição e consulta de ofícios."""

from dataclasses import dataclass
from datetime import datetime

from flask import current_app
from sqlalchemy import or_

from ..extensions import db
from ..models import Departamento, Oficio, Secretario
from . import numeracao
from .placeholders import DadosPlaceholder, processar_placeholders

TRATAMENTOS = ["", "Sr.", "Srª"]


class OficioInvalido(ValueError):
    pass


@dataclass
class Rascunho:
    """Ofício montado a partir do formulário, ainda não salvo (usado no preview)."""

    oficio: Oficio
    departamento: Departamento
    numero_previsto: str


def _texto(form, campo: str, limite: int | None = None) -> str:
    valor = (form.get(campo) or "").strip()
    return valor[:limite] if limite else valor


def montar_oficio(form, oficio: Oficio | None = None) -> Oficio:
    """Preenche um Oficio (novo ou existente) com os dados do formulário, já com placeholders."""
    cfg = current_app.config
    oficio = oficio or Oficio()

    try:
        departamento_id = int(form.get("departamento_id") or 0)
    except ValueError:
        departamento_id = 0
    departamento = db.session.get(Departamento, departamento_id) if departamento_id else None
    if not departamento:
        raise OficioInvalido("Selecione a secretaria de destino.")

    assunto = _texto(form, "assunto")
    if not assunto:
        raise OficioInvalido("Informe o assunto do ofício.")

    secretario = None
    if form.get("secretario_id"):
        try:
            secretario = db.session.get(Secretario, int(form.get("secretario_id")))
        except ValueError:
            secretario = None
        if secretario and secretario.departamento_id != departamento.id:
            secretario = None

    tratamento = _texto(form, "municipe_tratamento")
    if tratamento not in TRATAMENTOS:
        tratamento = ""

    dados = DadosPlaceholder.de_dict({**form, "municipe_tratamento": tratamento,
                                      "numero_endereco": form.get("numero_endereco")
                                      or form.get("numero") or ""})

    oficio.departamento_id = departamento.id
    oficio.departamento = departamento
    oficio.secretario_id = secretario.id if secretario else None
    oficio.secretario = secretario
    oficio.destinatario = (secretario.nome if secretario else _texto(form, "destinatario", 100))
    oficio.cargo_destinatario = (secretario.cargo if secretario
                                 else _texto(form, "cargo_destinatario", 100))
    if not oficio.destinatario:
        raise OficioInvalido("Selecione o secretário (destinatário).")

    oficio.assunto = processar_placeholders(assunto, dados)[:300]
    oficio.corpo_oficio = processar_placeholders(form.get("corpo_oficio") or "", dados)
    oficio.endereco = dados.endereco[:200]
    oficio.numero_endereco = dados.numero_endereco[:20]
    oficio.bairro = dados.bairro[:100]
    oficio.em_frente = dados.em_frente[:200]
    oficio.assessor_nome = _texto(form, "assessor_nome", 100)
    oficio.municipe_nome = dados.municipe_nome[:120]
    oficio.municipe_telefone = dados.municipe_telefone[:30]
    oficio.municipe_tratamento = tratamento
    oficio.nome_responsavel = _texto(form, "nome_responsavel", 100) or cfg["RESPONSAVEL_NOME"]
    oficio.cargo_responsavel = _texto(form, "cargo_responsavel", 100) or cfg["RESPONSAVEL_CARGO"]
    return oficio


def preparar_rascunho(form) -> Rascunho:
    oficio = montar_oficio(form)
    ano = numeracao.ano_atual()
    previsto = numeracao.formatar_numero(numeracao.calcular_proximo_sequencial(ano), ano)
    oficio.numero = previsto
    oficio.data_criacao = datetime.now()
    return Rascunho(oficio=oficio, departamento=oficio.departamento, numero_previsto=previsto)


def criar(form, usuario) -> Oficio:
    oficio = montar_oficio(form)
    oficio.data_criacao = datetime.now()
    oficio.criado_por_id = getattr(usuario, "id", None)
    oficio.executado = False
    return numeracao.atribuir_numero(oficio)


def registrar_manual(form, usuario) -> Oficio:
    oficio = montar_oficio(form)
    numeracao.aplicar_numero_manual(oficio, form.get("numero"))
    oficio.data_criacao = datetime.now()
    oficio.criado_por_id = getattr(usuario, "id", None)
    db.session.add(oficio)
    db.session.commit()
    return oficio


def atualizar(oficio: Oficio, form) -> Oficio:
    """Edição: os textos já estão processados, então placeholders só afetam o que for novo."""
    montar_oficio(form, oficio)
    db.session.commit()
    return oficio


@dataclass
class Filtros:
    busca: str = ""
    departamento_id: int | None = None
    assessor: str = ""
    status: str = ""
    mes: str = ""

    @classmethod
    def de_args(cls, args) -> "Filtros":
        try:
            dep = int(args.get("departamento_id")) if args.get("departamento_id") else None
        except ValueError:
            dep = None
        status = args.get("status", "")
        return cls(
            busca=(args.get("q") or "").strip()[:100],
            departamento_id=dep,
            assessor=(args.get("assessor") or "").strip()[:100],
            status=status if status in ("pendente", "executado") else "",
            mes=(args.get("mes") or "").strip(),
        )

    @property
    def ativos(self) -> bool:
        return any([self.busca, self.departamento_id, self.assessor, self.status, self.mes])


def periodo_do_mes(mes: str) -> tuple[datetime, datetime] | None:
    """'2026-03' -> (01/03/2026, 01/04/2026)."""
    try:
        ano, m = (int(p) for p in mes.split("-"))
        inicio = datetime(ano, m, 1)
    except (ValueError, AttributeError):
        return None
    fim = datetime(ano + 1, 1, 1) if m == 12 else datetime(ano, m + 1, 1)
    return inicio, fim


def consultar(filtros: Filtros):
    q = Oficio.query
    if filtros.busca:
        termo = f"%{filtros.busca}%"
        q = q.filter(or_(
            Oficio.numero.ilike(termo),
            Oficio.assunto.ilike(termo),
            Oficio.municipe_nome.ilike(termo),
            Oficio.destinatario.ilike(termo),
            Oficio.bairro.ilike(termo),
            Oficio.endereco.ilike(termo),
        ))
    if filtros.departamento_id:
        q = q.filter(Oficio.departamento_id == filtros.departamento_id)
    if filtros.assessor:
        q = q.filter(Oficio.assessor_nome.ilike(f"%{filtros.assessor}%"))
    if filtros.status == "executado":
        q = q.filter(Oficio.executado.is_(True))
    elif filtros.status == "pendente":
        q = q.filter(Oficio.executado.is_(False))
    periodo = periodo_do_mes(filtros.mes) if filtros.mes else None
    if periodo:
        q = q.filter(Oficio.data_criacao >= periodo[0], Oficio.data_criacao < periodo[1])
    return q.order_by(
        Oficio.ano.desc(), Oficio.sequencial.desc(), Oficio.data_criacao.desc()
    )


def assessores_conhecidos() -> list[str]:
    nomes = db.session.query(Oficio.assessor_nome).filter(
        Oficio.assessor_nome.isnot(None), Oficio.assessor_nome != ""
    ).distinct().all()
    from ..models import AssessorPadrao

    padrao = [a.nome for a in AssessorPadrao.query.order_by(AssessorPadrao.nome).all()]
    return sorted({*padrao, *(n for (n,) in nomes)}, key=str.lower)
