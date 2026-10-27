"""
WSGI config for workline project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workline.settings')

application = get_wsgi_application()

# Ensure SQLite database schema exists if deployed in a serverless environment (like Vercel)
if os.getenv('VERCEL') == '1' or os.getenv('VERCEL_URL'):
    try:
        from django.db import connection
        from django.core.management import call_command
        tables = connection.introspection.table_names()
        if 'auth_user' not in tables:
            call_command('migrate', interactive=False, verbosity=0)
    except Exception as e:
        import sys
        print(f"Vercel DB migration check failed: {e}", file=sys.stderr)
