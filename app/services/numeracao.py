"""Regras de numeração dos ofícios (formato 001/2026).

O próximo número considera: maior sequencial já usado no ano, números reservados
(feitos fora do sistema) e o "próximo número desejado" configurado manualmente.
A geração trava a linha de configuração do ano (SELECT ... FOR UPDATE) e a tabela
tem UNIQUE(ano, sequencial), então dois usuários ao mesmo tempo não recebem o mesmo número.
"""

import random
import re
import time
from datetime import datetime

from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, OperationalError

from ..extensions import db
from ..models import NumeracaoConfig, NumeroReserva, Oficio

_RE_NUMERO = re.compile(r"^\s*(\d{1,6})\s*/\s*(\d{4})\s*$")
LIMITE_BUSCA = 1000
JANELA_MAPA = 49


class NumeroInvalido(ValueError):
    pass


def ano_atual() -> int:
    return datetime.now().year


def formatar_numero(sequencial: int, ano: int) -> str:
    return f"{int(sequencial):03d}/{int(ano)}"


def parse_numero(numero: str) -> tuple[int, int] | None:
    """'223/2026' -> (223, 2026). Retorna None se não estiver no formato padrão."""
    if not numero:
        return None
    m = _RE_NUMERO.match(str(numero))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def proximo_desejado(ano: int) -> int:
    cfg = NumeracaoConfig.query.filter_by(ano=int(ano)).first()
    return int(cfg.offset) if cfg else 0


def definir_proximo_desejado(ano: int, valor: int) -> None:
    if int(valor) < 1:
        raise NumeroInvalido("O próximo número precisa ser maior que zero.")
    cfg = NumeracaoConfig.query.filter_by(ano=int(ano)).first()
    if cfg:
        cfg.offset = int(valor)
    else:
        db.session.add(NumeracaoConfig(ano=int(ano), offset=int(valor)))
    db.session.commit()


def esta_reservado(ano: int, sequencial: int) -> bool:
    return (
        NumeroReserva.query.filter_by(ano=int(ano), sequencial=int(sequencial)).first()
        is not None
    )


def esta_em_uso(ano: int, sequencial: int) -> bool:
    return (
        Oficio.query.filter_by(ano=int(ano), sequencial=int(sequencial)).first() is not None
        or Oficio.query.filter_by(numero=formatar_numero(sequencial, ano)).first() is not None
    )


def calcular_proximo_sequencial(ano: int) -> int:
    """Próximo sequencial livre do ano (sem reservar)."""
    ano = int(ano)
    maximo = db.session.query(func.max(Oficio.sequencial)).filter(Oficio.ano == ano).scalar()
    base = current_app.config["NUMERACAO_INICIAL"] if maximo is None else maximo + 1

    desejado = proximo_desejado(ano)
    if desejado > base:
        base = desejado
    base = max(1, int(base))

    for _ in range(LIMITE_BUSCA):
        if esta_em_uso(ano, base) or esta_reservado(ano, base):
            base += 1
            continue
        return base
    return base


def _garantir_linha_do_ano(ano: int) -> None:
    """Cria (em transação própria) a linha do ano usada como trava, se ainda não existir."""
    if NumeracaoConfig.query.filter_by(ano=ano).first():
        return
    try:
        db.session.add(NumeracaoConfig(ano=ano, offset=0))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()  # outra requisição criou ao mesmo tempo: tudo certo


def atribuir_numero(oficio: Oficio, ano: int | None = None, tentativas: int = 6) -> Oficio:
    """Atribui o próximo número ao ofício e faz o commit, de forma segura contra concorrência.

    1. garante a linha do ano em `numeracao_config`;
    2. trava essa linha com SELECT ... FOR UPDATE (as outras requisições esperam na fila);
    3. calcula o próximo número livre, insere o ofício e faz commit (libera a trava).
    Se mesmo assim houver conflito (UNIQUE ou deadlock), desfaz e tenta de novo.
    """
    ano = int(ano or ano_atual())
    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            _garantir_linha_do_ano(ano)
            NumeracaoConfig.query.filter_by(ano=ano).with_for_update().one()
            seq = calcular_proximo_sequencial(ano)
            oficio.ano, oficio.sequencial = ano, seq
            oficio.numero = formatar_numero(seq, ano)
            db.session.add(oficio)
            db.session.commit()
            return oficio
        except (IntegrityError, OperationalError) as erro:
            db.session.rollback()
            ultimo_erro = erro
            time.sleep(random.uniform(0.02, 0.08) * (tentativa + 1))
    raise RuntimeError("Não foi possível gerar um número único para o ofício.") from ultimo_erro


def aplicar_numero_manual(oficio: Oficio, numero: str, ignorar_id: int | None = None) -> None:
    """Define um número digitado à mão (registro manual / renumeração) validando duplicidade."""
    numero = (numero or "").strip()
    if not numero:
        raise NumeroInvalido("Informe o número do ofício.")

    consulta = Oficio.query.filter(Oficio.numero == numero)
    if ignorar_id:
        consulta = consulta.filter(Oficio.id != ignorar_id)
    if consulta.first():
        raise NumeroInvalido(f"O número {numero} já está em uso por outro ofício.")

    partes = parse_numero(numero)
    if partes:
        seq, ano = partes
        numero = formatar_numero(seq, ano)
        dup = Oficio.query.filter_by(ano=ano, sequencial=seq)
        if ignorar_id:
            dup = dup.filter(Oficio.id != ignorar_id)
        if dup.first():
            raise NumeroInvalido(f"O número {numero} já está em uso por outro ofício.")
        oficio.ano, oficio.sequencial = ano, seq
    else:
        oficio.ano, oficio.sequencial = None, None
    oficio.numero = numero


def mapa_do_ano(ano: int) -> dict:
    """Situação de cada sequencial do ano: OFICIO, RESERVADO ou LIVRE (janela visível)."""
    ano = int(ano)
    proximo = calcular_proximo_sequencial(ano)

    usados = {
        seq: (oid, numero, assunto)
        for seq, oid, numero, assunto in db.session.query(
            Oficio.sequencial, Oficio.id, Oficio.numero, Oficio.assunto
        ).filter(Oficio.ano == ano, Oficio.sequencial.isnot(None))
    }
    reservas = {
        r.sequencial: r.motivo or ""
        for r in NumeroReserva.query.filter_by(ano=ano).all()
    }

    # janela: os últimos ~50 números antes do próximo e 10 depois
    inicio = max(1, proximo - JANELA_MAPA)
    fim = proximo + 10

    numeros = []
    for seq in range(inicio, fim + 1):
        if seq in usados:
            oid, _numero, assunto = usados[seq]
            numeros.append({"sequencial": seq, "status": "OFICIO", "oficio_id": oid,
                            "assunto": assunto, "motivo": None})
        elif seq in reservas:
            numeros.append({"sequencial": seq, "status": "RESERVADO", "oficio_id": None,
                            "assunto": None, "motivo": reservas[seq]})
        else:
            numeros.append({"sequencial": seq, "status": "LIVRE", "oficio_id": None,
                            "assunto": None, "motivo": None,
                            "proximo": seq == proximo})

    return {
        "ano": ano,
        "proximo": formatar_numero(proximo, ano),
        "proximo_seq": proximo,
        "numeros": numeros,
        "inicio": inicio,
        "reservas": [{"sequencial": k, "motivo": v} for k, v in sorted(reservas.items())],
        "total_usados": len(usados),
        "total_reservados": len(reservas),
    }


def reservar(ano: int, sequencial: int, motivo: str = "") -> NumeroReserva:
    if sequencial < 1:
        raise NumeroInvalido("Informe um número válido.")
    numero = formatar_numero(sequencial, ano)
    if esta_em_uso(ano, sequencial):
        raise NumeroInvalido(f"Já existe um ofício com o número {numero}.")
    if esta_reservado(ano, sequencial):
        raise NumeroInvalido(f"O número {numero} já está reservado.")
    reserva = NumeroReserva(ano=ano, sequencial=sequencial,
                            motivo=(motivo or "feito fora do sistema")[:200])
    db.session.add(reserva)
    db.session.commit()
    return reserva


def liberar(ano: int, sequencial: int) -> bool:
    reserva = NumeroReserva.query.filter_by(ano=ano, sequencial=sequencial).first()
    if not reserva:
        return False
    db.session.delete(reserva)
    db.session.commit()
    return True
