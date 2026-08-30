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
    """Self-contained by design: no CDN to go down, nothing loaded from outside.

    The distinction that matters is LOADS, not links: a script src or stylesheet
    pulls a third party into the page and can break it during judging; an <a href>
    to the repo is navigation the reader chooses. The first version of this test
    banned the substring https:// outright and flagged the attribution footer.
    """
    html = (ROOT / "static" / "index.html").read_text()
    for load in ('script src="http', "script src='http", 'link rel="stylesheet" href="http',
                 "url(http", "@import", "//cdn", "//unpkg", "//fonts."):
        assert load not in html, f"external load found: {load}"


def test_the_frozen_study_ships_with_the_image():
    """/evidence renders from static/study.json; a missing artifact 500s in production
    while every code path works. It must exist, parse, and carry its provenance."""
    import json
    study = json.loads((ROOT / "static" / "study.json").read_text())
    assert study["provenance"]["git_commit"] != "unknown"
    assert not study["provenance"]["git_commit"].endswith("-dirty"), \
        "the shipped study must be generated from committed code"
    for key in ("accuracy_by_arm", "refutation_by_template",
                "confounded_priors", "edge_recovery"):
        assert key in study


def test_the_evidence_page_is_self_contained(cloud_run_env):
    html = (ROOT / "static" / "evidence.html").read_text()
    for scheme in ("http://cdn", "https://cdn", "//unpkg", "//fonts.", "https://ajax"):
        assert scheme not in html
    from fastapi.testclient import TestClient
    c = TestClient(cloud_run_env.app)
    assert c.get("/evidence").status_code == 200
    assert c.get("/static/study.json").status_code == 200


def test_the_world_inspector_ships_and_is_self_contained(cloud_run_env):
    html = (ROOT / "static" / "world.html").read_text()
    for scheme in ("http://cdn", "https://cdn", "//unpkg", "//fonts.", "https://ajax"):
        assert scheme not in html
    from fastapi.testclient import TestClient
    c = TestClient(cloud_run_env.app)
    assert c.get("/world/7/inspect").status_code == 200
    truth = c.get("/world/7/truth").json()
    assert "narrative" in truth and "ground_truth" in truth


def test_the_agent_surface_route_stays_clean_with_compounds(cloud_run_env):
    """The compound flag widens the world, never the surface: still labels, affordances
    and the brief — no edges, no mechanisms, no hidden nodes."""
    from fastapi.testclient import TestClient
    c = TestClient(cloud_run_env.app)
    surface = c.get("/world/7?compound=true").json()
    assert set(surface) == {"world_id", "variables", "affordances", "brief"}
    import json as _json
    blob = _json.dumps(surface).lower()
    for word in ("edge", "mechanism", "exponential", "multiplicative", "hidden"):
        assert word not in blob


def test_the_inspector_is_discoverable_from_the_landing_page():
    """Shipping a page nobody can find is not delivering it: a judge starts at the
    root URL, not in the README."""
    assert "/world/7/inspect" in (ROOT / "static" / "index.html").read_text()
    assert "/world/7/inspect" in (ROOT / "static" / "evidence.html").read_text()


def test_every_page_carries_attribution_and_licence():
    """Author, repo and licence in the footer of each shipped page — the submission
    is judged from these pages, and they should say whose work it is and on what
    terms, without a trip to the repo."""
    for page in ("index.html", "evidence.html", "world.html"):
        html = (ROOT / "static" / page).read_text()
        assert "Marco Vanadia" in html, page
        assert "github.com/meta-agentic/meta-science" in html, page
        assert "GPL-3.0" in html, page
