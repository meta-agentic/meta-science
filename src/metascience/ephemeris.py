"""Ephemeris worlds: orbits propagated by the isohub flight-dynamics service.

The historical dataset (kepler.py) has two hard limits: Mars is the most memorised
data in science, and nobody can act on it. A numerical propagator lifts both. It can
fly a planet that has never existed — real Keplerian physics, no textbook entry, so
recall is impossible — and it can fly one under a force model where the textbook law
is *wrong* (an oblate primary precesses the ellipse), so recall is punished.

The service is isohub's `space-flight-dynamics` (Orekit behind a REST contract,
`contracts/sfd/openapi.yaml`). One recipe works for heliocentric arcs: backend OREKIT
with every force-model term explicitly zeroed — the service's default force model is
tuned for Earth orbits and its integrator underflows its minimum step around the Sun.
Perturbed worlds turn individual terms back on.

Nothing here calls the network during tests. Arcs are recorded once into
tests/fixtures/ with the full request beside the response — provenance, and replay.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path

SFD_URL = os.environ.get("SFD_URL", "http://localhost:8080")
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

AU_M = 1.495978707e11

TWO_BODY = {"atmosphericDrag": False, "moonGravity": False, "sunGravity": False,
            "solarRadiationPressure": False, "gravityDegree": 0, "gravityOrder": 0}

# An oblate primary: degree-8 gravity field. Around Earth this precesses the line of
# apsides by degrees per day — the world where a closed conic is the wrong answer.
OBLATE = {**TWO_BODY, "gravityDegree": 8, "gravityOrder": 8}


def _quantity(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def fictional_planet(seed: int) -> dict:
    """Deterministic Keplerian elements for a planet that has never existed.

    Plain arithmetic on the seed, no RNG: the same seed is the same planet in every
    process, which is the same determinism bargain the generated worlds make.
    Inclination is zero by construction — the first-law loop lives in the plane.
    """
    a_au = 0.45 + (seed * 137) % 211 / 100.0          # 0.45 .. 2.55 AU
    ecc = 0.04 + (seed * 89) % 23 / 100.0             # 0.04 .. 0.26
    argp = (seed * 61) % 360
    anomaly = (seed * 29) % 360
    return {
        "centralBody": "SUN",
        "frame": "ICRF",
        "epoch": "2026-01-01T00:00:00Z",
        "semiMajorAxis": _quantity(round(a_au * AU_M / 1000.0, 1), "km"),
        "eccentricity": round(ecc, 4),
        "inclination": _quantity(0.0, "°"),
        "raan": _quantity(0.0, "°"),
        "argumentOfPerigee": _quantity(float(argp), "°"),
        "trueAnomaly": _quantity(float(anomaly), "°"),
    }


def low_orbit(seed: int) -> dict:
    """An equatorial orbit close to an oblate Earth: the law-breaking regime."""
    return {
        "centralBody": "EARTH",
        "frame": "EME2000",
        "epoch": "2026-01-01T00:00:00Z",
        "semiMajorAxis": _quantity(6900.0 + (seed * 37) % 400, "km"),
        "eccentricity": 0.05 + (seed * 13) % 5 / 100.0,
        "inclination": _quantity(0.0, "°"),
        "raan": _quantity(0.0, "°"),
        "argumentOfPerigee": _quantity(float((seed * 61) % 360), "°"),
        "trueAnomaly": _quantity(0.0, "°"),
    }


def _request(orbit: dict, duration: str, step: str, forces: dict) -> dict:
    return {
        "spacecraftId": "metascience",
        "startEpoch": orbit["epoch"],
        "duration": duration,
        "stepSize": step,
        "backend": "OREKIT",
        "orbit": orbit,
        "forceModel": forces,
    }


def _propagate_live(request: dict) -> dict:
    req = urllib.request.Request(
        f"{SFD_URL}/api/v1/trajectories/propagate",
        data=json.dumps(request).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    if not body.get("states"):
        raise RuntimeError(f"flight-dynamics returned no states: {body}")
    return body


def arc(name: str, orbit: dict, duration: str, step: str,
        forces: dict) -> list[tuple[str, float, float]]:
    """(epoch, theta_deg, r) samples of one propagated arc, fixture-first.

    r is in AU for heliocentric arcs and in Earth radii for Earth-centred ones —
    both dimensionless enough to keep the law machinery unit-blind.
    """
    path = FIXTURES / f"ephemeris-{name}.json"
    if path.exists():
        record = json.loads(path.read_text())
        if record["request"] != _request(orbit, duration, step, forces):
            raise RuntimeError(f"fixture {name} was recorded for a different request")
    else:
        request = _request(orbit, duration, step, forces)
        record = {"request": request, "response": _propagate_live(request)}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1))

    scale = AU_M if orbit["centralBody"] == "SUN" else 6.378137e6
    out = []
    for s in record["response"]["states"]:
        x, y = s["x"]["value"], s["y"]["value"]
        r = math.hypot(x, y) / scale
        out.append((s["epoch"], math.degrees(math.atan2(y, x)) % 360.0, r))
    return out


# ------------------------------------------------------------------- the three worlds

def unmemorisable(seed: int = 7) -> list[tuple[float, float]]:
    """A planet with no textbook: pure two-body, one and a half years, in the plane."""
    pts = arc(f"planet-{seed}", fictional_planet(seed), "P548D", "P4D", TWO_BODY)
    return [(t, r) for _, t, r in pts]


def law_breaking(seed: int = 7) -> list[tuple[float, float]]:
    """The same question where the textbook answer is wrong: an oblate primary
    rotates the ellipse under the data. A closed r(theta) does not exist here."""
    pts = arc(f"oblate-{seed}", low_orbit(seed), "P10D", "PT2H", OBLATE)
    return [(t, r) for _, t, r in pts]


def control_orbit(seed: int = 7) -> list[tuple[float, float]]:
    """The identical Earth orbit under two-body forces: the paired control arm,
    so the law-breaking comparison changes exactly one thing."""
    pts = arc(f"control-{seed}", low_orbit(seed), "P10D", "PT2H", TWO_BODY)
    return [(t, r) for _, t, r in pts]
