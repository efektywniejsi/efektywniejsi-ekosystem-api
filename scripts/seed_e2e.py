"""
E2E Test Data Seeder

Seeds the E2E database via HTTP API calls to localhost:8001.
Idempotent: safe to run multiple times.

Usage:
    python scripts/seed_e2e.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = os.environ.get("E2E_API_BASE", "http://localhost:8001/api/v1")

ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "e2e-admin@test.pl")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "E2eAdmin123!")
ADMIN_NAME = "E2E Admin"

USER_EMAIL = os.environ.get("E2E_USER_EMAIL", "e2e-user@test.pl")
USER_PASSWORD = os.environ.get("E2E_USER_PASSWORD", "E2eUser123!")
USER_NAME = "E2E Paid User"

# First, use the built-in admin to bootstrap
BOOTSTRAP_ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@efektywniejsi.pl")
BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not BOOTSTRAP_ADMIN_PASSWORD:
    print("ERROR: ADMIN_PASSWORD env var is required.")
    print("  Set it to the password used when seeding the admin user.")
    sys.exit(1)


def api_request(endpoint, method="GET", data=None, cookies=None):
    url = f"{API_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if cookies:
        headers["Cookie"] = cookies

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        response = urllib.request.urlopen(req)
        cookie_header = response.headers.get("Set-Cookie", "")
        response_body = response.read().decode("utf-8")
        if response_body:
            return json.loads(response_body), response.status, cookie_header
        return None, response.status, cookie_header
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
        except json.JSONDecodeError:
            error_data = {"detail": error_body}
        return error_data, e.code, ""


def extract_cookies(set_cookie_header, existing_cookies=""):
    """Extract cookie key=value pairs from Set-Cookie headers."""
    cookies = {}

    # Parse existing cookies
    if existing_cookies:
        for part in existing_cookies.split(";"):
            part = part.strip()
            if "=" in part and not part.lower().startswith(
                ("path", "domain", "expires", "max-age", "samesite", "httponly", "secure")
            ):
                key, val = part.split("=", 1)
                cookies[key.strip()] = val.strip()

    # Parse new Set-Cookie headers
    if set_cookie_header:
        for cookie_str in set_cookie_header.split(","):
            parts = cookie_str.strip().split(";")
            if parts and "=" in parts[0]:
                key, val = parts[0].strip().split("=", 1)
                cookies[key.strip()] = val.strip()

    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def login(email, password):
    """Login and return cookies string."""
    data, status, cookie_header = api_request(
        "/auth/login", method="POST", data={"email": email, "password": password}
    )
    if status not in (200, 201):
        print(f"  FAIL: Login failed for {email}: {data}")
        return None
    cookies = extract_cookies(cookie_header)
    print(f"  OK: Logged in as {email}")
    return cookies


def create_user_if_not_exists(cookies, email, name, password, role):
    """Create user via admin endpoint. Returns True if created or already exists."""
    data, status, _ = api_request(
        "/admin/users",
        method="POST",
        data={"email": email, "name": name, "password": password, "role": role},
        cookies=cookies,
    )
    if status == 201:
        print(f"  OK: Created user {email} (role={role})")
        return True
    if status == 409:
        print(f"  SKIP: User {email} already exists")
        return True
    print(f"  FAIL: Could not create user {email}: {data}")
    return False


def get_courses(cookies):
    """Get all courses (admin sees all)."""
    data, status, _ = api_request("/courses/all", cookies=cookies)
    if status == 200:
        return data
    return []


def create_course(
    cookies,
    slug,
    title,
    description,
    is_published=True,
    difficulty="beginner",
    content_type="course",
):
    """Create a course if it doesn't exist by slug."""
    existing = get_courses(cookies)
    for course in existing:
        if course.get("slug") == slug:
            print(f"  SKIP: Course '{slug}' already exists (id={course['id']})")
            return course

    data, status, _ = api_request(
        "/courses",
        method="POST",
        data={
            "slug": slug,
            "title": title,
            "description": description,
            "difficulty": difficulty,
            "estimated_hours": 2,
            "is_published": is_published,
            "category": "e2e-test",
            "sort_order": 0,
            "content_type": content_type,
        },
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Created course '{slug}' (id={data['id']})")
        return data
    print(f"  FAIL: Could not create course '{slug}': {data}")
    return None


def create_module(cookies, course_id, title, sort_order=0):
    """Create a module in a course."""
    data, status, _ = api_request(
        f"/courses/{course_id}/modules",
        method="POST",
        data={"title": title, "sort_order": sort_order},
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"    OK: Created module '{title}'")
        return data
    print(f"    FAIL: Could not create module '{title}': {data}")
    return None


def create_lesson(cookies, module_id, title, sort_order=0):
    """Create a lesson in a module."""
    data, status, _ = api_request(
        f"/modules/{module_id}/lessons",
        method="POST",
        data={
            "title": title,
            "mux_playback_id": None,
            "mux_asset_id": None,
            "duration_seconds": 300,
            "is_preview": False,
            "status": "available",
            "sort_order": sort_order,
        },
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"      OK: Created lesson '{title}'")
        return data
    print(f"      FAIL: Could not create lesson '{title}': {data}")
    return None


def enroll_user(cookies, course_id, user_email):
    """Enroll a user in a course via admin endpoint."""
    data, status, _ = api_request(
        f"/admin/courses/{course_id}/enrollments",
        method="POST",
        data={"email": user_email},
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Enrolled {user_email} in course {course_id}")
        return data
    if status == 409:
        print(f"  SKIP: {user_email} already enrolled in course {course_id}")
        return True
    print(f"  FAIL: Could not enroll {user_email}: {data}")
    return None


def create_community_thread(cookies, title, content, category="general"):
    """Create a community thread."""
    data, status, _ = api_request(
        "/community/threads",
        method="POST",
        data={
            "title": title,
            "content": content,
            "category": category,
        },
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Created thread '{title}' (id={data['id']})")
        return data
    print(f"  FAIL: Could not create thread '{title}': {data}")
    return None


def add_thread_reply(cookies, thread_id, content):
    """Add a reply to a community thread."""
    data, status, _ = api_request(
        f"/community/threads/{thread_id}/replies",
        method="POST",
        data={"content": content},
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Replied to thread {thread_id}")
        return data
    print(f"  FAIL: Could not reply to thread {thread_id}: {data}")
    return None


def resolve_thread(cookies, thread_id):
    """Mark a community thread as resolved."""
    data, status, _ = api_request(
        f"/community/threads/{thread_id}/resolve",
        method="PATCH",
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Resolved thread {thread_id}")
        return data
    print(f"  FAIL: Could not resolve thread {thread_id}: {data}")
    return None


def pin_thread(cookies, thread_id):
    """Pin a community thread (admin only)."""
    data, status, _ = api_request(
        f"/admin/community/threads/{thread_id}/pin",
        method="PATCH",
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Pinned thread {thread_id}")
        return data
    print(f"  FAIL: Could not pin thread {thread_id}: {data}")
    return None


def create_achievement(cookies, slug, name, description, points, criteria_type="manual"):
    """Create a gamification achievement if it doesn't exist."""
    # Check existing achievements
    data, status, _ = api_request("/admin/gamification/achievements", cookies=cookies)
    if status == 200:
        existing = data if isinstance(data, list) else data.get("achievements", [])
        for ach in existing:
            if ach.get("slug") == slug:
                print(f"  SKIP: Achievement '{slug}' already exists (id={ach['id']})")
                return ach

    data, status, _ = api_request(
        "/admin/gamification/achievements",
        method="POST",
        data={
            "slug": slug,
            "name": name,
            "description": description,
            "points": points,
            "criteria_type": criteria_type,
        },
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Created achievement '{slug}' (id={data.get('id', 'unknown')})")
        return data
    print(f"  FAIL: Could not create achievement '{slug}': {data}")
    return None


def get_bundles(cookies):
    """Get all bundles."""
    data, status, _ = api_request("/bundles", cookies=cookies)
    if status == 200:
        return data
    return []


def create_bundle(cookies, slug, name, package_ids):
    """Create a bundle if it doesn't exist by slug."""
    existing = get_bundles(cookies)
    for bundle in existing:
        if bundle.get("slug") == slug:
            print(f"  SKIP: Bundle '{slug}' already exists (id={bundle['id']})")
            return bundle

    data, status, _ = api_request(
        "/bundles",
        method="POST",
        data={
            "slug": slug,
            "name": name,
            "description": f"Bundle testowy E2E: {name}",
            "category": "e2e-test",
            "price": 19900,
            "difficulty": "beginner",
            "package_ids": package_ids,
        },
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Created bundle '{slug}' (id={data.get('id', 'unknown')})")
        return data
    print(f"  FAIL: Could not create bundle '{slug}': {data}")
    return None


def get_packages(cookies):
    """Get all packages."""
    data, status, _ = api_request("/packages/all", cookies=cookies)
    if status == 200:
        return data
    return []


def create_package(cookies, slug, title, description):
    """Create a package if it doesn't exist by slug."""
    existing = get_packages(cookies)
    for pkg in existing:
        if pkg.get("slug") == slug:
            print(f"  SKIP: Package '{slug}' already exists")
            return pkg

    data, status, _ = api_request(
        "/packages",
        method="POST",
        data={
            "slug": slug,
            "title": title,
            "description": description,
            "price": 99900,
            "category": "e2e-test",
            "difficulty": "beginner",
        },
        cookies=cookies,
    )
    if status in (200, 201):
        print(f"  OK: Created package '{slug}'")
        return data
    print(f"  FAIL: Could not create package '{slug}': {data}")
    return None


def main():
    print("=" * 60)
    print("E2E Test Data Seeder")
    print("=" * 60)

    # Step 1: Login as bootstrap admin
    print("\n[1/8] Logging in as bootstrap admin...")
    admin_cookies = login(BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD)
    if not admin_cookies:
        print("FATAL: Cannot login as bootstrap admin. Is the API running?")
        sys.exit(1)

    # Step 2: Create E2E test users
    print("\n[2/8] Creating E2E test users...")
    create_user_if_not_exists(admin_cookies, ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD, "admin")
    create_user_if_not_exists(admin_cookies, USER_EMAIL, USER_NAME, USER_PASSWORD, "paid")

    # Re-login as E2E admin for subsequent operations
    print("\n  Re-logging in as E2E admin...")
    e2e_admin_cookies = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not e2e_admin_cookies:
        print("FATAL: Cannot login as E2E admin")
        sys.exit(1)

    # Step 3: Create courses with modules and lessons
    print("\n[3/8] Creating courses...")
    course1 = create_course(
        e2e_admin_cookies,
        slug="e2e-kurs-1",
        title="E2E Kurs Pierwszy",
        description="Pierwszy kurs testowy E2E z modułami i lekcjami.",
        is_published=True,
    )
    create_course(
        e2e_admin_cookies,
        slug="e2e-kurs-2",
        title="E2E Kurs Drugi",
        description="Drugi kurs testowy E2E.",
        is_published=True,
    )
    create_course(
        e2e_admin_cookies,
        slug="e2e-kurs-ukryty",
        title="E2E Kurs Ukryty",
        description="Niepublikowany kurs testowy E2E.",
        is_published=False,
    )

    # Add modules and lessons to course1
    if course1:
        print("\n  Adding modules/lessons to e2e-kurs-1...")
        # Check if course already has modules
        existing_detail, status, _ = api_request("/courses/e2e-kurs-1", cookies=e2e_admin_cookies)
        if status == 200 and existing_detail.get("modules") and len(existing_detail["modules"]) > 0:
            print("    SKIP: Course already has modules")
        else:
            mod1 = create_module(
                e2e_admin_cookies, course1["id"], "Moduł 1: Wprowadzenie", sort_order=0
            )
            if mod1:
                create_lesson(e2e_admin_cookies, mod1["id"], "Lekcja 1.1: Powitanie", sort_order=0)
                create_lesson(e2e_admin_cookies, mod1["id"], "Lekcja 1.2: Podstawy", sort_order=1)
            mod2 = create_module(
                e2e_admin_cookies, course1["id"], "Moduł 2: Zaawansowane", sort_order=1
            )
            if mod2:
                create_lesson(e2e_admin_cookies, mod2["id"], "Lekcja 2.1: Techniki", sort_order=0)

    # Step 4: Create packages
    print("\n[4/8] Creating packages...")
    pkg1 = create_package(
        e2e_admin_cookies,
        slug="e2e-pakiet-1",
        title="E2E Pakiet Podstawowy",
        description="Podstawowy pakiet testowy E2E.",
    )
    pkg2 = create_package(
        e2e_admin_cookies,
        slug="e2e-pakiet-2",
        title="E2E Pakiet Premium",
        description="Premiumowy pakiet testowy E2E.",
    )

    # Step 5: Create bundles (required by sales window form)
    print("\n[5/8] Creating bundles...")
    pkg_ids = []
    if pkg1 and pkg1.get("id"):
        pkg_ids.append(str(pkg1["id"]))
    if pkg2 and pkg2.get("id"):
        pkg_ids.append(str(pkg2["id"]))

    if pkg_ids:
        create_bundle(
            e2e_admin_cookies,
            slug="e2e-bundle-1",
            name="E2E Bundle Podstawowy",
            package_ids=pkg_ids[:1],
        )
        create_bundle(
            e2e_admin_cookies,
            slug="e2e-bundle-2",
            name="E2E Bundle Premium",
            package_ids=pkg_ids,
        )
    else:
        print("  SKIP: No packages available for bundle creation")

    # Step 5b: Create gamification achievements
    print("\n[5b/8] Creating gamification achievements...")
    create_achievement(
        e2e_admin_cookies,
        slug="e2e-first-lesson",
        name="Pierwsza lekcja",
        description="Ukończ swoją pierwszą lekcję.",
        points=10,
        criteria_type="lesson_complete",
    )
    create_achievement(
        e2e_admin_cookies,
        slug="e2e-course-complete",
        name="Kurs ukończony",
        description="Ukończ cały kurs od początku do końca.",
        points=100,
        criteria_type="course_complete",
    )
    create_achievement(
        e2e_admin_cookies,
        slug="e2e-streak-7",
        name="Tydzień serii",
        description="Utrzymaj serię aktywności przez 7 dni.",
        points=50,
        criteria_type="streak",
    )

    # Step 6: Create enrollment
    print("\n[6/8] Creating enrollments...")
    if course1:
        enroll_user(e2e_admin_cookies, course1["id"], USER_EMAIL)

    # Step 6: Create community threads (as paid user)
    print("\n[7/8] Creating community threads...")
    user_cookies = login(USER_EMAIL, USER_PASSWORD)
    if user_cookies:
        # Check existing threads first
        existing_threads, threads_status, _ = api_request(
            "/community/threads", cookies=user_cookies
        )
        e2e_threads = []
        if threads_status == 200 and existing_threads.get("threads"):
            e2e_threads = [
                t for t in existing_threads["threads"] if t.get("title", "").startswith("[E2E]")
            ]

        if len(e2e_threads) >= 2:
            print("  SKIP: E2E threads already exist")
        else:
            create_community_thread(
                user_cookies,
                title="[E2E] Problem z dostępem do kursu",
                content="Nie mogę uzyskać dostępu do materiałów kursu. Proszę o pomoc.",
                category="pomoc",
            )

            # Resolved thread with reply
            resolved_thread = create_community_thread(
                user_cookies,
                title="[E2E] Pytanie o płatności",
                content="Mam pytanie dotyczące metod płatności.",
                category="ogolne",
            )

            if resolved_thread:
                add_thread_reply(
                    e2e_admin_cookies,
                    resolved_thread["id"],
                    "Dziękujemy za pytanie. Akceptujemy karty Visa, Mastercard oraz PayU.",
                )
                resolve_thread(user_cookies, resolved_thread["id"])
                pin_thread(e2e_admin_cookies, resolved_thread["id"])

    # Step 7: Summary
    print("\n[8/8] Seed complete!")
    print("=" * 60)
    print(f"  Admin:  {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  User:   {USER_EMAIL} / {USER_PASSWORD}")
    print("=" * 60)


if __name__ == "__main__":
    main()
