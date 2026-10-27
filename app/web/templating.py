"""Jinja2 템플릿 설정. 모든 라우트가 이 templates 객체를 공유한다."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"

templates = Jinja2Templates(directory=WEB_DIR / "templates")

# 사이드바 메뉴: (URL, 라벨, 아이콘). base.html에서 이 목록으로 메뉴를 그린다.
NAV_ITEMS = [
    ("/", "브리핑", "📰"),
    ("/chat", "대화", "💬"),
    ("/applications", "지원현황", "📋"),
    ("/calendar", "캘린더", "📅"),
    ("/me", "나에 대해", "🙂"),
]
templates.env.globals["nav_items"] = NAV_ITEMS
