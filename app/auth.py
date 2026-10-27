"""단일 계정 로그인.

- 비밀번호는 bcrypt 해시로만 보관한다 (.env의 ADMIN_PASSWORD_HASH).
- 로그인 상태는 서명된 세션 쿠키(Starlette SessionMiddleware)에 저장한다.
  1인용이라 사용자 테이블/세션 테이블을 두지 않는다.

해시 생성:  python -m app.auth hash '내비밀번호'
"""

import hmac
import sys

import bcrypt

from app.config import get_settings

SESSION_KEY = "user"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # 해시 형식이 잘못된 경우
        return False


def check_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    # compare_digest: 문자열 비교 시간 차이로 정보가 새지 않게 한다.
    username_ok = hmac.compare_digest(username, settings.admin_username)
    password_ok = verify_password(password, settings.admin_password_hash)
    return username_ok and password_ok


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "hash":
        print(hash_password(sys.argv[2]))
    else:
        print("usage: python -m app.auth hash '<password>'")
        sys.exit(1)
