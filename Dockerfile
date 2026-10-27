FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 의존성만 먼저 설치해서, 코드만 바뀌었을 때는 이 레이어를 캐시로 재사용한다.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# web/worker 모두 같은 이미지를 쓰고, 실행 명령만 docker-compose.yml에서 다르게 준다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
