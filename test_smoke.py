import urllib.request
import urllib.parse
import http.cookiejar
import re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Fetch login page
res = opener.open('http://127.0.0.1:8000/login/')
html = res.read().decode('utf-8')
match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
csrf_token = match.group(1) if match else ''

print(f"1. Login Page: HTTP {res.getcode()}, CSRF token extracted: {bool(csrf_token)}")

# 2. Login as Manager (Marcus Brody)
login_data = urllib.parse.urlencode({
    'csrfmiddlewaretoken': csrf_token,
    'quick_user': 'manager'
}).encode('utf-8')

res = opener.open('http://127.0.0.1:8000/login/', data=login_data)
print(f"2. Logged In: Landed at {res.geturl()} (HTTP {res.getcode()})")

# 3. Test core routes
routes = [
    ('Overview Dashboard', 'http://127.0.0.1:8000/analytics/overview/'),
    ('My Tasks', 'http://127.0.0.1:8000/tasks/my-tasks/'),
    ('Projects List', 'http://127.0.0.1:8000/projects/'),
    ('Kanban Board', 'http://127.0.0.1:8000/tasks/board/'),
    ('Task List Table', 'http://127.0.0.1:8000/tasks/list/'),
    ('Calendar View', 'http://127.0.0.1:8000/tasks/calendar/'),
    ('Gantt Timeline', 'http://127.0.0.1:8000/tasks/gantt/'),
    ('Team Workload', 'http://127.0.0.1:8000/analytics/workload/'),
    ('Executive Reports', 'http://127.0.0.1:8000/analytics/reports/'),
    ('Notifications', 'http://127.0.0.1:8000/notifications/'),
    ('User Profile', 'http://127.0.0.1:8000/profile/'),
    ('Task Detail (Task 1)', 'http://127.0.0.1:8000/tasks/1/'),
    ('Project Detail (Project 1)', 'http://127.0.0.1:8000/projects/1/'),
    ('Export Tasks CSV', 'http://127.0.0.1:8000/analytics/export/csv/'),
]

all_passed = True
for name, url in routes:
    try:
        r = opener.open(url)
        content = r.read()
        print(f"  [PASS] {name:<26} -> HTTP {r.getcode()} ({len(content)} bytes)")
    except Exception as e:
        print(f"  [FAIL] {name:<26} -> ERROR: {e}")
        all_passed = False

if all_passed:
    print("\nALL 14 CORE ROUTES PASSED WITH HTTP 200 OK!")

    # Test Admin routes with Admin account
    cj_admin = http.cookiejar.CookieJar()
    opener_admin = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_admin))
    r = opener_admin.open('http://127.0.0.1:8000/login/')
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', r.read().decode('utf-8'))
    csrf = m.group(1) if m else ''
    opener_admin.open('http://127.0.0.1:8000/login/', data=urllib.parse.urlencode({'csrfmiddlewaretoken': csrf, 'quick_user': 'admin'}).encode('utf-8'))
    
    admin_routes = [
        ('Users & Role Administration', 'http://127.0.0.1:8000/admin/users/'),
        ('Workspace Settings & Seeder', 'http://127.0.0.1:8000/workspaces/settings/'),
    ]
    for aname, aurl in admin_routes:
        ar = opener_admin.open(aurl)
        print(f"  [PASS] {aname:<26} -> HTTP {ar.getcode()} ({len(ar.read())} bytes)")

    print("\nALL ADMIN ROUTES PASSED WITH HTTP 200 OK!")
