from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.web.templating import templates

router = APIRouter()


@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "calendar.html")
