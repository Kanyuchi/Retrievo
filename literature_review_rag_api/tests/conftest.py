"""Test environment isolation.

Runs BEFORE any test module imports literature_rag (pytest loads conftest
first), so env defaults here win over whatever shell/.env the developer has.
The app does not call load_dotenv, so process env is the only source.

Every value uses setdefault: CI or a developer can still point a specific
run elsewhere by exporting the variable explicitly.
"""
import os
import tempfile

_TEST_TMP = tempfile.mkdtemp(prefix="litrag_tests_")

# Never let tests touch a real database (production Supabase in .env!)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_TMP}/test.db")

# Keep all file artifacts inside the throwaway dir
os.environ.setdefault("INDICES_PATH", f"{_TEST_TMP}/indices")

# No real cloud/API dependencies in unit tests
os.environ.setdefault("AWS_ACCESS_KEY_ID", "")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "")

# Deterministic auth/security behavior
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("REQUIRE_HTTPS", "false")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")
os.environ.setdefault("AUTH_REQUIRE_VERIFIED", "false")
