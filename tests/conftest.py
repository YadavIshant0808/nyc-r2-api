import os

import pytest


# Construct Settings without relying on a developer's local credentials.
os.environ["CLERK_ISSUER"] = "https://test.clerk.accounts.dev"
os.environ["CLERK_SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "postgresql://test:test@127.0.0.1:5432/test"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"


@pytest.fixture
def authenticated_app():
    from app.core.clerk_auth import get_current_user_claims
    from app.main import app

    app.dependency_overrides[get_current_user_claims] = lambda: {
        "sub": "user_test",
    }
    yield app
    app.dependency_overrides.clear()
