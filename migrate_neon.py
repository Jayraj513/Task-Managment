"""
Safe Neon PostgreSQL Migration & Admin Setup Script for OGFLOW.
Usage:
python migrate_neon.py
"""
import sys
sys.path.insert(0, r'D:\Task Management')

import os
from apps.common.utils import (
    sanitize_postgres_url,
    validate_postgres_url,
    secure_read_url,
)

# 1. Obtain DATABASE_URL
raw_url = os.getenv('DATABASE_URL', '')

if not raw_url and sys.platform == 'win32':
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
            val, _ = winreg.QueryValueEx(key, 'DATABASE_URL')
            raw_url = val or ''
    except (FileNotFoundError, OSError):
        pass

cleaned_url = sanitize_postgres_url(raw_url)
is_valid, err_msg, details = validate_postgres_url(cleaned_url)

if not is_valid:
    print("=" * 80)
    print("OGFLOW — Neon PostgreSQL Database Setup & Migration")
    print("=" * 80)
    print("Where to obtain your Neon connection string:")
    print("  1. Open your Neon Console: https://console.neon.tech")
    print("  2. Select your project and open \"Dashboard\"")
    print("  3. Under \"Connection Details\", select:")
    print("     - Branch: (your main branch, e.g. main)")
    print("     - Database: (e.g. neondb)")
    print("     - Dropdown: \"Connection string\"")
    print("  4. Copy the full URI (or copy DATABASE_URL from Vercel -> Project Settings -> Environment Variables)")
    print("\nAccepted format:")
    print("  postgresql://<user>:<password>@<ep-endpoint>.neon.tech/<dbname>?sslmode=require")
    print("  (including optional query parameters such as &channel_binding=require)")
    print("\n(Input is masked/hidden. Keystrokes will not be echoed or saved to shell history)")
    print("=" * 80)

    try:
        user_input = secure_read_url("Paste or enter Neon DATABASE_URL: ")
        cleaned_url = sanitize_postgres_url(user_input)
        is_valid, err_msg, details = validate_postgres_url(cleaned_url)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError reading input: {e}")
        sys.exit(1)

if not is_valid:
    print(f"\nERROR: {err_msg}")
    print("Please ensure you copy the full connection string starting with 'postgresql://' or 'postgres://'")
    sys.exit(1)

# Store in process memory only
os.environ['DATABASE_URL'] = cleaned_url
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workline.settings')

import django
django.setup()

from django.db import connection
from django.core.management import call_command

# 2. Verify destination database
print("\n=== 1. VERIFYING TARGET DATABASE ===")
with connection.cursor() as cursor:
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.execute("SELECT current_database();")
    current_db = cursor.fetchone()[0]
    cursor.execute("SELECT current_user;")
    current_user = cursor.fetchone()[0]

masked_host = details['masked_host']
is_neon = details['is_neon']

print(f"Target Database:  '{current_db}'")
print(f"Connected User:   '{current_user}'")
print(f"Target Host:       {masked_host}")
print(f"PostgreSQL Build:  {version.split(',')[0]}")
print(f"Provider:          {'Neon PostgreSQL (verified)' if is_neon else 'External/Other PostgreSQL'}")

if not is_neon:
    print(f"\nWARNING: Destination host '{masked_host}' does not end in '.neon.tech'.")
    confirm = input("Are you sure you want to run migrations on this target? [y/N]: ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("Aborted by user.")
        sys.exit(0)

# 3. Run schema migrations
print("\n=== 2. RUNNING DJANGO MIGRATIONS ===")
call_command('migrate', interactive=False, verbosity=1)

# 4. Securely configure Jayraj Admin account
print("\n=== 3. CONFIGURING JAYRAJ ADMIN ACCOUNT ===")
call_command('setup_admin', require_postgresql=True, reuse_local_hash=True, no_migrate=True)

# 5. Clear memory before exit
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']

print("\n" + "=" * 80)
print("SUCCESS: Neon PostgreSQL database is fully migrated and Jayraj admin is ready!")
print("=" * 80)
