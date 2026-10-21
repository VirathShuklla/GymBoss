Historical one-off suites from earlier iterations. They assume the original preview layout (/app paths and shared demo data), so they are excluded from the default run (pytest.ini: norecursedirs = archive).
The maintained suites live one level up and resolve paths via tests/paths.py (override with GYMBOSS_ROOT, GYMBOSS_BACKEND_ENV, GYMBOSS_FRONTEND_ENV, GYMBOSS_TEST_CREDENTIALS).
