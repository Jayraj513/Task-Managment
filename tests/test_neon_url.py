import unittest
from apps.common.utils import sanitize_postgres_url, validate_postgres_url


class NeonURLValidationTests(unittest.TestCase):
    def test_standard_neon_url(self):
        url = 'postgresql://testuser:mockpass@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
        s = sanitize_postgres_url(url)
        valid, err, details = validate_postgres_url(s)
        self.assertTrue(valid)
        self.assertTrue(details['is_neon'])
        self.assertEqual(details['scheme'], 'postgresql')
        self.assertEqual(details['database'], 'neondb')
        self.assertEqual(details['query'], 'sslmode=require&channel_binding=require')
        self.assertTrue(details['has_password'])

    def test_postgres_scheme_variation(self):
        url = 'postgres://testuser:mockpass@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require'
        s = sanitize_postgres_url(url)
        valid, err, details = validate_postgres_url(s)
        self.assertTrue(valid)
        self.assertTrue(details['is_neon'])
        self.assertEqual(details['scheme'], 'postgres')

    def test_surrounding_quotes_and_brackets(self):
        cases = [
            '"postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require"',
            "'postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require'",
            '<postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require>',
            '  postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require  \n',
        ]
        for c in cases:
            s = sanitize_postgres_url(c)
            valid, err, details = validate_postgres_url(s)
            self.assertTrue(valid, f"Failed on case: {c}")
            self.assertTrue(details['is_neon'])

    def test_inadvertent_shell_prefixes(self):
        cases = [
            'DATABASE_URL="postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require"',
            'DATABASE_URL=postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require',
            'export DATABASE_URL="postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require"',
            '$env:DATABASE_URL="postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require"',
            'psql "postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require"',
            "psql 'postgresql://testuser:mockpass@ep-xyz.neon.tech/neondb?sslmode=require'",
        ]
        for c in cases:
            s = sanitize_postgres_url(c)
            valid, err, details = validate_postgres_url(s)
            self.assertTrue(valid, f"Failed on prefix case: {c}")
            self.assertTrue(details['is_neon'])

    def test_non_neon_postgres_url(self):
        url = 'postgresql://testuser:mockpass@postgres-server.internal:5432/production_db'
        s = sanitize_postgres_url(url)
        valid, err, details = validate_postgres_url(s)
        self.assertTrue(valid)
        self.assertFalse(details['is_neon'])

    def test_invalid_urls(self):
        invalid_cases = [
            '',
            '   ',
            'mysql://testuser:mockpass@localhost/mydb',
            'sqlite:///tmp/db.sqlite3',
            'not_a_valid_url',
            'http://neon.tech',
            'postgresql://',
        ]
        for c in invalid_cases:
            s = sanitize_postgres_url(c)
            valid, err, details = validate_postgres_url(s)
            self.assertFalse(valid, f"Expected invalid for: {c}")

