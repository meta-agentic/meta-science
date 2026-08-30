"""Laws as expressions: the agent composes mathematics, the harness judges it.

Until now the law loop offered a menu of four hand-coded families, which has two
faults: the agent cannot express a law we did not anticipate, and the menu itself is
a fingerprint (offering r = p/(1+e·cos) all but names Kepler). This module removes
the menu. A law is a string over a small grammar —

    expr := number | x1 | c1..c4 | expr (+ - * /) expr | -expr
          | cos sin exp log sqrt abs (expr) | pow(expr, expr)

— proposed free-form, parsed by a recursive-descent parser (never eval), with free
constants c1..c4 fitted by the harness. The agent's job is the *shape* of the law;
the arithmetic, as ever, belongs to the machinery.

Fitting is deterministic: a fixed lattice of starting points refined by Nelder-Mead
with capped iterations — the same expression on the same data always yields the same
constants. Complexity is the node count, reported alongside error so that a gate can
one day charge it the way the strategy gate charges measurement.
"""
from __future__ import annotations

import math
import re

MAX_CONSTS = 4
_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?)|(x\d+|c[1-4]|pi"
                    r"|cos|sin|exp|log|sqrt|abs|pow)|(.))")

_FUNCS = {
    "cos": math.cos, "sin": math.sin, "exp": math.exp,
    "log": math.log, "sqrt": math.sqrt, "abs": abs,
}


class LawSyntaxError(ValueError):
    """The proposed expression is not in the grammar."""


def _tokens(text: str) -> list:
    out, pos = [], 0
    for m in _TOKEN.finditer(text):
        if m.start() != pos and text[pos:m.start()].strip():
            raise LawSyntaxError(f"cannot read {text[pos:m.start()]!r}")
        pos = m.end()
        num, word, sym = m.groups()
        if num is not None:
            out.append(("num", float(num)))
        elif word is not None:
            out.append(("word", word))
        elif sym.strip():
            if sym not in "+-*/(),":
                raise LawSyntaxError(f"unexpected character {sym!r}")
            out.append(("sym", sym))
    if pos != len(text) and text[pos:].strip():
        raise LawSyntaxError(f"cannot read {text[pos:]!r}")
    return out


def parse(text: str):
    """Expression string -> AST of nested tuples. Raises LawSyntaxError."""
    tokens = _tokens(text)
    i = 0

    def peek():
        return tokens[i] if i < len(tokens) else (None, None)

    def take(kind, value=None):
        nonlocal i
        k, v = peek()
        if k != kind or (value is not None and v != value):
            raise LawSyntaxError(f"expected {value or kind}, found {v!r}")
        i += 1
        return v

    def atom():
        nonlocal i
        k, v = peek()
        if k == "num":
            i += 1
            return ("const", v)
        if k == "word":
            i += 1
            if v == "pi":
                return ("const", math.pi)
            if re.fullmatch(r"x\d+|c[1-4]", v):
                return ("var", v)
            if v == "pow":
                take("sym", "(")
                base = expr()
                take("sym", ",")
                exponent = expr()
                take("sym", ")")
                return ("pow", base, exponent)
            take("sym", "(")
            inner = expr()
            take("sym", ")")
            return ("call", v, inner)
        if k == "sym" and v == "(":
            i += 1
            inner = expr()
            take("sym", ")")
            return inner
        if k == "sym" and v == "-":
            i += 1
            return ("neg", atom())
        raise LawSyntaxError(f"unexpected {v!r}")

    def term():
        node = atom()
        while peek() == ("sym", "*") or peek() == ("sym", "/"):
            op = take("sym")
            node = ("mul" if op == "*" else "div", node, atom())
        return node

    def expr():
        node = term()
        while peek() == ("sym", "+") or peek() == ("sym", "-"):
            op = take("sym")
            node = ("add" if op == "+" else "sub", node, term())
        return node

    tree = expr()
    if i != len(tokens):
        raise LawSyntaxError(f"trailing input from {tokens[i]!r}")
    return tree


def variables(tree) -> set:
    kind = tree[0]
    if kind == "var":
        return {tree[1]}
    if kind == "const":
        return set()
    return set().union(*(variables(t) for t in tree[1:] if isinstance(t, tuple)))


def complexity(tree) -> int:
    if tree[0] in ("const", "var"):
        return 1
    return 1 + sum(complexity(t) for t in tree[1:] if isinstance(t, tuple))


def evaluate(tree, env: dict) -> float:
    """May raise ValueError/OverflowError/ZeroDivisionError on domain faults —
    the fitter treats those as an infinitely bad law at that point."""
    kind = tree[0]
    if kind == "const":
        return tree[1]
    if kind == "var":
        return env[tree[1]]
    if kind == "neg":
        return -evaluate(tree[1], env)
    if kind == "call":
        return _FUNCS[tree[1]](evaluate(tree[2], env))
    a = evaluate(tree[1], env)
    b = evaluate(tree[2], env)
    if kind == "add":
        return a + b
    if kind == "sub":
        return a - b
    if kind == "mul":
        return a * b
    if kind == "div":
        return a / b
    if kind == "pow":
        return math.pow(a, b)
    raise LawSyntaxError(f"unknown node {kind!r}")


# ---------------------------------------------------------------------------- fitting

def _sse(tree, consts, points) -> float:
    total = 0.0
    for x1, x2 in points:
        env = {"x1": x1, **consts}
        try:
            err = evaluate(tree, env) - x2
        except (ValueError, OverflowError, ZeroDivisionError):
            return math.inf
        if not math.isfinite(err):
            return math.inf
        total += err * err
    return total


_STARTS = (-2.0, -0.5, 0.1, 0.5, 1.0, 3.0)


def fit(tree, points) -> tuple[dict, float]:
    """Fit the free constants by deterministic multi-start Nelder-Mead.

    Same tree, same points, same answer — the start lattice is fixed and the
    simplex arithmetic is plain floats. Returns ({c: value}, sse).
    """
    names = sorted(v for v in variables(tree) if v.startswith("c"))
    if not names:
        return {}, _sse(tree, {}, points)

    def loss(vec):
        return _sse(tree, dict(zip(names, vec)), points)

    best_vec, best_sse = None, math.inf
    k = len(names)
    starts = [[s] * k for s in _STARTS]
    starts += [[_STARTS[(i + j) % len(_STARTS)] for j in range(k)]
               for i in range(len(_STARTS))]
    for start in starts:
        vec, sse = _nelder_mead(loss, start)
        if sse < best_sse:
            best_vec, best_sse = vec, sse
    return dict(zip(names, [round(v, 6) for v in best_vec])), best_sse


def _nelder_mead(loss, start, iterations=200, step=0.5):
    n = len(start)
    simplex = [list(start)]
    for i in range(n):
        p = list(start)
        p[i] += step
        simplex.append(p)
    values = [loss(p) for p in simplex]
    for _ in range(iterations):
        order = sorted(range(n + 1), key=lambda i: values[i])
        simplex = [simplex[i] for i in order]
        values = [values[i] for i in order]
        if values[0] != math.inf and abs(values[-1] - values[0]) < 1e-12:
            break
        centroid = [sum(p[i] for p in simplex[:-1]) / n for i in range(n)]
        worst = simplex[-1]
        refl = [c + (c - w) for c, w in zip(centroid, worst)]
        fr = loss(refl)
        if fr < values[0]:
            expa = [c + 2 * (c - w) for c, w in zip(centroid, worst)]
            fe = loss(expa)
            simplex[-1], values[-1] = (expa, fe) if fe < fr else (refl, fr)
        elif fr < values[-2]:
            simplex[-1], values[-1] = refl, fr
        else:
            contr = [c + 0.5 * (w - c) for c, w in zip(centroid, worst)]
            fc = loss(contr)
            if fc < values[-1]:
                simplex[-1], values[-1] = contr, fc
            else:
                bestp = simplex[0]
                simplex = [bestp] + [[(p[i] + bestp[i]) / 2 for i in range(n)]
                                     for p in simplex[1:]]
                values = [values[0]] + [loss(p) for p in simplex[1:]]
    order = sorted(range(n + 1), key=lambda i: values[i])
    return simplex[order[0]], values[order[0]]


# ---------------------------------------------------------------------------- scoring

def score(expression: str, points, stride: int = 5) -> dict:
    """Parse, fit on the training split, judge on the held-out split.

    The same held-out discipline as everywhere else in this project: the constants
    never see the points they are scored on.
    """
    tree = parse(expression)
    unknown = {v for v in variables(tree) if not (v == "x1" or v.startswith("c"))}
    if unknown:
        raise LawSyntaxError(f"unknown variables {sorted(unknown)}")
    train = [p for i, p in enumerate(points) if i % stride]
    test = [p for i, p in enumerate(points) if not i % stride]
    consts, train_sse = fit(tree, train)
    errs = []
    for x1, x2 in test:
        try:
            errs.append(abs(evaluate(tree, {"x1": x1, **consts}) - x2))
        except (ValueError, OverflowError, ZeroDivisionError):
            errs.append(math.inf)
    mean = sum(errs) / len(errs)
    return {
        "expression": expression,
        "constants": consts,
        "complexity": complexity(tree),
        "train_sse": (round(train_sse, 9) if math.isfinite(train_sse) else None),
        "holdout_mean_abs_err": (round(mean, 6) if math.isfinite(mean) else None),
        "holdout_worst_abs_err": (round(max(errs), 6) if math.isfinite(max(errs))
                                  else None),
    }


def score_in_time(expression: str, points, train_frac: float = 0.6,
                  judge_frac: float = 0.2) -> dict:
    """Fit on the earliest rows, judge on the final ones — extrapolation.

    `points` must be in causal order (time for a timed series; the orbit's own
    sweep for angular data). The constants never see the judged rows, and unlike
    the stride split, neither do their neighbours: the law is asked about a
    region of the world it has only ever pointed toward.
    """
    tree = parse(expression)
    unknown = {v for v in variables(tree) if not (v == "x1" or v.startswith("c"))}
    if unknown:
        raise LawSyntaxError(f"unknown variables {sorted(unknown)}")
    n = len(points)
    train = points[:max(2, int(n * train_frac))]
    judged = points[n - max(1, int(n * judge_frac)):]
    consts, _ = fit(tree, train)
    errs = []
    for x1, x2 in judged:
        try:
            errs.append(abs(evaluate(tree, {"x1": x1, **consts}) - x2))
        except (ValueError, OverflowError, ZeroDivisionError):
            errs.append(math.inf)
    mean = sum(errs) / len(errs)
    return {
        "expression": expression,
        "constants": consts,
        "train_rows": len(train),
        "judged_rows": len(judged),
        "future_mean_abs_err": (round(mean, 6) if math.isfinite(mean) else None),
        "future_worst_abs_err": (round(max(errs), 6) if math.isfinite(max(errs))
                                 else None),
    }


# A law extrapolates if its future error stays within TOLERANCE times its
# interleaved error, or within ABS_FLOOR of the data's own scale — whichever is
# more generous. Both bounds are needed, and the second was learned from the
# first's failure: a shape that interpolates near-perfectly can have a future
# error 8x its interleaved error that is still 0.08% of the data — a pure
# self-ratio punishes excellence. Calibrated on the second-law drag arc: the
# true shape (linear - quadratic) passes, naive linear fails for missing the
# decay, and the saturating impostors fail by an order of magnitude.
EXTRAPOLATION_TOLERANCE = 3.0
EXTRAPOLATION_ABS_FLOOR = 1e-3


def judge(expression: str, points, stride: int = 5, train_frac: float = 0.6,
          judge_frac: float = 0.2) -> dict:
    """Both verdicts on one law: interpolation (stride) and extrapolation (time).

    The second-law experiment is why both are required: a hyperbolic-tangent
    'law' for a decaying orbit scored 0.06% relative on the interleaved split
    and collapsed 22x when fitted early and judged late. Interpolation
    flatters; a law is a claim about the rows that have not happened yet.
    """
    interp = score(expression, points, stride)
    extrap = score_in_time(expression, points, train_frac, judge_frac)
    i_err, f_err = interp["holdout_mean_abs_err"], extrap["future_mean_abs_err"]
    if i_err is None or f_err is None:
        penalty, extrapolates = None, False
    else:
        # floor at the reporting quantum: a machine-precision interpolation must
        # not make a tiny future error look infinitely bad
        penalty = round(f_err / max(i_err, 1e-6), 3)
        scale = sum(abs(x2) for _, x2 in points) / len(points)
        allowance = max(EXTRAPOLATION_TOLERANCE * i_err,
                        EXTRAPOLATION_ABS_FLOOR * scale)
        extrapolates = f_err <= allowance
    return {
        "expression": expression,
        "interpolation": {k: v for k, v in interp.items() if k != "expression"},
        "extrapolation": {k: v for k, v in extrap.items() if k != "expression"},
        "extrapolation_penalty": penalty,
        "extrapolates": extrapolates,
    }


# ------------------------------------------------------------------- free-form probe

FREEFORM_SCHEMA = {
    "type": "object",
    "properties": {
        "depends_on_x1": {"type": "boolean"},
        "expression": {"type": "string"},
        "claimed_source": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["depends_on_x1", "expression", "claimed_source", "rationale"],
}


def freeform_prompt(rows: list, held_x1: float, cyclic: bool = True) -> str:
    """No menu, no family names: the agent must compose the law itself."""
    table = "\n".join(f"  x1={a}   x2={b}" for a, b in rows)
    x1_fact = ("x1 is a cyclic coordinate with period 1 (x1=0 and x1=1 are the "
               "same place)" if cyclic else
               "x1 is a positive measured quantity in fixed but unstated units")
    return (
        f"{len(rows)} measured rows of two variables. {x1_fact}. x2 is a positive "
        "measured quantity in fixed but unstated units. Nothing else about the "
        "source of this data is available.\n\n" + table + "\n\n"
        "Task:\n"
        "1. Does x2 depend on x1?\n"
        "2. Write ONE mathematical expression for x2 as a function of x1. You may "
        "use: numbers, x1, free constants c1 c2 c3 c4 (their values will be fitted "
        "for you — put every tunable quantity into a constant), pi, + - * / "
        "parentheses, and the functions cos sin exp log sqrt abs pow(base, "
        "exponent). Nothing else. Choose the SHAPE of the law; do not solve for "
        "the constants.\n"
        f"3. The expression will be judged on measurements you have not seen, "
        f"including near x1={held_x1}.\n"
        "4. Say what specific physical system, if any, you believe produced this "
        "data. If you cannot name one, say so.\n"
        "5. One sentence of rationale.")


def freeform_probe(points, n_shown: int = 11, stride: int = 5) -> dict:
    """One live free-form proposal, scored by the harness. Returns the record."""
    from .gemini import _generate  # imported here: only this is live

    from .kepler import BLIND_SCALE
    scaled = [(round(t / 360.0, 5), round(r * BLIND_SCALE, 5)) for t, r in points]
    step = max(1, len(scaled) // n_shown)
    shown = scaled[::step][:n_shown]
    held_x1 = scaled[len(scaled) // 3][0]

    answer = _generate(freeform_prompt(shown, held_x1), FREEFORM_SCHEMA)
    record = {"model": answer}
    try:
        record["scored"] = judge(answer["expression"], scaled, stride)
    except LawSyntaxError as exc:
        record["scored"] = {"error": str(exc)}
    return record
