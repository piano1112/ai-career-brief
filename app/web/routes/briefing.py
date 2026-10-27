from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.web.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def briefing_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "briefing.html")
