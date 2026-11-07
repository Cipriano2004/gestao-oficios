"""CRUD dos modelos de ofício (templates de texto com placeholders)."""

import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import Departamento, TemplateOficio
from ...seguranca import PODE_EDITAR, SO_ADMIN, exigir_login, requer_perfil
from ...services import auditoria
from ...services.placeholders import PLACEHOLDERS_DISPONIVEIS
from ...services.templates_padrao import recriar_modelos

bp = Blueprint("modelos", __name__, url_prefix="/modelos")
bp.before_request(exigir_login)

_RE_PH = re.compile(r"\[[A-ZÇÃÉÚ_/]+\]")


def placeholders_usados(texto: str) -> list[str]:
    vistos = []
    for ph in _RE_PH.findall(texto or ""):
        if ph not in vistos:
            vistos.append(ph)
    return vistos


def _obter(modelo_id: int) -> TemplateOficio:
    modelo = db.session.get(TemplateOficio, modelo_id)
    if not modelo:
        abort(404)
    return modelo


def _preencher(modelo: TemplateOficio, form) -> str | None:
    titulo = (form.get("titulo") or "").strip()
    assunto = (form.get("assunto") or "").strip()
    corpo = (form.get("corpo_texto") or "").strip()
    try:
        dep = db.session.get(Departamento, int(form.get("departamento_id") or 0))
    except ValueError:
        dep = None
    if not (titulo and assunto and corpo and dep):
        return "Preencha título, secretaria, assunto e texto."
    modelo.titulo, modelo.assunto, modelo.corpo_texto = titulo[:200], assunto[:300], corpo
    modelo.departamento_id = dep.id
    return None


@bp.get("/")
def lista():
    dep_id = request.args.get("departamento_id", type=int)
    q = TemplateOficio.query.join(Departamento)
    if dep_id:
        q = q.filter(TemplateOficio.departamento_id == dep_id)
    modelos = q.order_by(Departamento.sigla, TemplateOficio.titulo).all()
    return render_template(
        "modelos/lista.html",
        modelos=modelos,
        departamentos=Departamento.query.order_by(Departamento.sigla).all(),
        dep_id=dep_id,
        placeholders_usados=placeholders_usados,
    )


@bp.route("/novo", methods=["GET", "POST"])
@requer_perfil(*PODE_EDITAR)
def novo():
    modelo = TemplateOficio()
    if request.method == "POST":
        erro = _preencher(modelo, request.form)
        if erro:
            flash(erro, "danger")
        else:
            db.session.add(modelo)
            db.session.commit()
            auditoria.registrar("CRIAR", "modelo", modelo.id, {"titulo": modelo.titulo})
            flash("Modelo criado.", "success")
            return redirect(url_for("modelos.lista"))
    return render_template("modelos/form.html", modelo=None, form=request.form,
                           departamentos=Departamento.query.order_by(Departamento.sigla).all(),
                           placeholders=PLACEHOLDERS_DISPONIVEIS)


@bp.route("/<int:modelo_id>/editar", methods=["GET", "POST"])
@requer_perfil(*PODE_EDITAR)
def editar(modelo_id: int):
    modelo = _obter(modelo_id)
    if request.method == "POST":
        erro = _preencher(modelo, request.form)
        if erro:
            db.session.rollback()
            flash(erro, "danger")
        else:
            db.session.commit()
            auditoria.registrar("EDITAR", "modelo", modelo.id, {"titulo": modelo.titulo})
            flash("Modelo atualizado.", "success")
            return redirect(url_for("modelos.lista"))
    form = request.form if request.method == "POST" else {
        "titulo": modelo.titulo, "assunto": modelo.assunto,
        "corpo_texto": modelo.corpo_texto, "departamento_id": modelo.departamento_id,
    }
    return render_template("modelos/form.html", modelo=modelo, form=form,
                           departamentos=Departamento.query.order_by(Departamento.sigla).all(),
                           placeholders=PLACEHOLDERS_DISPONIVEIS)


@bp.post("/<int:modelo_id>/duplicar")
@requer_perfil(*PODE_EDITAR)
def duplicar(modelo_id: int):
    original = _obter(modelo_id)
    copia = TemplateOficio(titulo=f"{original.titulo} (cópia)"[:200], assunto=original.assunto,
                           corpo_texto=original.corpo_texto,
                           departamento_id=original.departamento_id)
    db.session.add(copia)
    db.session.commit()
    auditoria.registrar("CRIAR", "modelo", copia.id, {"duplicado_de": original.id})
    flash("Modelo duplicado. Ajuste o que precisar.", "success")
    return redirect(url_for("modelos.editar", modelo_id=copia.id))


@bp.post("/<int:modelo_id>/excluir")
@requer_perfil(*PODE_EDITAR)
def excluir(modelo_id: int):
    modelo = _obter(modelo_id)
    titulo = modelo.titulo
    db.session.delete(modelo)
    auditoria.registrar("EXCLUIR", "modelo", modelo_id, {"titulo": titulo}, commit=False)
    db.session.commit()
    flash("Modelo excluído.", "success")
    return redirect(url_for("modelos.lista"))


@bp.post("/recriar-padrao")
@requer_perfil(*SO_ADMIN)
def recriar_padrao():
    qtd = recriar_modelos()
    auditoria.registrar("CONFIG", "modelo", None, {"acao": "recriar_padrao", "criados": qtd})
    flash(f"{qtd} modelos padrão recriados.", "success")
    return redirect(url_for("modelos.lista"))
