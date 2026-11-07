from datetime import datetime

from app.models import Oficio
from app.services import relatorios
from app.services.seed import popular
from app.services.templates_padrao import recriar_modelos

_contador = iter(range(1, 10_000))


def _oficio(dep_id, data, assessor="", executado=False, municipe=""):
    return Oficio(numero=f"T-{next(_contador)}", assunto="A", destinatario="X",
                  departamento_id=dep_id, data_criacao=data, assessor_nome=assessor,
                  executado=executado, municipe_nome=municipe)


def test_canonizar_e_agrupar_assessores():
    assert relatorios.canonizar_assessor("  João   Silva ") == "Joao Silva"
    assert relatorios.canonizar_assessor("") == "Sem assessor"
    grupos = relatorios.agrupar_assessores({"Joao Silva": 3, "Joao Silv": 2, "Ana": 1,
                                            "Sem assessor": 4})
    assert grupos[0] == {"nome": "Joao Silva", "count": 5}
    assert {"nome": "Sem assessor", "count": 4} in grupos


def test_fechamento_mensal(db, dados_base):
    dep = dados_base["ssu"].id
    db.session.add_all([
        _oficio(dep, datetime(2026, 3, 2, 10), "Ana", True, "maria"),
        _oficio(dep, datetime(2026, 3, 5, 11), "Ana", False, "MARIA "),
        _oficio(dados_base["st"].id, datetime(2026, 3, 9, 9), "", False, "José"),
        _oficio(dep, datetime(2026, 4, 1, 9), "Ana", True),
    ])
    db.session.commit()
    r = relatorios.fechamento_mensal(2026, 3)
    assert (r["total"], r["executados"], r["pendentes"]) == (3, 1, 2)
    assert r["secretarias"][0]["sigla"] == "SSU" and r["secretarias"][0]["count"] == 2
    assert r["total_municipes"] == 2
    assert "Em março de 2026 foram registrados 3 ofício(s)" in r["resumo"]


def test_serie_mensal_inclui_meses_vazios(db, dados_base):
    db.session.add(_oficio(dados_base["ssu"].id, datetime(2026, 1, 10)))
    db.session.commit()
    s = relatorios.serie_mensal(3, referencia=datetime(2026, 2, 15))
    assert s["labels"] == ["Dez/25", "Jan/26", "Fev/26"]
    assert s["total"] == [0, 1, 0]


def test_dados_graficos_por_periodo(db, dados_base):
    dep = dados_base["ssu"].id
    db.session.add_all([_oficio(dep, datetime(2026, 3, 1)), _oficio(dep, datetime(2026, 5, 1))])
    db.session.commit()
    todos = relatorios.dados_graficos()
    assert todos["secretarias"][0]["count"] == 2
    marco = relatorios.dados_graficos(datetime(2026, 3, 1), datetime(2026, 4, 1))
    assert marco["secretarias"][0]["count"] == 1


def test_seed_e_modelos_padrao(app, db):
    assert recriar_modelos() >= 10
    resumo = popular(qtd_oficios=40)
    assert "40 ofícios" in resumo
    numeros = [o.numero for o in Oficio.query.all()]
    assert len(numeros) == len(set(numeros)) == 40
