"""
Safe Neon PostgreSQL Migration & Admin Setup Script.
Usage in PowerShell:
python migrate_neon.py
(Prompts securely with hidden input if DATABASE_URL is not already in environment)
"""
import sys
sys.path.insert(0, r'D:\Task Management')

import os
import getpass

def clean_url(raw: str) -> str:
    if not raw:
        return ''
    cleaned = raw.strip().strip('\'"`<> ')
    if cleaned.startswith('psql '):
        cleaned = cleaned[5:].strip().strip('\'"`<> ')
    return cleaned

# 1. Obtain DATABASE_URL securely in memory
db_url = clean_url(os.getenv('DATABASE_URL', ''))

if not db_url and sys.platform == 'win32':
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
            val, _ = winreg.QueryValueEx(key, 'DATABASE_URL')
            db_url = clean_url(val or '')
    except (FileNotFoundError, OSError):
        pass

if not db_url:
    print("=" * 65)
    print("OGFLOW — Neon PostgreSQL Setup")
    print("No DATABASE_URL found in environment.")
    print("Please enter your Neon connection string below.")
    print("(Input is masked/hidden, will NOT be saved to shell history or disk)")
    print("=" * 65)
    try:
        raw_input = getpass.getpass("Enter Neon DATABASE_URL: ")
        db_url = clean_url(raw_input)
    except Exception as e:
        print(f"Error reading input: {e}")
        sys.exit(1)

if not db_url:
    print("ERROR: No connection string provided. Aborting.")
    sys.exit(1)

if not (db_url.startswith('postgresql://') or db_url.startswith('postgres://')):
    print("ERROR: Connection string must start with 'postgresql://' or 'postgres://'")
    sys.exit(1)

# Store in process memory only
os.environ['DATABASE_URL'] = db_url
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workline.settings')

import django
django.setup()

from django.db import connection
from django.core.management import call_command

# 2. Verify connection
print("\n=== 1. VERIFYING NEON POSTGRESQL CONNECTION ===")
with connection.cursor() as cursor:
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.execute("SELECT current_database();")
    current_db = cursor.fetchone()[0]

settings_conf = connection.settings_dict
host = settings_conf.get('HOST', 'unknown')
masked_host = host[:6] + "..." + host[-15:] if len(host) > 21 else host
print(f"Connected to Database: '{current_db}' on Host: '{masked_host}'")
print(f"PostgreSQL Version: {version.split(',')[0]}")

# 3. Run schema migrations
print("\n=== 2. RUNNING DJANGO MIGRATIONS ===")
call_command('migrate', interactive=False, verbosity=1)

# 4. Securely configure Jayraj Admin account
print("\n=== 3. CONFIGURING JAYRAJ ADMIN ACCOUNT ===")
call_command('setup_admin', require_postgresql=True, reuse_local_hash=True, no_migrate=True)

# 5. Clear memory before exit
del os.environ['DATABASE_URL']
print("\nSUCCESS: Neon database is fully migrated and Jayraj admin is ready!")
