import os
from datetime import timedelta
from dotenv import load_dotenv

# Carga variables de entorno desde backend/.env si existe
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# JWT
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret")
ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRES_MIN: int = int(os.getenv("ACCESS_TOKEN_EXPIRES_MIN", "60"))
REFRESH_TOKEN_EXPIRES_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "7"))

# Cookies (access)
COOKIE_NAME: str = os.getenv("AUTH_COOKIE_NAME", "access_token")
COOKIE_SECURE: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE: str = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
COOKIE_DOMAIN: str | None = os.getenv("AUTH_COOKIE_DOMAIN") or None
COOKIE_PATH: str = os.getenv("AUTH_COOKIE_PATH", "/")

# Cookies (refresh)
REFRESH_COOKIE_NAME: str = os.getenv("AUTH_REFRESH_COOKIE_NAME", "refresh_token")
REFRESH_COOKIE_SECURE: bool = os.getenv("AUTH_REFRESH_COOKIE_SECURE", "false").lower() == "true"
REFRESH_COOKIE_SAMESITE: str = os.getenv("AUTH_REFRESH_COOKIE_SAMESITE", "Lax")
REFRESH_COOKIE_DOMAIN: str | None = os.getenv("AUTH_REFRESH_COOKIE_DOMAIN") or None
REFRESH_COOKIE_PATH: str = os.getenv("AUTH_REFRESH_COOKIE_PATH", "/auth")

# CSRF
CSRF_COOKIE_NAME: str = os.getenv("CSRF_COOKIE_NAME", "csrftoken")
CSRF_HEADER_NAME: str = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")

# Seguridad: hashing
BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

# Seguridad: rate limiting login y anti-bruteforce
AUTH_RATE_LIMIT_PER_MIN: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MIN", "10"))
AUTH_LOGIN_FAIL_LIMIT: int = int(os.getenv("AUTH_LOGIN_FAIL_LIMIT", "5"))
AUTH_LOGIN_LOCK_MINUTES: int = int(os.getenv("AUTH_LOGIN_LOCK_MINUTES", "5"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str | None = os.getenv("LOG_FILE") or None

# Password reset / email verification
RESET_TOKEN_EXPIRES_MIN: int = int(os.getenv("RESET_TOKEN_EXPIRES_MIN", "30"))
EMAIL_FROM: str | None = os.getenv("EMAIL_FROM") or None
SMTP_HOST: str | None = os.getenv("SMTP_HOST") or None
SMTP_PORT: int | None = int(os.getenv("SMTP_PORT", "0")) or None
SMTP_USER: str | None = os.getenv("SMTP_USER") or None
SMTP_PASS: str | None = os.getenv("SMTP_PASS") or None
EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_STUB: bool = os.getenv("EMAIL_STUB", "true").lower() == "true"  # en dev, loguear en vez de enviar

# Utilidades de tiempo
def access_token_timedelta() -> timedelta:
    return timedelta(minutes=ACCESS_TOKEN_EXPIRES_MIN)

def refresh_token_timedelta() -> timedelta:
    return timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
