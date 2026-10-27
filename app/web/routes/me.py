from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.web.templating import templates

router = APIRouter()


@router.get("/me", response_class=HTMLResponse)
def me_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "me.html")
