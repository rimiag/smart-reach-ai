"""
Unsubscribe Endpoint

Public (no auth) unsubscribe link included in the footer of every outreach
email. Tokens are deterministic per lead and verified before suppression.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.db.base import get_db
from app.services.email_service import email_service

router = APIRouter()

PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Unsubscribed</title>
<style>body{{font-family:system-ui,sans-serif;background:#f8fafc;color:#1f2937;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);
padding:40px;max-width:420px;text-align:center}}</style></head>
<body><div class="card"><h1>{title}</h1><p>{message}</p></div></body></html>"""


@router.get("/{lead_id}/{token}", response_class=HTMLResponse)
async def unsubscribe(lead_id: int, token: str) -> HTMLResponse:
    """One-click unsubscribe: verifies the token and suppresses the email."""
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        ok = await email_service.unsubscribe_by_token(db, lead_id, token)

    if ok:
        return HTMLResponse(
            PAGE.format(
                title="You're unsubscribed",
                message="You won't receive any further outreach emails from us. "
                "Sorry for the interruption.",
            )
        )
    return HTMLResponse(
        PAGE.format(
            title="Link not valid",
            message="This unsubscribe link is not valid or has expired. "
            "If you keep receiving email, reply to it and we'll remove you manually.",
        ),
        status_code=400,
    )
