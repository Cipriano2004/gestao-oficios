from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user

from ...extensions import db
from ...models import Departamento, Oficio, Secretario, TemplateOficio
from ...seguranca import PODE_EDITAR, SO_ADMIN, exigir_login, requer_perfil
from ...services import auditoria, documento_word, numeracao
from ...services import oficios as svc
from ...services.placeholders import PLACEHOLDERS_DISPONIVEIS

bp = Blueprint("oficios", __name__, url_prefix="/oficios")
bp.before_request(exigir_login)


def _obter(oficio_id: int) -> Oficio:
    oficio = db.session.get(Oficio, oficio_id)
    if not oficio:
        abort(404)
    return oficio


def _contexto_formulario(**extra):
    return {
        "departamentos": Departamento.query.order_by(Departamento.nome).all(),
        "assessores": svc.assessores_conhecidos(),
        "tratamentos": svc.TRATAMENTOS,
        "placeholders": PLACEHOLDERS_DISPONIVEIS,
        "config": current_app.config,
        **extra,
    }


@bp.get("/")
def lista():
    filtros = svc.Filtros.de_args(request.args)
    pagina = request.args.get("pagina", 1, type=int)
    paginacao = svc.consultar(filtros).paginate(
        page=pagina, per_page=current_app.config["ITENS_POR_PAGINA"], error_out=False
    )
    return render_template(
        "oficios/lista.html",
        paginacao=paginacao,
        filtros=filtros,
        departamentos=Departamento.query.order_by(Departamento.sigla).all(),
        assessores=svc.assessores_conhecidos(),
    )


@bp.route("/novo", methods=["GET", "POST"])
@requer_perfil(*PODE_EDITAR)
def novo():
    """Passo 1 e 2 do assistente (formulário). O POST mostra a revisão (passo 3)."""
    if request.method == "POST":
        try:
            rascunho = svc.preparar_rascunho(request.form)
        except svc.OficioInvalido as erro:
            flash(str(erro), "danger")
            return render_template("oficios/form.html",
                                   **_contexto_formulario(form=request.form, modo="novo"))
        return render_template("oficios/revisao.html", rascunho=rascunho, form=request.form)

    return render_template("oficios/form.html", **_contexto_formulario(form={}, modo="novo"))


@bp.post("/confirmar")
@requer_perfil(*PODE_EDITAR)
def confirmar():
    if request.form.get("acao") == "voltar":
        return render_template("oficios/form.html",
                               **_contexto_formulario(form=request.form, modo="novo"))
    try:
        oficio = svc.criar(request.form, current_user)
    except svc.OficioInvalido as erro:
        flash(str(erro), "danger")
        return render_template("oficios/form.html",
                               **_contexto_formulario(form=request.form, modo="novo"))
    auditoria.registrar("CRIAR", "oficio", oficio.id, {"numero": oficio.numero})
    flash(f"Ofício {oficio.numero} criado com sucesso.", "success")
    return redirect(url_for("oficios.detalhe", oficio_id=oficio.id, novo=1))


@bp.route("/registro-manual", methods=["GET", "POST"])
@requer_perfil(*PODE_EDITAR)
def registrar_manual():
    """Registra um ofício cujo número foi definido fora do sistema."""
    if request.method == "POST":
        try:
            oficio = svc.registrar_manual(request.form, current_user)
        except (svc.OficioInvalido, numeracao.NumeroInvalido) as erro:
            db.session.rollback()
            flash(str(erro), "danger")
            return render_template("oficios/form.html",
                                   **_contexto_formulario(form=request.form, modo="manual"))
        auditoria.registrar("CRIAR", "oficio", oficio.id,
                            {"numero": oficio.numero, "manual": True})
        flash(f"Ofício {oficio.numero} registrado com sucesso.", "success")
        return redirect(url_for("oficios.detalhe", oficio_id=oficio.id))
    return render_template("oficios/form.html", **_contexto_formulario(form={}, modo="manual"))


@bp.get("/<int:oficio_id>")
def detalhe(oficio_id: int):
    return render_template("oficios/detalhe.html", oficio=_obter(oficio_id),
                           recem_criado=request.args.get("novo") == "1")


@bp.route("/<int:oficio_id>/editar", methods=["GET", "POST"])
@requer_perfil(*PODE_EDITAR)
def editar(oficio_id: int):
    oficio = _obter(oficio_id)
    if request.method == "POST":
        try:
            svc.atualizar(oficio, request.form)
        except svc.OficioInvalido as erro:
            db.session.rollback()
            flash(str(erro), "danger")
        else:
            auditoria.registrar("EDITAR", "oficio", oficio.id, {"numero": oficio.numero})
            flash("Ofício atualizado.", "success")
            return redirect(url_for("oficios.detalhe", oficio_id=oficio.id))

    form = request.form if request.method == "POST" else {
        "departamento_id": oficio.departamento_id,
        "secretario_id": oficio.secretario_id or "",
        "destinatario": oficio.destinatario or "",
        "cargo_destinatario": oficio.cargo_destinatario or "",
        "assunto": oficio.assunto,
        "corpo_oficio": oficio.corpo_oficio or "",
        "endereco": oficio.endereco or "",
        "numero_endereco": oficio.numero_endereco or "",
        "bairro": oficio.bairro or "",
        "em_frente": oficio.em_frente or "",
        "assessor_nome": oficio.assessor_nome or "",
        "municipe_tratamento": oficio.municipe_tratamento or "",
        "municipe_nome": oficio.municipe_nome or "",
        "municipe_telefone": oficio.municipe_telefone or "",
        "nome_responsavel": oficio.nome_responsavel or "",
        "cargo_responsavel": oficio.cargo_responsavel or "",
    }
    return render_template("oficios/form.html",
                           **_contexto_formulario(form=form, modo="editar", oficio=oficio))


@bp.post("/<int:oficio_id>/excluir")
@requer_perfil(*SO_ADMIN)
def excluir(oficio_id: int):
    oficio = _obter(oficio_id)
    numero = oficio.numero
    db.session.delete(oficio)
    auditoria.registrar("EXCLUIR", "oficio", oficio_id, {"numero": numero}, commit=False)
    db.session.commit()
    flash(f"Ofício {numero} excluído.", "success")
    return redirect(url_for("oficios.lista"))


@bp.route("/<int:oficio_id>/renumerar", methods=["GET", "POST"])
@requer_perfil(*SO_ADMIN)
def renumerar(oficio_id: int):
    oficio = _obter(oficio_id)
    if request.method == "POST":
        anterior = oficio.numero
        try:
            numeracao.aplicar_numero_manual(oficio, request.form.get("novo_numero"),
                                            ignorar_id=oficio.id)
            db.session.commit()
        except numeracao.NumeroInvalido as erro:
            db.session.rollback()
            flash(str(erro), "danger")
        else:
            auditoria.registrar("RENUMERAR", "oficio", oficio.id,
                                {"de": anterior, "para": oficio.numero})
            flash(f"Ofício renumerado de {anterior} para {oficio.numero}.", "success")
            return redirect(url_for("oficios.detalhe", oficio_id=oficio.id))
    return render_template("oficios/renumerar.html", oficio=oficio)


@bp.get("/<int:oficio_id>/download")
def download(oficio_id: int):
    oficio = _obter(oficio_id)
    return send_file(
        documento_word.gerar_documento(oficio),
        as_attachment=True,
        download_name=documento_word.nome_arquivo(oficio),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@bp.post("/<int:oficio_id>/executado")
@requer_perfil(*PODE_EDITAR)
def marcar_executado(oficio_id: int):
    oficio = _obter(oficio_id)
    dados = request.get_json(silent=True) or {}
    oficio.executado = bool(dados.get("executado"))
    auditoria.registrar("EDITAR", "oficio", oficio.id,
                        {"numero": oficio.numero, "executado": oficio.executado}, commit=False)
    db.session.commit()
    return jsonify(sucesso=True, oficio_id=oficio.id, executado=oficio.executado)


@bp.get("/api/secretarios/<int:departamento_id>")
def api_secretarios(departamento_id: int):
    secretarios = Secretario.query.filter_by(departamento_id=departamento_id).order_by(
        Secretario.nome).all()
    return jsonify(secretarios=[{"id": s.id, "nome": s.nome, "cargo": s.cargo}
                                for s in secretarios])


@bp.get("/api/modelos/<int:departamento_id>")
def api_modelos(departamento_id: int):
    modelos = TemplateOficio.query.filter_by(departamento_id=departamento_id).order_by(
        TemplateOficio.titulo).all()
    return jsonify(modelos=[{"id": t.id, "titulo": t.titulo, "assunto": t.assunto,
                             "corpo_texto": t.corpo_texto} for t in modelos])
