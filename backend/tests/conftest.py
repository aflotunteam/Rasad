"""Test muhiti: alohida SQLite bazasi, sessiya boshida bir marta seed qilinadi."""

import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="rasad-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
# Testlar hech qachon haqiqiy Anthropic API ni chaqirmasligi kerak: .env dagi kalit e'tiborsiz qoldiriladi.
os.environ["ANTHROPIC_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def seeded():
    from scripts import seed

    seed.main()
    return True


@pytest.fixture(scope="session")
def client(seeded):
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def db(seeded):
    from app.core.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['token']}"}


@pytest.fixture(scope="session")
def admin_h(client):
    return _login(client, "admin", "Admin123!")


@pytest.fixture(scope="session")
def analyst_h(client):
    return _login(client, "tahlilchi", "Tahlil123!")


@pytest.fixture(scope="session")
def manager_h(client):
    return _login(client, "rahbar", "Rahbar123!")


@pytest.fixture(scope="session")
def auditor_h(client):
    return _login(client, "auditor", "Audit123!")
