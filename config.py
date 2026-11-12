import os
from typing import Dict, Tuple
from urllib.parse import urlsplit


def _required_secret(name: str, minimum_length: int) -> str:
    value = os.environ.get(name, "")
    if len(value) < minimum_length:
        raise RuntimeError(
            f"{name} must be set in the environment and contain at least {minimum_length} characters"
        )
    return value


def _required_setting(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set in the environment")
    return value


def _setting(name: str, default: str) -> str:
    value = os.environ.get(name, default).strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


def _boolean_setting(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() in {"1", "true"}:
        return True
    if value.lower() in {"0", "false"}:
        return False
    raise ValueError(f"{name} must be one of: 1, 0, true, false")


def _integer_setting(name: str, default: int, minimum: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return parsed


def _https_url(name: str, default: str) -> str:
    value = os.environ.get(name, default)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError(f"{name} must be an absolute HTTPS URL without credentials or fragments")
    return value


def _https_origin(name: str, default: str) -> str:
    value = os.environ.get(name, default)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{name} must be an HTTPS origin without credentials, path, or query")
    return value.rstrip("/")


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


class Config:
    SECRET_KEY: str = _required_secret("SECRET_KEY", 32)
    ADMIN_EMAIL: str = _required_setting("ADMIN_EMAIL")
    ADMIN_PASSWORD: str = _required_secret("ADMIN_PASSWORD", 16)
    SQLALCHEMY_DATABASE_URI: str = _setting("DATABASE_URL", "sqlite:///complaints.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": _integer_setting("DB_POOL_RECYCLE_SECONDS", 280, 1),
    }
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = _boolean_setting("COOKIE_SECURE", False)
    DEBUG: bool = _boolean_setting("FLASK_DEBUG", False)
    PER_PAGE: int = _integer_setting("PER_PAGE", 20, 1)
    MAX_PAGE: int = _integer_setting("MAX_PAGE", 100_000, 1)
    CSV_BATCH_SIZE: int = _integer_setting("CSV_BATCH_SIZE", 500, 1)
    LOGIN_LIMIT_WINDOW_MINUTES: int = _integer_setting("LOGIN_LIMIT_WINDOW_MINUTES", 15, 1)
    STUDENT_LOGIN_MAX_ATTEMPTS: int = _integer_setting("STUDENT_LOGIN_MAX_ATTEMPTS", 10, 1)
    ADMIN_LOGIN_MAX_ATTEMPTS: int = _integer_setting("ADMIN_LOGIN_MAX_ATTEMPTS", 5, 1)
    RATE_LIMIT_STORAGE_URI: str = _setting("RATE_LIMIT_STORAGE_URI", "memory://")
    BOOTSTRAP_CSS_URL: str = _https_url(
        "BOOTSTRAP_CSS_URL",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    )
    BOOTSTRAP_ICONS_URL: str = _https_url(
        "BOOTSTRAP_ICONS_URL",
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    )
    BOOTSTRAP_JS_URL: str = _https_url(
        "BOOTSTRAP_JS_URL",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
    )
    GOOGLE_FONTS_ORIGIN: str = _https_origin(
        "GOOGLE_FONTS_ORIGIN", "https://fonts.googleapis.com"
    )
    GOOGLE_FONTS_STATIC_ORIGIN: str = _https_origin(
        "GOOGLE_FONTS_STATIC_ORIGIN", "https://fonts.gstatic.com"
    )
    GOOGLE_FONTS_CSS_URL: str = _https_url(
        "GOOGLE_FONTS_CSS_URL",
        "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,800;1,9..144,500&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Sans:wght@400;500;600&display=swap",
    )
    SCRIPT_CDN_ORIGINS: Tuple[str, ...] = (_origin(BOOTSTRAP_JS_URL),)
    STYLE_CDN_ORIGINS: Tuple[str, ...] = tuple(
        dict.fromkeys(
            (
                _origin(BOOTSTRAP_CSS_URL),
                _origin(BOOTSTRAP_ICONS_URL),
                _origin(GOOGLE_FONTS_CSS_URL),
            )
        )
    )
    FONT_CDN_ORIGINS: Tuple[str, ...] = tuple(
        dict.fromkeys(
            (_origin(BOOTSTRAP_ICONS_URL), _origin(GOOGLE_FONTS_STATIC_ORIGIN))
        )
    )
    ASSET_URLS: Dict[str, str] = {
        "bootstrap_css": BOOTSTRAP_CSS_URL,
        "bootstrap_icons": BOOTSTRAP_ICONS_URL,
        "bootstrap_js": BOOTSTRAP_JS_URL,
        "google_fonts_origin": GOOGLE_FONTS_ORIGIN,
        "google_fonts_static_origin": GOOGLE_FONTS_STATIC_ORIGIN,
        "google_fonts_css": GOOGLE_FONTS_CSS_URL,
    }
