"""Level 3, first slice: law induction from a real, purely observational dataset.

The dataset is the one that started modern astronomy. Five pairs of observations of
Mars — collected by Tycho Brahe, triangulated by the method Kepler describes in
Astronomia Nova (1609): Mars returns to the same point of its orbit once per Martian
year, so two sightings from two different Earth positions locate it in the plane.

The numbers are transcribed verbatim, to the arc-minute, from the Sky & Telescope
laboratory exercise "The Orbit of Mars" (solution sheet, Phys 102, Fall 2021 printing),
which publishes the pairs as Kepler used them. Three pairs are exactly 687 days apart;
two use longer baselines (an integer story the exercise simplifies — the day gaps are
recorded below and asserted by test, so nothing here rests on the folklore).

This world differs from the generated ones in the way that matters: nobody intervenes
on a planet. `intervene()` refuses. The law must be earned by proposing a functional
form and predicting a held-out point — before seeing it — not by acting.

Everything numeric here is deterministic pure Python. Only the proposing is live.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- dataset

# (date, Earth heliocentric longitude, Mars geocentric longitude), angles verbatim.
# Both longitudes are measured eastward from the vernal equinox; Earth's orbit is
# taken as a unit circle, the exercise's (and, near enough, Kepler's) approximation.
TYCHO_PAIRS: tuple = (
    (("1585-03-10", "179° 41'", "131° 48'"), ("1587-01-26", "136° 06'", "184° 42'")),
    (("1585-02-17", "159° 23'", "135° 12'"), ("1587-01-05", "115° 21'", "182° 08'")),
    (("1591-09-19", "5° 47'", "284° 18'"), ("1583-08-06", "323° 26'", "346° 56'")),
    (("1593-12-07", "85° 53'", "3° 04'"), ("1589-02-12", "41° 42'", "49° 42'")),
    (("1587-03-28", "196° 50'", "168° 12'"), ("1589-02-12", "153° 42'", "218° 48'")),
)

# The exercise's own annotations: pair 2 brackets perihelion, pairs 0-1 aphelion.
APHELION_PAIRS = (0, 1)
PERIHELION_PAIR = 2

# Multiplicative disguise for the blind brief. Any constant would do; this one turns
# "about one and a half astronomical units" into nothing in particular.
BLIND_SCALE = 0.7300


def _angle(text: str) -> float:
    deg, minutes = text.replace("°", " ").replace("'", " ").split()
    return float(deg) + float(minutes) / 60.0


def triangulate(pair) -> tuple[float, float]:
    """One Mars position (theta_deg, r_au) from two sightings of the same point."""
    (_, e1_txt, m1_txt), (_, e2_txt, m2_txt) = pair
    le1, lm1 = math.radians(_angle(e1_txt)), math.radians(_angle(m1_txt))
    le2, lm2 = math.radians(_angle(e2_txt)), math.radians(_angle(m2_txt))
    e1 = (math.cos(le1), math.sin(le1))
    e2 = (math.cos(le2), math.sin(le2))
    d1 = (math.cos(lm1), math.sin(lm1))
    d2 = (math.cos(lm2), math.sin(lm2))
    det = d1[0] * (-d2[1]) - (-d2[0]) * d1[1]
    t = ((e2[0] - e1[0]) * (-d2[1]) - (-d2[0]) * (e2[1] - e1[1])) / det
    x, y = e1[0] + t * d1[0], e1[1] + t * d1[1]
    return math.degrees(math.atan2(y, x)) % 360.0, math.hypot(x, y)


def mars_points() -> list[tuple[float, float]]:
    """The five triangulated (theta_deg, r_au) positions, in dataset order."""
    return [triangulate(p) for p in TYCHO_PAIRS]


# ----------------------------------------------------------------- observational world

class ObservationalOnly(RuntimeError):
    """Raised by intervene(): this world can only be watched."""


@dataclass
class HistoricalWorld:
    """A world backed by a fixed historical table instead of a sampled mechanism.

    observe() returns every row at once — history does not resample. intervene()
    refuses, which is the honest statement of what astronomy is: the one science
    that never got to act on its subject.
    """

    points: list = field(default_factory=mars_points)

    def observe(self) -> list[tuple[float, float]]:
        return list(self.points)

    def intervene(self, *_args, **_kwargs):
        raise ObservationalOnly(
            "this dataset is purely observational — nobody intervenes on a planet")


# ------------------------------------------------------------------------ law families
#
# Each family fits r(theta) by deterministic grid search with one refinement pass.
# No numpy, no randomness: the same points always give the same parameters.

def _sse(points, predict) -> float:
    return sum((r - predict(t)) ** 2 for t, r in points)


def fit_constant(points):
    c = sum(r for _, r in points) / len(points)
    return {"c": round(c, 6)}, (lambda t, c=c: c)


def fit_cosine(points):
    """r = a + b*cos(theta - phi): the generic periodic guess — and, to first order
    in eccentricity, exactly what a focus conic looks like."""
    best = None
    for step, centre, span in ((4.0, 180.0, 180.0), (0.25, None, 8.0)):
        lo = (centre if centre is not None else best[1]) - span
        hi = lo + 2 * span
        phi = lo
        while phi <= hi:
            cos = [math.cos(math.radians(t - phi)) for t, _ in points]
            n, sc = len(points), sum(cos)
            scc, sr = sum(c * c for c in cos), sum(r for _, r in points)
            src = sum(r * c for (_, r), c in zip(points, cos))
            det = n * scc - sc * sc
            if abs(det) > 1e-12:
                a = (sr * scc - sc * src) / det
                b = (n * src - sc * sr) / det
                sse = _sse(points, lambda t, a=a, b=b, p=phi:
                           a + b * math.cos(math.radians(t - p)))
                if best is None or sse < best[0]:
                    best = (sse, phi, a, b)
            phi += step
    _, phi, a, b = best
    if b < 0:  # canonical form: positive amplitude, phase shifted half a turn
        b, phi = -b, (phi + 180.0) % 360.0
    return ({"a": round(a, 6), "b": round(b, 6), "phi_deg": round(phi % 360.0, 3)},
            lambda t, a=a, b=b, p=phi: a + b * math.cos(math.radians(t - p)))


def fit_focus_conic(points):
    """r = p / (1 + e*cos(theta - theta0)): a conic with the origin at a focus."""
    best = None
    for estep, tstep, ecentre, tcentre in ((0.01, 4.0, None, None),
                                           (0.0005, 0.25, "refine", "refine")):
        e_lo, e_hi = (0.0, 0.5) if ecentre is None else (max(0.0, best[1] - 0.02),
                                                         best[1] + 0.02)
        t_lo, t_hi = (0.0, 360.0) if tcentre is None else (best[2] - 8.0, best[2] + 8.0)
        e = e_lo
        while e <= e_hi:
            t0 = t_lo
            while t0 <= t_hi:
                u = [1.0 / (1.0 + e * math.cos(math.radians(t - t0))) for t, _ in points]
                p = (sum(r * ui for (_, r), ui in zip(points, u))
                     / sum(ui * ui for ui in u))
                sse = _sse(points, lambda t, p=p, e=e, t0=t0:
                           p / (1.0 + e * math.cos(math.radians(t - t0))))
                if best is None or sse < best[0]:
                    best = (sse, e, t0, p)
                t0 += tstep
            e += estep
    _, e, t0, p = best
    return ({"p": round(p, 6), "e": round(e, 6), "theta0_deg": round(t0 % 360.0, 3)},
            lambda t, p=p, e=e, t0=t0: p / (1.0 + e * math.cos(math.radians(t - t0))))


def fit_offset_circle(points):
    """A circle whose centre is displaced from the origin — the hypothesis Kepler
    spent years on before giving it up."""
    best = None
    for step, span in ((0.02, 0.30), (0.002, 0.03)):
        cx0, cy0 = (0.0, 0.0) if best is None else (best[1], best[2])
        cx = cx0 - span
        while cx <= cx0 + span:
            cy = cy0 - span
            while cy <= cy0 + span:
                radii = [math.hypot(r * math.cos(math.radians(t)) - cx,
                                    r * math.sin(math.radians(t)) - cy)
                         for t, r in points]
                radius = sum(radii) / len(radii)

                def predict(t, cx=cx, cy=cy, radius=radius):
                    m = cx * math.cos(math.radians(t)) + cy * math.sin(math.radians(t))
                    disc = m * m + radius * radius - (cx * cx + cy * cy)
                    return m + math.sqrt(max(disc, 0.0))

                sse = _sse(points, predict)
                if best is None or sse < best[0]:
                    best = (sse, cx, cy, radius, predict)
                cy += step
            cx += step
    _, cx, cy, radius, predict = best
    return ({"cx": round(cx, 6), "cy": round(cy, 6), "radius": round(radius, 6)},
            predict)


FAMILIES = {
    "constant": fit_constant,
    "cosine": fit_cosine,
    "offset_circle": fit_offset_circle,
    "focus_conic": fit_focus_conic,
}


def leave_one_out(points=None) -> dict:
    """Mean held-out |error| per family, each point predicted by a fit that never
    saw it. Five points and three-parameter families: the errors are honest about
    how little data Kepler's contemporaries were working with."""
    points = points if points is not None else mars_points()
    out = {}
    for name, fitter in FAMILIES.items():
        errs = []
        for i, (t, r) in enumerate(points):
            rest = [p for j, p in enumerate(points) if j != i]
            _, predict = fitter(rest)
            errs.append(abs(predict(t) - r))
        out[name] = {"mean_abs_err": round(sum(errs) / len(errs), 6),
                     "worst_abs_err": round(max(errs), 6)}
    return out


def full_fits(points=None) -> dict:
    points = points if points is not None else mars_points()
    return {name: fitter(points)[0] for name, fitter in FAMILIES.items()}


# ------------------------------------------------------------------------- the briefs

HELD_OUT_INDEX = 3  # theta ~ 44 deg, r ~ 1.50 AU: mid-range, far from the aphelion
                    # cluster, so the families genuinely disagree about it.


def _rows(blind: bool):
    pts = mars_points()
    if blind:
        rows = [(round(t / 360.0, 5), round(r * BLIND_SCALE, 5)) for t, r in pts]
    else:
        rows = [(round(t, 3), round(r, 4)) for t, r in pts]
    held = rows[HELD_OUT_INDEX]
    shown = [row for i, row in enumerate(rows) if i != HELD_OUT_INDEX]
    return sorted(shown), held


def brief(blind: bool) -> tuple[str, tuple[float, float]]:
    """The text shown to the model, and the held-out (x1, x2) it must predict.

    The blind brief states one structural fact — x1 is cyclic with period 1 —
    because that is knowledge of the instrument, not of the subject. Kepler knew
    his coordinate was an angle; he did not know what curve he was on.
    """
    shown, held = _rows(blind)
    table = "\n".join(f"  x1={a}   x2={b}" for a, b in shown)
    if blind:
        head = ("Four measured rows of two variables. x1 is a cyclic coordinate with "
                "period 1 (x1=0 and x1=1 are the same place). x2 is a positive "
                "measured quantity in fixed but unstated units. Nothing else about "
                "the source of this data is available, and none of it is synthetic: "
                "these are real measurements.")
    else:
        head = ("Four heliocentric positions of the planet Mars, triangulated from "
                "Tycho Brahe's observations by the 687-day method Kepler describes "
                "in Astronomia Nova. x1 is heliocentric longitude in degrees; x2 is "
                "the Sun-Mars distance in astronomical units.")
    return (
        f"{head}\n\n{table}\n\n"
        "Task, in order:\n"
        "1. Is x2 constant in x1, or does it depend on x1? Decide from these rows.\n"
        "2. Propose the functional family relating them. Choose one of: constant, "
        "cosine (a + b*cos(angle - phase)), offset_circle (a circle displaced from "
        "the origin of a polar coordinate system), focus_conic (r = p/(1 + "
        "e*cos(angle - phase)), origin at a focus).\n"
        f"3. Predict x2 at x1={held[0]}. Commit to a number now; it will be scored "
        "against the measured value, which you have not been shown.\n"
        "4. Say what physical system, if any, you believe produced this data. If "
        "you do not know, say so.\n"
        "5. One sentence of rationale.",
        held,
    )


PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "depends_on_x1": {"type": "boolean"},
        "family": {"type": "string",
                   "enum": ["constant", "cosine", "offset_circle", "focus_conic"]},
        "predicted_x2": {"type": "number"},
        "claimed_source": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["depends_on_x1", "family", "predicted_x2", "claimed_source",
                 "rationale"],
}


def blind_inference(blind: bool = True) -> dict:
    """One live proposal, scored against the held-out point and the family fits.

    Everything the model is judged on was computed before it answered: the held-out
    value, and each family's own held-out prediction. The model's number lands
    somewhere in that field, and the record says where.
    """
    from .gemini import LAST_ERRORS, _generate  # imported here: only this is live

    text, held = brief(blind)
    scale = BLIND_SCALE if blind else 1.0
    shown = [p for i, p in enumerate(mars_points()) if i != HELD_OUT_INDEX]
    held_theta, held_r = mars_points()[HELD_OUT_INDEX]

    harness = {}
    for name, fitter in FAMILIES.items():
        _, predict = fitter(shown)
        harness[name] = round(predict(held_theta) * scale, 5)

    answer = _generate(text, PROPOSAL_SCHEMA)
    err = abs(answer["predicted_x2"] - held[1])
    return {
        "arm": "blind" if blind else "labelled",
        "held_out": {"x1": held[0], "x2": held[1]},
        "model": answer,
        "abs_error": round(err, 5),
        "abs_error_au": round(err / scale, 5),
        "harness_predictions": harness,
        "beats_constant": err < abs(harness["constant"] - held[1]),
        "transport_errors": list(LAST_ERRORS),
    }
