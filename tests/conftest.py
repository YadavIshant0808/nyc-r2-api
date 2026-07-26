import os

import pytest


# Settings are constructed during module import. Keep tests independent from a
# developer's local .env and ensure no real service credentials are required.
os.environ["CLERK_ISSUER"] = "https://test.clerk.accounts.dev"
os.environ["CLERK_SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "postgresql://test:test@127.0.0.1:5432/test"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"


@pytest.fixture
def authenticated_app():
    from app.core.clerk_auth import get_current_user_profile
    from app.main import app

    app.dependency_overrides[get_current_user_profile] = lambda: {
        "id": "user_test",
        "email_addresses": [],
    }
    yield app
    app.dependency_overrides.clear()
