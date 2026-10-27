"""
Safe Neon PostgreSQL Migration & Admin Setup Script.
Usage in PowerShell:
$env:DATABASE_URL="postgresql://<user>:<password>@<host>/<database>?sslmode=require"
python migrate_neon.py
$env:DATABASE_URL=""
"""
import sys
sys.path.insert(0, r'D:\Task Management')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workline.settings')

db_url = os.getenv('DATABASE_URL', '').strip()
if not db_url:
    print("ERROR: DATABASE_URL environment variable is not set in this terminal session.")
    print("Run: $env:DATABASE_URL=\"<your-neon-url>\" before running this script.")
    sys.exit(1)

import django
django.setup()

from django.db import connection
from django.core.management import call_command
from django.contrib.auth.models import User

# 1. Verify connection
print("=== 1. VERIFYING NEON POSTGRESQL CONNECTION ===")
with connection.cursor() as cursor:
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.execute("SELECT current_database();")
    current_db = cursor.fetchone()[0]

settings_conf = connection.settings_dict
host = settings_conf.get('HOST', 'unknown')
# Mask host for security
masked_host = host[:6] + "..." + host[-15:] if len(host) > 21 else host
print(f"Connected to Database: '{current_db}' on Host: '{masked_host}'")
print(f"PostgreSQL Version: {version.split(',')[0]}")

# 2. Run migrations
print("\n=== 2. RUNNING DJANGO MIGRATIONS ===")
call_command('migrate', interactive=False)

# 3. Securely install / enable Jayraj Admin account
print("\n=== 3. CONFIGURING JAYRAJ ADMIN ACCOUNT ===")
call_command('setup_admin', require_postgresql=True, reuse_local_hash=True, no_migrate=True)

