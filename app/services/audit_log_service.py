import json
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.middleware.request_context import get_client_ip, get_request_id
from app.models.audit_logs import AuditLog
from app.models.users import User


_SENSITIVE_KEYS = {
    "authorization",
    "password",
    "pass",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "otp",
    "secret",
    "api_key",
    "jwt",
}


def _sanitize_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "…"

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if key.lower() in _SENSITIVE_KEYS:
                sanitized[key] = "***redacted***"
            else:
                sanitized[key] = _sanitize_value(v, depth=depth + 1)
        return sanitized

    if isinstance(value, list):
        # Cap list lengths to keep payloads bounded.
        capped = value[:50]
        return [_sanitize_value(v, depth=depth + 1) for v in capped]

    if isinstance(value, str):
        # Keep strings bounded; audit logs should not store huge provider payloads.
        return value if len(value) <= 500 else (value[:497] + "…")

    return value


def sanitize_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}

    sanitized = _sanitize_value(metadata)
    try:
        raw = json.dumps(sanitized, default=str)
        if len(raw) <= 8000:
            return sanitized  # type: ignore[return-value]
    except Exception:
        return {"note": "metadata_unserializable"}

    # Too large: keep a minimal skeleton.
    minimal: dict[str, Any] = {"note": "metadata_truncated"}
    for k in ("event", "status", "reference", "provider", "provider_id", "transfer_code"):
        if isinstance(sanitized, dict) and k in sanitized:
            minimal[k] = sanitized.get(k)
    return minimal


def write_audit_log(
    db: Session,
    *,
    category: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor: Optional[User] = None,
    request: Optional[Request] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    amount: Optional[Decimal] = None,
    currency: Optional[str] = None,
    provider: Optional[str] = None,
    provider_reference: Optional[str] = None,
    payer_user_id: Optional[str] = None,
    payee_user_id: Optional[str] = None,
    payee_gym_id: Optional[str] = None,
    initiated_by_user_id: Optional[str] = None,
    approved_by_user_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog:
    record = AuditLog(
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=getattr(actor, "role", None),
        actor_ip=get_client_ip(request) if request else None,
        user_agent=(request.headers.get("user-agent")[:256] if request and request.headers.get("user-agent") else None),
        request_id=get_request_id(request) if request else None,
        amount=amount,
        currency=(currency.upper()[:8] if currency else None),
        provider=(provider[:32] if provider else None),
        provider_reference=(provider_reference[:128] if provider_reference else None),
        payer_user_id=payer_user_id,
        payee_user_id=payee_user_id,
        payee_gym_id=payee_gym_id,
        initiated_by_user_id=initiated_by_user_id,
        approved_by_user_id=approved_by_user_id,
        success=success,
        error_message=(error_message[:4000] if error_message else None),
        audit_metadata=sanitize_metadata(metadata),
    )
    db.add(record)
    return record
