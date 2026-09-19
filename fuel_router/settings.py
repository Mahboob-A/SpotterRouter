"""Django settings for the fuel router service."""

import os
from pathlib import Path

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = _env_bool("DEBUG", True)
ALLOWED_HOSTS = _env_list(
    "ALLOWED_HOSTS",
    "spotterrouter.mahboob.engineer,localhost,127.0.0.1,backend,nginx,testserver",
)

# Reverse proxy and HTTPS configuration
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = _env_list(
    "CSRF_TRUSTED_ORIGINS",
    "https://spotterrouter.mahboob.engineer,http://localhost:8000,http://localhost:8080,http://127.0.0.1:8000",
)



# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.gis",
    "django.contrib.postgres",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "api",
    "stations",
    "routing",
    "trips",
    "explanations",
    "ui",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fuel_router.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "fuel_router.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgis://fuel_router:fuel_router@db:5432/fuel_router",
)
DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
    )
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_API_BASE_URL = os.environ.get(
    "FIREWORKS_API_BASE_URL",
    "https://api.fireworks.ai/inference/v1/chat/completions",
)
FIREWORKS_LLM_MODEL_NAME = os.environ.get(
    "FIREWORKS_LLM_MODEL_NAME",
    "accounts/fireworks/models/deepseek-v4p1-flash",
)

# --- Interactive Map Tile Provider (MapTiler Cloud) ---
MAPTILER_API_KEY = os.environ.get("MAPTILER_API_KEY", "").strip()

_maptiler_streets_url = (
    "https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png"
    f"?key={MAPTILER_API_KEY}"
)
_default_tile_url = (
    _maptiler_streets_url
    if MAPTILER_API_KEY
    else "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
)
_default_attribution = (
    '<a href="https://www.maptiler.com/copyright/" target="_blank">'
    "&copy; MapTiler</a> "
    '<a href="https://www.openstreetmap.org/copyright" target="_blank">'
    "&copy; OpenStreetMap contributors</a>"
    if MAPTILER_API_KEY
    else (
        '&copy; <a href="https://www.openstreetmap.org/copyright">'
        "OpenStreetMap</a> contributors "
        '&copy; <a href="https://carto.com/attributions">CARTO</a>'
    )
)


def _int_env(key: str, default: int) -> int:
    val = os.environ.get(key, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


MAP_TILE_URL = os.environ.get("MAP_TILE_URL", "").strip() or _default_tile_url
MAP_TILE_ATTRIBUTION = (
    os.environ.get("MAP_TILE_ATTRIBUTION", "").strip() or _default_attribution
)
MAP_TILE_SUBDOMAINS = (
    os.environ.get("MAP_TILE_SUBDOMAINS", "").strip()
    or ("" if MAPTILER_API_KEY else "abcd")
)
MAP_TILE_SIZE = _int_env("MAP_TILE_SIZE", 512 if MAPTILER_API_KEY else 256)
MAP_TILE_ZOOM_OFFSET = _int_env(
    "MAP_TILE_ZOOM_OFFSET", -1 if MAPTILER_API_KEY else 0
)
MAP_TILE_MAX_ZOOM = _int_env("MAP_TILE_MAX_ZOOM", 19)


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "api.exceptions.custom_exception_handler",
}
