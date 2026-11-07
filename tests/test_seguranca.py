"""Testes dos controles de segurança: autenticação, autorização, CSRF, força bruta e cabeçalhos."""

from app import create_app
from app.extensions import db as _db
from app.models import LogAuditoria, Oficio
from tests.conftest import SENHA, form_oficio

ROTAS_PROTEGIDAS = ["/", "/oficios/", "/oficios/novo", "/modelos/", "/numeracao/",
                    "/relatorios/", "/relatorios/fechamento", "/relatorios/exportar",
                    "/admin/usuarios", "/admin/auditoria"]


def test_rotas_exigem_login(client):
    for rota in ROTAS_PROTEGIDAS:
        resp = client.get(rota)
        assert resp.status_code == 302, rota
        assert "/login" in resp.headers["Location"], rota


def test_api_sem_login_retorna_401_json(client):
    resp = client.get("/api/graficos")
    assert resp.status_code == 401
    assert resp.is_json


def test_health_e_publico(client):
    assert client.get("/health").status_code == 200


def test_login_valido_e_auditado(client, usuarios, db):
    resp = client.post("/login", data={"email": "ADMIN@teste.com ", "senha": SENHA})
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/")
    log = LogAuditoria.query.filter_by(acao="LOGIN").one()
    assert log.usuario_id == usuarios["admin"].id and log.ip


def test_login_invalido_mensagem_generica_e_auditado(client, usuarios, db):
    resp = client.post("/login", data={"email": "admin@teste.com", "senha": "errada123456"})
    assert "E-mail ou senha inválidos" in resp.get_data(as_text=True)
    resp2 = client.post("/login", data={"email": "naoexiste@teste.com", "senha": "x" * 12})
    assert "E-mail ou senha inválidos" in resp2.get_data(as_text=True)
    falhas = LogAuditoria.query.filter_by(acao="LOGIN_FALHOU").all()
    assert {f.usuario_email for f in falhas} == {"admin@teste.com", "naoexiste@teste.com"}


def test_usuario_inativo_nao_entra(client, usuarios, db):
    usuarios["assessor"].ativo = False
    db.session.commit()
    resp = client.post("/login", data={"email": "assessor@teste.com", "senha": SENHA})
    assert resp.status_code == 200
    assert client.get("/").status_code == 302


def test_rate_limit_no_login(client, usuarios):
    for _ in range(5):
        client.post("/login", data={"email": "admin@teste.com", "senha": "errada"})
    resp = client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
    assert resp.status_code == 429


def test_open_redirect_bloqueado(client, usuarios):
    resp = client.post("/login?next=https://site-malicioso.com",
                       data={"email": "admin@teste.com", "senha": SENHA})
    assert resp.headers["Location"] == "/"
    client.post("/logout")
    resp = client.post("/login?next=//site-malicioso.com",
                       data={"email": "admin@teste.com", "senha": SENHA})
    assert resp.headers["Location"] == "/"


def test_redirect_interno_permitido(client, usuarios):
    resp = client.post("/login?next=/oficios/", data={"email": "admin@teste.com", "senha": SENHA})
    assert resp.headers["Location"] == "/oficios/"


def test_perfil_leitura_nao_cria_nem_exclui(client, login, dados_base, db):
    login("leitura")
    assert client.get("/").status_code == 200
    assert client.get("/oficios/novo").status_code == 403
    assert client.post("/oficios/confirmar", data=form_oficio(dados_base)).status_code == 403
    assert client.get("/admin/usuarios").status_code == 403


def test_assessor_nao_exclui_nem_administra(client, login, dados_base, db):
    login("assessor")
    client.post("/oficios/confirmar", data=form_oficio(dados_base))
    oficio = Oficio.query.one()
    assert client.post(f"/oficios/{oficio.id}/excluir").status_code == 403
    assert client.get(f"/oficios/{oficio.id}/renumerar").status_code == 403
    resp = client.post("/numeracao/reservar", data={"ano": 2026, "sequencial": 9})
    assert resp.status_code == 403
    assert client.get("/admin/auditoria").status_code == 403


def test_exclusao_por_get_nao_permitida(client, login, dados_base, db):
    login("admin")
    client.post("/oficios/confirmar", data=form_oficio(dados_base))
    oficio = Oficio.query.one()
    assert client.get(f"/oficios/{oficio.id}/excluir").status_code == 405
    assert db.session.get(Oficio, oficio.id) is not None


def test_logout_somente_post(client, login):
    login("admin")
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
    assert client.get("/").status_code == 302


def test_csrf_obrigatorio_quando_ativo(usuarios):
    """Com CSRF ligado (como em produção), POST sem token é recusado."""
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        _db.create_all()
        cliente = app.test_client()
        resp = cliente.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
        assert resp.status_code == 400
        resp_json = cliente.post("/oficios/1/executado", json={"executado": True})
        assert resp_json.status_code in (400, 401)


def test_cabecalhos_de_seguranca(client):
    resp = client.get("/login")
    h = resp.headers
    assert h["X-Frame-Options"] == "DENY"
    assert h["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert "script-src 'self';" in h["Content-Security-Policy"]
    assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_cookie_de_sessao_httponly(client, usuarios):
    resp = client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
    cookie = resp.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_senha_armazenada_com_hash(usuarios):
    u = usuarios["admin"]
    assert SENHA not in u.senha_hash
    assert u.senha_hash.startswith(("scrypt:", "pbkdf2:"))
    assert u.checar_senha(SENHA) and not u.checar_senha("outra")


def test_admin_nao_desativa_a_si_mesmo(client, login, usuarios, db):
    login("admin")
    client.post(f"/admin/usuarios/{usuarios['admin'].id}/alterar", data={"acao": "desativar"})
    assert usuarios["admin"].ativo is True


def test_criacao_de_usuario_valida_senha(client, login, db):
    login("admin")
    client.post("/admin/usuarios", data={"nome": "Fraco", "email": "fraco@teste.com",
                                         "senha": "123", "perfil": "assessor"})
    from app.models import Usuario
    assert Usuario.query.filter_by(email="fraco@teste.com").first() is None
    client.post("/admin/usuarios", data={"nome": "Forte", "email": "forte@teste.com",
                                         "senha": "SenhaBoa2026x", "perfil": "leitura"})
    novo = Usuario.query.filter_by(email="forte@teste.com").one()
    assert novo.perfil == "leitura"
    assert LogAuditoria.query.filter_by(acao="CRIAR", entidade="usuario").count() == 1
