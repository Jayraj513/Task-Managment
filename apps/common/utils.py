"""
Common URL sanitization and secure input utilities for OGFLOW.
"""
import sys
import ctypes
import urllib.parse


def get_clipboard_text():
    """Reads plain text from Windows clipboard if available."""
    if sys.platform != 'win32':
        return None
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return None
        try:
            CF_UNICODETEXT = 13
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return None
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                return ctypes.c_wchar_p(ptr).value
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    except Exception:
        return None


def secure_read_url(prompt: str = "Paste or enter Neon DATABASE_URL: ") -> str:
    """
    Securely reads input without echoing to console.
    On Windows conhost/PowerShell, supports Ctrl+V by reading from the clipboard,
    and supports right-click pasting without logging the secret to shell history.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()

    if sys.platform == 'win32' and sys.stdin.isatty():
        import msvcrt
        chars = []
        while True:
            ch = msvcrt.getwch()
            if ch in ('\r', '\n'):
                sys.stdout.write('\n')
                sys.stdout.flush()
                break
            elif ch == '\003':  # Ctrl+C
                sys.stdout.write('\n')
                sys.stdout.flush()
                raise KeyboardInterrupt
            elif ch == '\b':  # Backspace
                if chars:
                    chars.pop()
            elif ch == '\x16':  # Ctrl+V on Windows console
                clip = get_clipboard_text()
                if clip:
                    clip = clip.rstrip('\r\n')
                    chars.extend(list(clip))
            else:
                chars.append(ch)
        return "".join(chars)
    else:
        import getpass
        return getpass.getpass("")


def sanitize_postgres_url(raw: str) -> str:
    """
    Strips accidental surrounding quotes, brackets, whitespace,
    and shell assignment prefixes without altering the underlying URI.
    """
    if not raw:
        return ''
    cleaned = raw.strip().strip('\r\n\t \ufeff')

    prefixes_to_strip = [
        'export DATABASE_URL=',
        '$env:DATABASE_URL=',
        'DATABASE_URL=',
        'DATABASE_URL:',
        'psql ',
    ]
    for prefix in prefixes_to_strip:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    cleaned = cleaned.strip('\'"`<> ')

    # Nested psql '...'
    if cleaned.startswith('psql '):
        cleaned = cleaned[5:].strip().strip('\'"`<> ')

    return cleaned


def validate_postgres_url(cleaned: str) -> tuple[bool, str, dict]:
    """
    Validates that the string has a valid PostgreSQL URI structure.
    Does NOT transform an unrelated string into a valid URL.
    """
    if not cleaned:
        return False, "Connection string cannot be empty.", {}

    try:
        parsed = urllib.parse.urlparse(cleaned)
    except Exception as e:
        return False, f"Malformed URI: {e}", {}

    if parsed.scheme not in ('postgresql', 'postgres'):
        return False, (
            f"Invalid scheme '{parsed.scheme}://'. "
            "Connection string must begin with 'postgresql://' or 'postgres://'."
        ), {}

    if not parsed.hostname:
        return False, "Connection string is missing a valid server/hostname.", {}

    is_neon = 'neon.tech' in parsed.hostname.lower()

    raw_host = parsed.hostname
    if len(raw_host) > 22:
        masked_host = raw_host[:6] + "..." + raw_host[-15:]
    else:
        masked_host = raw_host

    db_name = parsed.path.lstrip('/') or 'default'
    username = parsed.username or 'unspecified'

    details = {
        'scheme': parsed.scheme,
        'host': parsed.hostname,
        'masked_host': masked_host,
        'port': parsed.port or 5432,
        'database': db_name,
        'username': username,
        'has_password': bool(parsed.password),
        'query': parsed.query,
        'is_neon': is_neon,
    }
    return True, "", details

