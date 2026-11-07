"""Exportação dos ofícios para Excel."""

from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

COLUNAS = [
    ("Número", 12), ("Status", 12), ("Assunto", 60), ("Secretaria", 12),
    ("Destinatário", 30), ("Data", 17), ("Assessor", 22), ("Munícipe", 28), ("Telefone", 16),
]


def gerar_planilha(oficios) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ofícios"

    ws.append([c for c, _ in COLUNAS])
    cabecalho = PatternFill("solid", fgColor="1D4ED8")
    for i, (_, largura) in enumerate(COLUNAS, start=1):
        celula = ws.cell(row=1, column=i)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = cabecalho
        celula.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = largura

    for o in oficios:
        ws.append([
            o.numero,
            o.status,
            o.assunto,
            o.departamento.sigla if o.departamento else "",
            o.destinatario or "",
            o.data_criacao.strftime("%d/%m/%Y %H:%M") if o.data_criacao else "",
            o.assessor_nome or "",
            o.municipe_nome or "",
            o.municipe_telefone or "",
        ])

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def nome_planilha(sufixo: str = "") -> str:
    return f"oficios{sufixo}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
