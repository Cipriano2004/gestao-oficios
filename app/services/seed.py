"""Dados FICTÍCIOS para demonstração (gerados com Faker). Nunca use dados reais aqui."""

import random
from datetime import datetime, timedelta

from faker import Faker
from flask import current_app

from ..extensions import db
from ..models import AssessorPadrao, Oficio, Secretario, TemplateOficio
from . import numeracao
from .placeholders import DadosPlaceholder, processar_placeholders
from .templates_padrao import garantir_secretarias, recriar_modelos

ASSESSORES = ["Ana Ribeiro", "Bruno Carvalho", "Carla Mendes", "Diego Fernandes"]
BAIRROS = ["Centro", "Jardim das Flores", "Vila Nova", "Parque Industrial", "Jardim América",
           "Vila Esperança", "Recanto Verde", "Jardim Primavera", "Vila São João"]


def _data_aleatoria(fake: Faker, dias: int) -> datetime:
    """Datas nos últimos `dias`, com mais peso nos meses recentes e só em horário comercial."""
    atras = int(abs(random.triangular(0, dias, 0)))
    dia = datetime.now() - timedelta(days=atras)
    while dia.weekday() >= 5:
        dia -= timedelta(days=1)
    return dia.replace(hour=random.randint(8, 17), minute=random.randint(0, 59), second=0,
                       microsecond=0)


def popular(qtd_oficios: int = 180, semente: int = 42) -> str:
    random.seed(semente)
    fake = Faker("pt_BR")
    Faker.seed(semente)

    deps = garantir_secretarias()
    if not Secretario.query.first():
        for dep in deps.values():
            db.session.add(Secretario(nome=fake.name(), cargo=f"Secretário(a) - {dep.sigla}",
                                      departamento_id=dep.id))
    if not AssessorPadrao.query.first():
        for nome in ASSESSORES:
            db.session.add(AssessorPadrao(nome=nome))
    db.session.commit()

    if not TemplateOficio.query.first():
        recriar_modelos()

    if Oficio.query.count() >= qtd_oficios:
        return "Banco já possui dados de demonstração."

    modelos = TemplateOficio.query.all()
    pesos = {"SSU": 5, "ST": 3, "SMMA": 3, "SS": 2, "SADS": 2, "SOP": 1}
    pesos_modelos = [pesos.get(m.departamento.sigla, 1) for m in modelos]

    registros = []
    for _ in range(qtd_oficios):
        modelo = random.choices(modelos, weights=pesos_modelos)[0]
        secretario = Secretario.query.filter_by(departamento_id=modelo.departamento_id).first()
        dados = DadosPlaceholder(
            endereco=f"Rua {fake.last_name()} {fake.last_name()}",
            numero_endereco=str(random.randint(10, 1999)),
            bairro=random.choice(BAIRROS),
            municipe_tratamento=random.choice(["Sr.", "Srª"]),
            municipe_nome=fake.name(),
            municipe_telefone=f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            data_evento=fake.date_between("+5d", "+60d").strftime("%d/%m/%Y"),
            em_frente="das 9h às 17h",
        )
        data = _data_aleatoria(fake, 330)
        registros.append((data, Oficio(
            assunto=processar_placeholders(modelo.assunto, dados)[:300],
            corpo_oficio=processar_placeholders(modelo.corpo_texto, dados),
            destinatario=secretario.nome,
            cargo_destinatario=secretario.cargo,
            departamento_id=modelo.departamento_id,
            secretario_id=secretario.id,
            endereco=dados.endereco,
            numero_endereco=dados.numero_endereco,
            bairro=dados.bairro,
            assessor_nome=random.choices(ASSESSORES + [""], weights=[5, 4, 3, 2, 1])[0],
            municipe_nome=dados.municipe_nome,
            municipe_telefone=dados.municipe_telefone,
            municipe_tratamento=dados.municipe_tratamento,
            data_criacao=data,
            atualizado_em=data,
            nome_responsavel=current_app.config['RESPONSAVEL_NOME'],
            cargo_responsavel=current_app.config['RESPONSAVEL_CARGO'],
            executado=random.random() < (0.85 if (datetime.now() - data).days > 45 else 0.35),
        )))

    contador: dict[int, int] = {}
    for data, oficio in sorted(registros, key=lambda r: r[0]):
        ano = data.year
        contador[ano] = contador.get(ano, 0) + 1
        oficio.ano, oficio.sequencial = ano, contador[ano]
        oficio.numero = numeracao.formatar_numero(contador[ano], ano)
        db.session.add(oficio)
    db.session.commit()

    return (f"Seed concluído: {len(deps)} secretarias, {len(modelos)} modelos, "
            f"{len(registros)} ofícios fictícios.")
