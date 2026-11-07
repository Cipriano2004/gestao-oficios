import os

import pytest

os.environ.setdefault("SECRET_KEY", "chave-apenas-para-testes")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.extensions import limiter  # noqa: E402
from app.models import Departamento, Secretario, TemplateOficio  # noqa: E402
from app.services.usuarios import criar_usuario  # noqa: E402

SENHA = "SenhaForte123"


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        limiter.reset()
        yield app
        _db.session.remove()
        _db.engine.dispose()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def dados_base(db):
    ssu = Departamento(sigla="SSU", nome="Secretaria de Serviços Urbanos")
    st = Departamento(sigla="ST", nome="Secretaria de Transportes")
    db.session.add_all([ssu, st])
    db.session.flush()
    sec = Secretario(nome="Maria Exemplo", cargo="Secretária de Serviços Urbanos",
                     departamento_id=ssu.id)
    sec_st = Secretario(nome="João Exemplo", cargo="Secretário de Transportes",
                        departamento_id=st.id)
    modelo = TemplateOficio(titulo="Tapa buraco",
                            assunto="Solicita tapa buraco na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
                            corpo_texto="Pedido do(a) [MUNICIPE_TRATAMENTO] [MUNICIPE_NOME].",
                            departamento_id=ssu.id)
    db.session.add_all([sec, sec_st, modelo])
    db.session.commit()
    return {"ssu": ssu, "st": st, "secretario": sec, "secretario_st": sec_st, "modelo": modelo}


@pytest.fixture
def usuarios(db):
    return {
        perfil: criar_usuario(nome=f"Usuário {perfil}", email=f"{perfil}@teste.com",
                              senha=SENHA, perfil=perfil)
        for perfil in ("admin", "assessor", "leitura")
    }


@pytest.fixture
def login(client, usuarios):
    def _login(perfil="admin"):
        return client.post("/login", data={"email": f"{perfil}@teste.com", "senha": SENHA})
    return _login


def form_oficio(dados_base, **extra):
    base = {
        "departamento_id": str(dados_base["ssu"].id),
        "secretario_id": str(dados_base["secretario"].id),
        "assunto": "Solicita tapa buraco na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
        "corpo_oficio": "Pedido do(a) [MUNICIPE_TRATAMENTO] [MUNICIPE_NOME].\nSegunda linha.",
        "endereco": "Rua das Flores",
        "numero_endereco": "120",
        "bairro": "Centro",
        "municipe_tratamento": "Srª",
        "municipe_nome": "Ana Teste",
        "municipe_telefone": "(11) 90000-0000",
        "assessor_nome": "Carlos",
    }
    base.update(extra)
    return base
