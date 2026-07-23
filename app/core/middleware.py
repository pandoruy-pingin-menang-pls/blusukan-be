from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token
from app.db.session import async_session_maker
from app.modules.monitoring.models import ActivityLog


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # We only care about modifying actions
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)

        response = await call_next(request)

        # Don't log if the action failed
        if response.status_code >= 400:
            return response

        # Extract token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return response

        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            user_role = payload.get("role")
        except Exception:
            return response

        if user_id:
            # Determine action name based on endpoint
            path = request.url.path
            action = f"Accessed {path}"

            # Simplified async session usage for middleware
            async with async_session_maker() as session:
                log_entry = ActivityLog(
                    user_id=user_id,
                    user_role=user_role,
                    action=action,
                    endpoint=path,
                    method=request.method,
                )
                session.add(log_entry)
                await session.commit()

        return response
