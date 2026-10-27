from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.web.templating import templates

router = APIRouter()


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "chat.html")
