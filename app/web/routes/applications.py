from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.web.templating import templates

router = APIRouter()


@router.get("/applications", response_class=HTMLResponse)
def applications_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "applications.html")
