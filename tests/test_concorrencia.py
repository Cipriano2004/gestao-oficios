"""Numeração sob concorrência real. Só roda com MySQL/MariaDB (TEST_DATABASE_URL), como no CI."""

import threading
from datetime import datetime

import pytest

from app.extensions import db
from app.models import Oficio
from app.services import numeracao

THREADS, POR_THREAD = 12, 5


@pytest.mark.usefixtures("dados_base")
def test_numeros_unicos_e_sem_buracos_com_varios_usuarios(app, dados_base):
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql"):
        pytest.skip("teste de concorrência precisa de MySQL/MariaDB")

    dep_id = dados_base["ssu"].id
    barreira = threading.Barrier(THREADS)
    erros = []

    def usuario():
        with app.app_context():
            barreira.wait()
            try:
                for _ in range(POR_THREAD):
                    numeracao.atribuir_numero(
                        Oficio(assunto="x", destinatario="x", departamento_id=dep_id,
                               data_criacao=datetime.now()),
                        ano=2026,
                    )
            except Exception as erro:  # pragma: no cover - só em caso de falha
                erros.append(repr(erro))
            finally:
                db.session.remove()

    threads = [threading.Thread(target=usuario) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not erros
    seqs = sorted(s for (s,) in db.session.query(Oficio.sequencial))
    assert seqs == list(range(1, THREADS * POR_THREAD + 1))
