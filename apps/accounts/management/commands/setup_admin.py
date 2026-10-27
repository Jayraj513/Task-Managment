"""
Management command to safely initialize or enable the jayraj admin account in production (Neon PostgreSQL).
Usage:
python manage.py setup_admin [--database-url "<URL>"] [--password "<PWD>"] [--require-postgresql] [--reuse-local-hash] [--no-migrate]
"""
import sys
import sqlite3
import getpass
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection, connections
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile, Role
from django.conf import settings
import dj_database_url


def clean_url(raw: str) -> str:
    if not raw:
        return ''
    cleaned = raw.strip().strip('\'"`<> ')
    if cleaned.startswith('psql '):
        cleaned = cleaned[5:].strip().strip('\'"`<> ')
    return cleaned


class Command(BaseCommand):
    help = 'Safely runs migrations and creates/enables the jayraj admin account in PostgreSQL without touching demo data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database-url',
            type=str,
            default=None,
            help='Neon PostgreSQL connection string (starting with postgresql:// or postgres://)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Password to set for admin jayraj (e.g. Jayraj123)',
        )
        parser.add_argument(
            '--require-postgresql',
            action='store_true',
            help='Fail if the target database is not PostgreSQL',
        )
        parser.add_argument(
            '--reuse-local-hash',
            action='store_true',
            help='Reuse the verified password hash from local db.sqlite3',
        )
        parser.add_argument(
            '--no-migrate',
            action='store_true',
            help='Skip running schema migrations before setting up admin',
        )

    def handle(self, *args, **options):
        db_url = clean_url(options.get('database_url') or '')

        # Fallback to env or Windows User registry
        if not db_url:
            import os
            db_url = clean_url(os.getenv('DATABASE_URL', ''))
            if not db_url and sys.platform == 'win32':
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
                        val, _ = winreg.QueryValueEx(key, 'DATABASE_URL')
                        db_url = clean_url(val or '')
                except (FileNotFoundError, OSError):
                    pass

        # If user explicitly provided db_url or found it in env/registry, reconfigure connection
        if db_url:
            if not (db_url.startswith('postgresql://') or db_url.startswith('postgres://')):
                raise CommandError(
                    "DATABASE_URL must be a valid PostgreSQL connection string starting with postgresql:// or postgres://"
                )
            connections.close_all()
            settings.DATABASES['default'] = dj_database_url.parse(
                db_url,
                conn_max_age=600,
                conn_health_checks=True,
            )

        vendor = connection.vendor
        conf = connection.settings_dict
        db_name = conf.get('NAME', 'unknown')
        host = conf.get('HOST', 'localhost')

        if (options['require_postgresql'] or db_url) and vendor != 'postgresql':
            raise CommandError(
                f"Aborted: Target database is {vendor}, but PostgreSQL is required. "
                "Specify --database-url \"postgresql://...\" or set DATABASE_URL before running."
            )

        # Mask host for security
        masked_host = (host[:6] + "..." + host[-15:]) if len(host) > 21 else host
        self.stdout.write(self.style.NOTICE(f"Target Database: {vendor.upper()} ('{db_name}' on '{masked_host}')"))

        # Verify connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")

        # 2. Schema migrations
        if not options['no_migrate']:
            self.stdout.write(self.style.NOTICE("Running schema migrations..."))
            call_command('migrate', interactive=False, verbosity=1)

        # 3. Setup Jayraj Admin Account
        self.stdout.write(self.style.NOTICE("Configuring admin account 'jayraj'..."))
        user = User.objects.filter(username='jayraj').first()

        # Check local hash if requested or available
        local_hash = None
        local_db_path = settings.BASE_DIR / 'db.sqlite3'
        if local_db_path.exists():
            try:
                conn = sqlite3.connect(str(local_db_path))
                c = conn.cursor()
                c.execute("SELECT password, email, first_name, last_name FROM auth_user WHERE username='jayraj'")
                row = c.fetchone()
                conn.close()
                if row:
                    local_hash, local_email, local_fn, local_ln = row
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not read local hash: {e}"))

        chosen_password = options.get('password')

        if not user:
            user = User(
                username='jayraj',
                email='jayraj.borde@gmail.com',
                first_name='Jayraj',
                last_name='Borde',
                is_superuser=True,
                is_staff=True,
                is_active=True,
            )
            if chosen_password:
                user.set_password(chosen_password)
                user.save()
                self.stdout.write(self.style.SUCCESS("Created 'jayraj' with requested password."))
            elif local_hash and local_hash.startswith(('pbkdf2_sha256$', 'argon2$', 'bcrypt$')):
                user.password = local_hash
                user.save()
                self.stdout.write(self.style.SUCCESS("Created 'jayraj' with verified password hash from local database."))
            else:
                self.stdout.write("Enter password for new admin 'jayraj':")
                pwd = getpass.getpass("Password: ")
                user.set_password(pwd)
                user.save()
                self.stdout.write(self.style.SUCCESS("Created 'jayraj' with new password."))
        else:
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            update_fields = ['is_superuser', 'is_staff', 'is_active']
            if chosen_password:
                user.set_password(chosen_password)
                update_fields.append('password')
                user.save(update_fields=update_fields)
                self.stdout.write(self.style.SUCCESS("Updated existing 'jayraj' with requested password."))
            elif local_hash and local_hash.startswith(('pbkdf2_sha256$', 'argon2$', 'bcrypt$')):
                user.password = local_hash
                update_fields.append('password')
                user.save(update_fields=update_fields)
                self.stdout.write(self.style.SUCCESS("Updated existing 'jayraj' with verified password hash from local database."))
            else:
                user.save(update_fields=update_fields)
                self.stdout.write(self.style.SUCCESS("Updated existing 'jayraj' to Superuser & Staff."))

        # Ensure UserProfile exists with Role.ADMIN
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = Role.ADMIN
        profile.save()

        # Check password usability
        pwd_usable = user.has_usable_password()

        self.stdout.write(self.style.SUCCESS(
            f"\nAdmin setup verified for '{user.username}':\n"
            f"  - Superuser: {user.is_superuser}\n"
            f"  - Staff: {user.is_staff}\n"
            f"  - Active: {user.is_active}\n"
            f"  - Profile Role: {profile.role}\n"
            f"  - Has Usable Password: {pwd_usable}\n"
            "Ready for production login!"
        ))

