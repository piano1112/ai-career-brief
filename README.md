# ai-career-brief

매일 07:00에 "지금 나에게 중요한" AI 동향 + 대기업 채용 정보 + 오늘 할 일 제안을 발행하고,
대화를 통해 사용자를 점점 더 정확히 알아가는 개인용 웹앱. 명세는 [SPEC.md](SPEC.md),
설계 결정 기록은 [docs/decisions.md](docs/decisions.md).

**현재 상태: Milestone 1 (뼈대)** — 로그인, 기본 레이아웃, DB 스키마, worker 스케줄러.

## 구성

| 컨테이너 | 역할 | 실행 명령 |
|---|---|---|
| `db` | PostgreSQL 16 | — |
| `web` | FastAPI (대화 에이전트, 화면) | `alembic upgrade head && uvicorn app.main:app` |
| `worker` | APScheduler (백그라운드 에이전트) | `python worker.py` |

## 실행 (Docker Compose)

### 1. `.env` 만들기

```bash
cp .env.example .env
```

### 2. 로그인 설정

비밀번호 해시와 세션 비밀키를 만들어 `.env`에 넣는다. 해시는 컨테이너 안에서 만들면 로컬에 아무것도 설치하지 않아도 된다 (로컬 venv가 있으면 `python -m app.auth hash ...`).

```bash
docker compose run --rm --no-deps web python -m app.auth hash '내비밀번호'
```

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```
ADMIN_USERNAME=me
ADMIN_PASSWORD_HASH='$2b$12$....'   # 반드시 작은따옴표로 감싼다 ($ 때문)
SESSION_SECRET=<위에서 만든 값>
```

### 3. 실행

```bash
docker compose up -d --build
```

- 웹: http://localhost:8000 → 로그인 화면
- 헬스체크: http://localhost:8000/healthz

### 4. 확인

```bash
docker compose ps
```

```bash
docker compose logs -f worker
```

worker 로그에 1분마다 `heartbeat ok — db now() = ...` 가 찍히면 스케줄러와 DB 연결이 정상이다.

```bash
docker compose exec db psql -U brief -d brief -c '\dt'
```

SPEC 섹션 4의 14개 테이블 + `alembic_version`이 보이면 마이그레이션이 정상이다.

## 로컬 개발 (Docker 없이)

Python 3.12+ 와 PostgreSQL이 필요하다. DB만 Docker로 띄워도 된다: `docker compose up -d db`

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements-dev.txt
```

```bash
alembic upgrade head
```

```bash
uvicorn app.main:app --reload
```

```bash
python worker.py
```

### 테스트 / 린트

```bash
pytest
```

```bash
ruff check . && ruff format --check .
```

### 스키마를 바꿀 때

`app/db/models.py`를 수정한 뒤:

```bash
alembic revision --autogenerate -m "변경 내용"
```

생성된 `migrations/versions/*.py`를 **반드시 읽어보고** (autogenerate는 enum 변경 등을 놓친다) `alembic upgrade head`.

## 디렉터리

```
app/
  main.py              # FastAPI 앱 + 로그인 미들웨어
  config.py            # 환경변수 (여기서만 읽는다)
  auth.py              # 단일 계정 로그인 (bcrypt)
  db/                  # models.py (스키마), session.py
  agents/background/   # scheduler.py, jobs/*.py
  web/
    routes/            # 화면별 라우트
    templates/         # Jinja2 (base.html = 사이드바 레이아웃)
    static/vendor/     # htmx, tailwind (CDN 대신 파일로 포함)
worker.py              # 백그라운드 엔트리포인트
migrations/            # Alembic
tests/
docs/decisions.md      # 설계 결정 기록
```
