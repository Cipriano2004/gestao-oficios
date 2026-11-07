"""Substituição dos placeholders dos modelos de ofício.

Comportamento mantido igual ao sistema original. Placeholders suportados:
[ENDEREÇO] [NÚMERO] [BAIRRO] [EM_FRENTE] [HORARIO] [ENDERECO_FORMATADO]
[MUNICIPE_TRATAMENTO] [MUNICIPE_NOME] [MUNICIPE_TEL] [TELEFONE]
[DATA_EVENTO] [HORA_INICIO] [HORA_FIM] [NUMERO_INICIO] [NUMERO_FIM]
"""

from dataclasses import dataclass, fields

PLACEHOLDERS_DISPONIVEIS = [
    ("[ENDEREÇO]", "Rua/avenida"),
    ("[NÚMERO]", "Número do imóvel"),
    ("[BAIRRO]", "Bairro"),
    ("[EM_FRENTE]", "Ponto de referência"),
    ("[ENDERECO_FORMATADO]", "Rua, número - bairro"),
    ("[MUNICIPE_TRATAMENTO]", "Sr. / Srª"),
    ("[MUNICIPE_NOME]", "Nome do munícipe"),
    ("[MUNICIPE_TEL]", "Telefone do munícipe"),
    ("[DATA_EVENTO]", "Data do evento"),
    ("[HORARIO]", "Horário do evento"),
    ("[HORA_INICIO]", "Hora de início"),
    ("[HORA_FIM]", "Hora de término"),
    ("[NUMERO_INICIO]", "Número inicial do trecho"),
    ("[NUMERO_FIM]", "Número final do trecho"),
]


@dataclass
class DadosPlaceholder:
    endereco: str = ""
    numero_endereco: str = ""
    bairro: str = ""
    em_frente: str = ""
    municipe_tratamento: str = ""
    municipe_nome: str = ""
    municipe_telefone: str = ""
    data_evento: str = ""
    hora_inicio: str = ""
    hora_fim: str = ""
    numero_inicio: str = ""
    numero_fim: str = ""

    @classmethod
    def de_dict(cls, dados) -> "DadosPlaceholder":
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: (dados.get(k) or "").strip() for k in nomes})


def formatar_endereco(endereco: str, numero: str, bairro: str) -> str:
    rua, num, bai = (endereco or "").strip(), (numero or "").strip(), (bairro or "").strip()
    texto = f"{rua}, {num}" if rua and num else (rua or num)
    if bai:
        texto = f"{texto} - {bai}" if texto else bai
    return texto


def processar_placeholders(texto: str, d: DadosPlaceholder) -> str:
    if not texto:
        return texto

    resultado = texto

    if d.endereco:
        resultado = resultado.replace("[ENDEREÇO]", d.endereco)
    if d.numero_endereco:
        resultado = resultado.replace("[NÚMERO]", d.numero_endereco)
    if d.bairro:
        resultado = resultado.replace("[BAIRRO]", d.bairro)

    endereco_formatado = formatar_endereco(d.endereco, d.numero_endereco, d.bairro)
    for ph in ("[ENDERECO_FORMATADO]", "[ENDERECOFORMATADO]"):
        resultado = resultado.replace(ph, endereco_formatado)

    def substituir_com_e_sem_underscore(ph: str, valor: str) -> None:
        nonlocal resultado
        resultado = resultado.replace(ph, valor or "")
        resultado = resultado.replace(ph.replace("_", ""), valor or "")

    substituir_com_e_sem_underscore("[MUNICIPE_TRATAMENTO]", d.municipe_tratamento)
    substituir_com_e_sem_underscore("[MUNICIPE_NOME]", d.municipe_nome)
    substituir_com_e_sem_underscore("[MUNICIPE_TEL]", d.municipe_telefone.strip())
    resultado = resultado.replace("[TELEFONE]", d.municipe_telefone.strip())

    if d.em_frente.strip():
        resultado = resultado.replace("[EM_FRENTE]", d.em_frente)
        resultado = resultado.replace("[HORARIO]", d.em_frente)
    else:
        resultado = resultado.replace(" em frente a [EM_FRENTE]", "")
        resultado = resultado.replace("[EM_FRENTE]", "")
        resultado = resultado.replace("[HORARIO]", "")

    for ph, valor in (
        ("[DATA_EVENTO]", d.data_evento),
        ("[HORA_INICIO]", d.hora_inicio),
        ("[HORA_FIM]", d.hora_fim),
        ("[NUMERO_INICIO]", d.numero_inicio),
        ("[NUMERO_FIM]", d.numero_fim),
    ):
        resultado = resultado.replace(ph, valor or "")

    return resultado
