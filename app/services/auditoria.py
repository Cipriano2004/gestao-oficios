"""Registro da trilha de auditoria."""

import json

from flask import has_request_context, request
from flask_login import current_user

from ..extensions import db
from ..models import LogAuditoria


def ip_cliente() -> str | None:
    if not has_request_context():
        return None
    return request.remote_addr


def registrar(acao: str, entidade: str | None = None, entidade_id: int | None = None,
              detalhes=None, usuario=None, email: str | None = None,
              commit: bool = True) -> LogAuditoria:
    usuario = usuario if usuario is not None else (
        current_user if has_request_context() and current_user.is_authenticated else None
    )
    if isinstance(detalhes, dict):
        detalhes = json.dumps(detalhes, ensure_ascii=False, default=str)

    log = LogAuditoria(
        usuario_id=getattr(usuario, "id", None),
        usuario_email=email or getattr(usuario, "email", None),
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        ip=ip_cliente(),
        user_agent=(request.user_agent.string[:255] if has_request_context() else None),
        detalhes=detalhes,
    )
    db.session.add(log)
    if commit:
        db.session.commit()
    return log
