"""
Django settings for Workline project.
An original ClickUp-inspired work and project management web application.
"""

from pathlib import Path
import os
import sys

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-workline-team-management-secret-key-development-2026'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',')
    if host.strip()
]

# Vercel deployment support
VERCEL_URL = os.getenv('VERCEL_URL')
if VERCEL_URL and VERCEL_URL not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(VERCEL_URL)

for vhost in ['ogflow.vercel.app', '.vercel.app']:
    if vhost not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(vhost)

# Render cloud hosting support
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Honor X-Forwarded-Proto header for request.is_secure() behind reverse proxies
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',

    # Workline modular apps
    'apps.accounts.apps.AccountsConfig',
    'apps.workspaces.apps.WorkspacesConfig',
    'apps.projects.apps.ProjectsConfig',
    'apps.tasks.apps.TasksConfig',
    'apps.analytics.apps.AnalyticsConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.common.apps.CommonConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'workline.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.common.context_processors.workline_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'workline.wsgi.application'

# Database configuration
# - Production/PostgreSQL: Configured via DATABASE_URL environment variable
# - Vercel Serverless: Requires DATABASE_URL (ephemeral SQLite disabled in production)
# - Local Development: Defaults to SQLite database at BASE_DIR / 'db.sqlite3'
def clean_database_url(raw: str) -> str:
    if not raw:
        return ''
    cleaned = raw.strip().strip('\'"`<> ')
    if cleaned.startswith('psql '):
        cleaned = cleaned[5:].strip().strip('\'"`<> ')
    return cleaned

DATABASE_URL = clean_database_url(os.getenv('DATABASE_URL', ''))
if not DATABASE_URL and sys.platform == 'win32':
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
            val, _ = winreg.QueryValueEx(key, 'DATABASE_URL')
            DATABASE_URL = clean_database_url(val or '')
    except (FileNotFoundError, OSError):
        pass

IS_VERCEL = os.getenv('VERCEL') == '1' or bool(os.getenv('VERCEL_URL'))

if DATABASE_URL:
    if not (DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')):
        if IS_VERCEL:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "DATABASE_URL must be a valid PostgreSQL connection string starting with postgresql:// or postgres://"
            )
        else:
            import warnings
            warnings.warn(
                "Ignoring invalid local DATABASE_URL (must start with postgresql:// or postgres://). Falling back to SQLite."
            )
            DATABASE_URL = ''

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.getenv('CONN_MAX_AGE', '0' if IS_VERCEL else '600')),
            conn_health_checks=False if IS_VERCEL else True,
        )
    }
elif IS_VERCEL:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DATABASE_URL environment variable is required on Vercel for persistent PostgreSQL storage. "
        "Ephemeral SQLite is disabled in production to prevent data loss."
    )
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User attachments)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth redirect settings
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'overview'
LOGOUT_REDIRECT_URL = 'login'

# CSRF Trusted Origins for proxy/production support
CSRF_TRUSTED_ORIGINS = []
csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS.extend([orig.strip() for orig in csrf_origins.split(',') if orig.strip()])
if VERCEL_URL:
    CSRF_TRUSTED_ORIGINS.extend([
        f'https://{VERCEL_URL}',
        f'http://{VERCEL_URL}',
    ])
CSRF_TRUSTED_ORIGINS.extend([
    'https://ogflow.vercel.app',
    'http://ogflow.vercel.app',
    'https://*.vercel.app',
    'http://*.vercel.app',
    'https://*.onrender.com',
    'http://*.onrender.com',
])
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.extend([
        f'https://{RENDER_EXTERNAL_HOSTNAME}',
        f'http://{RENDER_EXTERNAL_HOSTNAME}',
    ])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# Custom user-friendly CSRF failure view
CSRF_FAILURE_VIEW = 'apps.accounts.views.csrf_failure_view'

# Cookie and proxy security settings
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# Maximum file upload size: 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
