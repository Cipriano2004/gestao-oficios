"""Funções pequenas de formatação usadas em templates e documentos."""

from datetime import datetime

MESES = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def nome_mes(mes: int, capitalizar: bool = False) -> str:
    nome = MESES.get(int(mes), "")
    return nome.capitalize() if capitalizar else nome


def data_por_extenso(data: datetime) -> str:
    return f"{data.day} de {MESES[data.month]} de {data.year}"


def data_br(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else ""


def data_hora_br(valor) -> str:
    return valor.strftime("%d/%m/%Y %H:%M") if valor else ""
