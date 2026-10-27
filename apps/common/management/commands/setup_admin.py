"""
Management command to safely initialize or enable the jayraj admin account in production (Neon PostgreSQL).
Usage:
python manage.py setup_admin [--require-postgresql] [--reuse-local-hash]
"""
import sqlite3
import getpass
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile, Role
from django.conf import settings


class Command(BaseCommand):
    help = 'Safely runs migrations and creates/enables the jayraj admin account in PostgreSQL without touching demo data.'

    def add_arguments(self, parser):
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
        vendor = connection.vendor
        conf = connection.settings_dict
        db_name = conf.get('NAME', 'unknown')
        host = conf.get('HOST', 'localhost')

        if options['require_postgresql'] and vendor != 'postgresql':
            raise CommandError(
                f"Aborted: Target database is {vendor}, but --require-postgresql was specified. "
                "Set DATABASE_URL to your Neon connection string before running."
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

        local_hash = None
        if options['reuse_local_hash']:
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
            if local_hash and local_hash.startswith(('pbkdf2_sha256$', 'argon2$', 'bcrypt$')):
                user.password = local_hash
                user.save()
                self.stdout.write(self.style.SUCCESS("Created 'jayraj' with verified existing password hash."))
            else:
                self.stdout.write("Enter password for new admin 'jayraj':")
                pwd = getpass.getpass("Password: ")
                user.set_password(pwd)
                user.save()
                self.stdout.write(self.style.SUCCESS("Created 'jayraj' with new secure password."))
        else:
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            update_fields = ['is_superuser', 'is_staff', 'is_active']
            if local_hash and local_hash.startswith(('pbkdf2_sha256$', 'argon2$', 'bcrypt$')):
                user.password = local_hash
                update_fields.append('password')
            user.save(update_fields=update_fields)
            self.stdout.write(self.style.SUCCESS("Updated existing 'jayraj' to Superuser & Staff with verified password."))

        # Ensure UserProfile exists with Role.ADMIN
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = Role.ADMIN
        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f"\nAdmin setup verified for '{user.username}':\n"
            f"  - Superuser: {user.is_superuser}\n"
            f"  - Staff: {user.is_staff}\n"
            f"  - Active: {user.is_active}\n"
            f"  - Profile Role: {profile.role}\n"
            f"  - Has Usable Password: {user.has_usable_password()}\n"
            "Ready for production login!"
        ))

