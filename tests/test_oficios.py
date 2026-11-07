from io import BytesIO

from docx import Document
from openpyxl import load_workbook

from app.models import LogAuditoria, Oficio
from app.services import numeracao
from tests.conftest import form_oficio


def _criar(client, dados_base, **extra):
    resp = client.post("/oficios/confirmar", data=form_oficio(dados_base, **extra))
    assert resp.status_code == 302
    return Oficio.query.order_by(Oficio.id.desc()).first()


def test_preview_nao_salva_e_mostra_numero_previsto(client, login, dados_base, db):
    login("assessor")
    resp = client.post("/oficios/novo", data=form_oficio(dados_base))
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Revisar e confirmar" in html
    assert "Rua das Flores, nº 120 - Centro" in html
    assert f"001/{numeracao.ano_atual()}" in html
    assert Oficio.query.count() == 0


def test_criar_oficio_processa_placeholders_e_audita(client, login, dados_base, usuarios, db):
    login("assessor")
    o = _criar(client, dados_base)
    ano = numeracao.ano_atual()
    assert o.numero == f"001/{ano}" and (o.ano, o.sequencial) == (ano, 1)
    assert o.assunto == "Solicita tapa buraco na Rua das Flores, nº 120 - Centro."
    assert o.corpo_oficio.startswith("Pedido do(a) Srª Ana Teste.")
    assert o.destinatario == "Maria Exemplo"
    assert o.criado_por_id == usuarios["assessor"].id
    assert o.nome_responsavel == "FULANO DE TAL"
    log = LogAuditoria.query.filter_by(acao="CRIAR", entidade="oficio").one()
    assert log.entidade_id == o.id


def test_criar_sem_secretaria_ou_assunto_falha(client, login, dados_base, db):
    login("admin")
    resp = client.post("/oficios/confirmar", data=form_oficio(dados_base, departamento_id=""))
    assert "Selecione a secretaria" in resp.get_data(as_text=True)
    resp = client.post("/oficios/confirmar", data=form_oficio(dados_base, assunto=" "))
    assert "Informe o assunto" in resp.get_data(as_text=True)
    assert Oficio.query.count() == 0


def test_secretario_de_outra_secretaria_e_rejeitado(client, login, dados_base, db):
    login("admin")
    resp = client.post("/oficios/confirmar", data=form_oficio(
        dados_base, secretario_id=str(dados_base["secretario_st"].id)))
    assert "Selecione o secretário" in resp.get_data(as_text=True)


def test_voltar_da_revisao_mantem_dados(client, login, dados_base):
    login("admin")
    resp = client.post("/oficios/confirmar", data=form_oficio(dados_base, acao="voltar"))
    assert 'value="Rua das Flores"' in resp.get_data(as_text=True)
    assert Oficio.query.count() == 0


def test_registro_manual(client, login, dados_base, db):
    login("admin")
    resp = client.post("/oficios/registro-manual", data=form_oficio(dados_base, numero="77/2026"))
    assert resp.status_code == 302
    assert Oficio.query.one().numero == "077/2026"
    resp = client.post("/oficios/registro-manual", data=form_oficio(dados_base, numero="077/2026"))
    assert "já está em uso" in resp.get_data(as_text=True)


def test_editar_oficio(client, login, dados_base, db):
    login("assessor")
    o = _criar(client, dados_base)
    dados = form_oficio(dados_base, assunto="Novo assunto", bairro="Vila Nova")
    resp = client.post(f"/oficios/{o.id}/editar", data=dados)
    assert resp.status_code == 302
    db.session.refresh(o)
    assert o.assunto == "Novo assunto" and o.bairro == "Vila Nova"


def test_marcar_executado_json(client, login, dados_base, db):
    login("assessor")
    o = _criar(client, dados_base)
    resp = client.post(f"/oficios/{o.id}/executado", json={"executado": True})
    assert resp.get_json() == {"sucesso": True, "oficio_id": o.id, "executado": True}
    db.session.refresh(o)
    assert o.executado is True


def test_excluir_e_renumerar_admin(client, login, dados_base, db):
    login("admin")
    a = _criar(client, dados_base)
    b = _criar(client, dados_base)
    ano = numeracao.ano_atual()
    resp = client.post(f"/oficios/{b.id}/renumerar", data={"novo_numero": f"001/{ano}"})
    assert "já está em uso" in resp.get_data(as_text=True)
    client.post(f"/oficios/{b.id}/renumerar", data={"novo_numero": f"10/{ano}"})
    db.session.refresh(b)
    assert b.numero == f"010/{ano}"
    client.post(f"/oficios/{a.id}/excluir")
    assert db.session.get(Oficio, a.id) is None
    acoes = {log.acao for log in LogAuditoria.query.all()}
    assert {"RENUMERAR", "EXCLUIR"} <= acoes


def test_download_word(client, login, dados_base, db):
    login("admin")
    o = _criar(client, dados_base)
    resp = client.get(f"/oficios/{o.id}/download")
    assert resp.status_code == 200
    assert "oficio_001_" in resp.headers["Content-Disposition"]
    doc = Document(BytesIO(resp.data))
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert f"OFÍCIO Nº {o.numero}." in texto
    assert "Cidade Teste," in texto
    assert "ASSUNTO: Solicita tapa buraco na Rua das Flores, nº 120 - Centro." in texto
    assert "Segunda linha." in texto
    assert "FULANO DE TAL" in texto
    assert all(r.font.name in (None, "Arial") for p in doc.paragraphs for r in p.runs)


def test_lista_com_filtros_e_paginacao(client, login, dados_base, db):
    login("admin")
    for i in range(3):
        _criar(client, dados_base, bairro=f"Bairro {i}")
    html = client.get("/oficios/?q=Bairro 1").get_data(as_text=True)
    assert "3 ofícios" not in html and "1 ofício" in html
    assert "1 ofício" in client.get("/oficios/?status=pendente&q=Bairro 2").get_data(as_text=True)
    assert "0 ofícios" in client.get("/oficios/?status=executado").get_data(as_text=True)


def test_exportar_excel(client, login, dados_base, db):
    login("leitura")
    resp = client.get("/relatorios/exportar")
    assert resp.status_code == 200
    login_admin = client.post("/logout")
    assert login_admin.status_code == 302
    client.post("/login", data={"email": "admin@teste.com", "senha": "SenhaForte123"})
    _criar(client, dados_base)
    resp = client.get("/relatorios/exportar")
    ws = load_workbook(BytesIO(resp.data)).active
    assert ws["A1"].value == "Número"
    assert ws["A2"].value.startswith("001/")
    assert LogAuditoria.query.filter_by(acao="EXPORTAR").count() == 2


def test_api_secretarios_e_modelos(client, login, dados_base):
    login("assessor")
    dep = dados_base["ssu"].id
    sec = client.get(f"/oficios/api/secretarios/{dep}").get_json()
    assert sec["secretarios"][0]["nome"] == "Maria Exemplo"
    mod = client.get(f"/oficios/api/modelos/{dep}").get_json()
    assert mod["modelos"][0]["titulo"] == "Tapa buraco"


def test_paginas_renderizam(client, login, dados_base, db):
    login("admin")
    o = _criar(client, dados_base)
    for url in ["/", "/oficios/", f"/oficios/{o.id}", f"/oficios/{o.id}/editar",
                "/oficios/registro-manual", "/modelos/", "/modelos/novo", "/numeracao/",
                "/relatorios/", "/relatorios/fechamento", "/admin/usuarios", "/admin/auditoria"]:
        assert client.get(url).status_code == 200, url
    assert client.get("/oficios/99999").status_code == 404
