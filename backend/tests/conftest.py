import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:////tmp/fingraph_qris_test.sqlite3"
os.environ["PJP_SIMULATOR_SECRET"] = "test-only-pjp-secret-0123456789abcdef0123456789"
os.environ["PAYER_PSEUDONYM_KEY"] = "test-only-payer-key-0123456789abcdef0123456789"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-0123456789abcdef0123456789"
os.environ["NEO4J_URI"] = "bolt://127.0.0.1:1"
os.environ["NEO4J_CONNECTION_TIMEOUT_SECONDS"] = "0.2"
os.environ["NEO4J_MAX_RETRY_SECONDS"] = "0.2"
os.environ["SEED_GRAPH_SYNC"] = "false"
os.environ["ML_ARTIFACT_DIR"] = "/tmp/fingraph-qris-test-artifacts"
os.environ["ML_ARTIFACT_SIGNING_KEY"] = "test-only-artifact-signing-key-0123456789abcdef"
# Keep integration fixtures deterministic; graph tests enable GNN explicitly.
os.environ["QRIS_GNN_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, engine
import app.models  # noqa: F401
from app.db.seeds.seed import run_seed
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    run_seed()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    return TestClient(app)


def login_headers(client: TestClient, email: str):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def merchant_headers(client):
    return login_headers(client, "merchant@fingraph.id")


@pytest.fixture()
def second_merchant_headers(client):
    return login_headers(client, "batik@fingraph.id")


@pytest.fixture()
def analyst_headers(client):
    return login_headers(client, "analyst@fingraph.id")


@pytest.fixture()
def admin_headers(client):
    return login_headers(client, "admin@fingraph.id")
