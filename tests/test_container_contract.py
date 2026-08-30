"""What has to hold for the Cloud Run image to work.

These are the failures that deploy silently and only surface as a 500 in production:
the app needing a file the build context excludes, the ledger quietly staying on the
filesystem inside a container, or a route that only works because a local .env happened
to be readable.

No Docker required — the contract is checkable directly.
"""
import importlib
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


@pytest.fixture
def cloud_run_env(monkeypatch):
    """Reproduce the container: K_SERVICE set, and no .env to fall back on."""
    monkeypatch.setenv("K_SERVICE", "metascience")
    monkeypatch.setenv("GEMINI_PROJECT", "meta-science")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import app
    importlib.reload(app)
    return app


def test_the_build_context_excludes_secrets_and_local_state():
    ignored = (ROOT / ".dockerignore").read_text().split()
    for path in (".env", ".env.*", "runs/", ".git/"):
        assert path in ignored, f"{path} would be baked into the image"


def test_the_image_only_needs_what_it_copies():
    """COPY brings src/ and app.py. Anything else imported at module scope breaks."""
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "COPY src/" in dockerfile and "COPY app.py" in dockerfile
    for needed in ("fastapi", "uvicorn", "google-genai", "google-cloud-firestore"):
        assert needed in (ROOT / "requirements.txt").read_text()


def test_the_container_honours_the_port_contract():
    """Cloud Run supplies PORT; a hardcoded port fails health checks."""
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "${PORT}" in dockerfile, "must bind the injected PORT"
    assert "--host 0.0.0.0" in dockerfile, "binding localhost is unreachable in a container"


def test_k_service_selects_the_firestore_ledger(cloud_run_env):
    """Silently staying on the filesystem would lose every receipt on scale-to-zero."""
    assert type(cloud_run_env._ledger()).__name__ == "FirestoreLedger"


def test_the_offline_routes_work_without_an_api_key(cloud_run_env):
    """A judge hitting /world or /discover must not need our credentials."""
    from fastapi.testclient import TestClient
    c = TestClient(cloud_run_env.app)
    # /health, not /healthz: Google's frontend intercepts the latter and returns its own
    # 404 before the request reaches the container. Caught only against the deployment.
    assert c.get("/health").status_code == 200
    assert c.get("/world/7").json()["variables"]
    body = c.get("/discover/7").json()
    assert body["refutation_count"] >= 1


def test_the_image_copies_the_static_page():
    """The index route reads static/index.html at request time; if COPY misses it the
    landing page 500s in production while every local test passes."""
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "COPY static/" in dockerfile
    assert (ROOT / "static" / "index.html").exists()


def test_the_landing_page_makes_no_external_requests(cloud_run_env):
    """Self-contained by design: no CDN to go down, nothing leaving the viewer's browser."""
    html = (ROOT / "static" / "index.html").read_text()
    for scheme in ("http://", "https://", "//cdn", "//unpkg", "//fonts."):
        assert scheme not in html, f"external reference found: {scheme}"
