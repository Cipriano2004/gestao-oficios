"""Geração do ofício em Word (.docx), em memória.

O layout é o mesmo do sistema original (Arial 12, número e data à direita,
destinatário, assunto, corpo com recuo e assinatura centralizada).
O arquivo não é salvo em disco: é gerado a cada download, então nunca fica
desatualizado e nenhum documento com dados pessoais fica exposto em pasta pública.
"""

import re
from datetime import datetime
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt
from flask import current_app

from .formatacao import data_por_extenso

FONTE = "Arial"
TAMANHO = Pt(12)


def _formatar(p, *, antes=0, depois=0, recuo_cm=0.0, alinhamento=None):
    p.paragraph_format.space_before = Pt(antes)
    p.paragraph_format.space_after = Pt(depois)
    if recuo_cm:
        p.paragraph_format.first_line_indent = Cm(recuo_cm)
    if alinhamento is not None:
        p.alignment = alinhamento
    for r in p.runs:
        r.font.name = FONTE
        r.font.size = TAMANHO
    return p


def _paragrafo(doc, texto, *, negrito=False, **fmt):
    p = doc.add_paragraph()
    run = p.add_run(texto)
    run.bold = negrito
    return _formatar(p, **fmt)


def _fonte_padrao(doc):
    estilo = doc.styles["Normal"]
    estilo.font.name = FONTE
    estilo.font.size = TAMANHO
    # garante Arial também para caracteres asiáticos/complexos no Word
    rpr = estilo.element.get_or_add_rPr()
    fontes = rpr.find(qn("w:rFonts"))
    if fontes is None:
        fontes = OxmlElement("w:rFonts")
        rpr.append(fontes)
    fontes.set(qn("w:eastAsia"), FONTE)
    estilo.paragraph_format.space_after = Pt(0)
    estilo.paragraph_format.line_spacing = 1.15


def nome_arquivo(oficio) -> str:
    numero = re.sub(r"[^A-Za-z0-9_\-.]+", "_", oficio.numero or "")
    numero = numero or datetime.now().strftime("%Y%m%d_%H%M%S")
    sigla = oficio.departamento.sigla if oficio.departamento else "GERAL"
    return f"oficio_{numero}_{sigla}.docx"


def gerar_documento(oficio) -> BytesIO:
    cfg = current_app.config
    doc = Document()

    for secao in doc.sections:
        secao.top_margin = Emu(936000)
        secao.bottom_margin = Emu(720000)
        secao.left_margin = Emu(1143000)
        secao.right_margin = Emu(914400)

    _fonte_padrao(doc)
    direita = WD_ALIGN_PARAGRAPH.RIGHT
    centro = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()
    _paragrafo(doc, f"OFÍCIO Nº {oficio.numero}.", negrito=True, depois=6, alinhamento=direita)

    data = oficio.data_criacao or datetime.now()
    _paragrafo(doc, f"{cfg['CIDADE']}, {data_por_extenso(data)}.", negrito=True, depois=18,
               alinhamento=direita)

    if oficio.destinatario:
        _paragrafo(doc, oficio.destinatario, negrito=True, depois=2)
        if oficio.cargo_destinatario:
            _paragrafo(doc, oficio.cargo_destinatario, negrito=True, depois=18)
    else:
        _paragrafo(doc, "A/C: [DESTINATÁRIO]", negrito=True, depois=18)

    _paragrafo(doc, f"ASSUNTO: {oficio.assunto.rstrip('.')}.", negrito=True, depois=14)

    corpo = (oficio.corpo_oficio or "").strip() or "Venho por meio deste ofício solicitar..."
    for linha in corpo.split("\n"):
        if linha.strip():
            _paragrafo(doc, linha.strip(), depois=16, recuo_cm=1.25)
        else:
            _formatar(doc.add_paragraph())

    _paragrafo(doc, "Atenciosamente,", antes=18, depois=10, alinhamento=centro)
    _paragrafo(doc, "_" * 22, depois=6, alinhamento=centro)
    _paragrafo(doc, oficio.nome_responsavel or cfg["RESPONSAVEL_NOME"], negrito=True,
               depois=2, alinhamento=centro)
    _paragrafo(doc, oficio.cargo_responsavel or cfg["RESPONSAVEL_CARGO"], alinhamento=centro)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
