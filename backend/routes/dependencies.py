from fastapi import Header, HTTPException
from backend.config import ADMIN_API_KEY


def require_admin(x_admin_key: str = Header(default="")):
    """Optional admin gate for observability endpoints.

    Enabled only when ADMIN_API_KEY is configured; otherwise these endpoints stay
    open so the personal/demo deployments keep working unchanged.
    """
    if ADMIN_API_KEY and x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
