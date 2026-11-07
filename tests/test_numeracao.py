from datetime import datetime

import pytest

from app.models import Oficio
from app.services import numeracao


def _oficio(dados_base, **kw):
    base = dict(assunto="Teste", destinatario="X", departamento_id=dados_base["ssu"].id,
                data_criacao=datetime.now())
    base.update(kw)
    return Oficio(**base)


def test_parse_e_formatar():
    assert numeracao.parse_numero("223/2026") == (223, 2026)
    assert numeracao.parse_numero(" 7 / 2025 ") == (7, 2025)
    assert numeracao.parse_numero("abc") is None
    assert numeracao.formatar_numero(7, 2026) == "007/2026"


def test_primeiro_numero_do_ano_usa_numeracao_inicial(app, dados_base):
    assert numeracao.calcular_proximo_sequencial(2026) == 1
    app.config["NUMERACAO_INICIAL"] = 222
    assert numeracao.calcular_proximo_sequencial(2026) == 222


def test_atribuir_numero_sequencial(db, dados_base):
    a = numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    b = numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    assert (a.numero, b.numero) == ("001/2026", "002/2026")
    assert (b.ano, b.sequencial) == (2026, 2)


def test_pula_numeros_reservados(db, dados_base):
    numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    numeracao.reservar(2026, 2, "feito à mão")
    numeracao.reservar(2026, 3)
    c = numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    assert c.numero == "004/2026"


def test_proximo_desejado_avanca_numeracao(db, dados_base):
    numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    numeracao.definir_proximo_desejado(2026, 50)
    assert numeracao.atribuir_numero(_oficio(dados_base), ano=2026).numero == "050/2026"
    # valor desejado menor que o atual é ignorado
    numeracao.definir_proximo_desejado(2026, 10)
    assert numeracao.atribuir_numero(_oficio(dados_base), ano=2026).numero == "051/2026"


def test_proximo_desejado_invalido(db, dados_base):
    with pytest.raises(numeracao.NumeroInvalido):
        numeracao.definir_proximo_desejado(2026, 0)


def test_virada_de_ano_reinicia(db, dados_base):
    numeracao.atribuir_numero(_oficio(dados_base), ano=2025)
    numeracao.atribuir_numero(_oficio(dados_base), ano=2025)
    assert numeracao.atribuir_numero(_oficio(dados_base), ano=2026).numero == "001/2026"


def test_reserva_de_numero_em_uso_e_duplicada(db, dados_base):
    numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    with pytest.raises(numeracao.NumeroInvalido):
        numeracao.reservar(2026, 1)
    numeracao.reservar(2026, 5)
    with pytest.raises(numeracao.NumeroInvalido):
        numeracao.reservar(2026, 5)
    assert numeracao.liberar(2026, 5) is True
    assert numeracao.liberar(2026, 5) is False


def test_numero_manual_valida_duplicidade(db, dados_base):
    a = numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    novo = _oficio(dados_base)
    with pytest.raises(numeracao.NumeroInvalido):
        numeracao.aplicar_numero_manual(novo, "1/2026")  # normaliza para 001/2026
    numeracao.aplicar_numero_manual(novo, "45/2026")
    assert (novo.numero, novo.ano, novo.sequencial) == ("045/2026", 2026, 45)
    # renumerar o próprio ofício para o mesmo número é permitido
    numeracao.aplicar_numero_manual(a, "001/2026", ignorar_id=a.id)


def test_numero_manual_fora_do_padrao(db, dados_base):
    o = _oficio(dados_base)
    numeracao.aplicar_numero_manual(o, "GAB-12/2026-A")
    assert o.numero == "GAB-12/2026-A" and o.ano is None and o.sequencial is None


def test_numero_manual_vazio(db, dados_base):
    with pytest.raises(numeracao.NumeroInvalido):
        numeracao.aplicar_numero_manual(_oficio(dados_base), "  ")


def test_mapa_do_ano(db, dados_base):
    numeracao.atribuir_numero(_oficio(dados_base), ano=2026)
    numeracao.reservar(2026, 2, "manual")
    mapa = numeracao.mapa_do_ano(2026)
    status = {n["sequencial"]: n["status"] for n in mapa["numeros"]}
    assert status[1] == "OFICIO" and status[2] == "RESERVADO" and status[3] == "LIVRE"
    assert mapa["proximo"] == "003/2026"
    assert mapa["reservas"] == [{"sequencial": 2, "motivo": "manual"}]
