"""
Local smoke test runner for Workline / OGFLOW.
Run manually against a running local development server:
python test_smoke.py
"""
import urllib.request
import urllib.parse
import http.cookiejar
import re

def run_smoke_test(base_url='http://127.0.0.1:8000', username='jayraj', password='WorklineDemo2026!'):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 1. Fetch login page
    res = opener.open(f'{base_url}/login/')
    html = res.read().decode('utf-8')
    match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
    csrf_token = match.group(1) if match else ''

    print(f"1. Login Page: HTTP {res.getcode()}, CSRF token extracted: {bool(csrf_token)}")

    # 2. Login as Admin/User
    login_data = urllib.parse.urlencode({
        'csrfmiddlewaretoken': csrf_token,
        'username': username,
        'password': password
    }).encode('utf-8')

    res = opener.open(f'{base_url}/login/', data=login_data)
    print(f"2. Logged In: Landed at {res.geturl()} (HTTP {res.getcode()})")

    # 3. Test core routes
    routes = [
        ('Overview Dashboard', f'{base_url}/analytics/overview/'),
        ('My Tasks', f'{base_url}/tasks/my-tasks/'),
        ('Projects List', f'{base_url}/projects/'),
        ('Kanban Board', f'{base_url}/tasks/board/'),
        ('Task List Table', f'{base_url}/tasks/list/'),
        ('Calendar View', f'{base_url}/tasks/calendar/'),
        ('Gantt Timeline', f'{base_url}/tasks/gantt/'),
        ('Team Workload', f'{base_url}/analytics/workload/'),
        ('Executive Reports', f'{base_url}/analytics/reports/'),
        ('Notifications', f'{base_url}/notifications/'),
        ('User Profile', f'{base_url}/profile/'),
        ('Users & Role Administration', f'{base_url}/admin/users/'),
    ]

    all_passed = True
    for name, url in routes:
        try:
            r = opener.open(url)
            content = r.read()
            print(f"  [PASS] {name:<28} -> HTTP {r.getcode()} ({len(content)} bytes)")
        except Exception as e:
            print(f"  [FAIL] {name:<28} -> ERROR: {e}")
            all_passed = False

    if all_passed:
        print("\nALL CORE ROUTES PASSED WITH HTTP 200 OK!")
    return all_passed

if __name__ == '__main__':
    run_smoke_test()
