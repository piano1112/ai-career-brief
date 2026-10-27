"""FastAPI 앱 엔트리포인트 (web 컨테이너)."""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.sessions import SessionMiddleware

from app.auth import SESSION_KEY
from app.config import get_settings
from app.web.routes import applications, auth, briefing, calendar, chat, me
from app.web.templating import STATIC_DIR

# 로그인 없이 접근 가능한 경로
PUBLIC_PATHS = ("/login", "/static", "/healthz")


class LoginRequiredMiddleware(BaseHTTPMiddleware):
    """로그인하지 않은 요청은 /login으로 보낸다. 라우트마다 체크하지 않도록 한 곳에서 처리."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith(PUBLIC_PATHS) or request.session.get(SESSION_KEY):
            return await call_next(request)
        # HTMX 요청은 302를 따라가면 페이지 조각 자리에 로그인 화면이 박히므로,
        # HX-Redirect 헤더로 전체 페이지 이동을 지시한다.
        if request.headers.get("HX-Request"):
            return Response(status_code=401, headers={"HX-Redirect": "/login"})
        return RedirectResponse("/login", status_code=303)


def create_app() -> FastAPI:
    settings = get_settings()
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET이 비어 있습니다. .env를 확인하세요 (.env.example 참고).")

    app = FastAPI(title="AI Career Brief")

    # 미들웨어는 나중에 추가한 것이 바깥쪽에서 먼저 실행된다.
    # → SessionMiddleware가 먼저 쿠키를 풀어야 LoginRequiredMiddleware가 session을 읽을 수 있다.
    app.add_middleware(LoginRequiredMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="acb_session",
        max_age=60 * 60 * 24 * 14,  # 14일
        same_site="lax",
        https_only=settings.session_https_only,
    )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    for module in (auth, briefing, chat, applications, calendar, me):
        app.include_router(module.router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
