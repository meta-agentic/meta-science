"""Render the two UML sequence diagrams — the gate, and the refutation.

docs/sequence-evolution.png : one generation of gated self-evolution, the
    system's thesis as a message flow — who may say what to whom, and what the
    proposer never sees.
docs/sequence-discovery.png : one hypothesis through the discovery loop — the
    prediction committed before the experiment, and a verdict computed rather
    than asked.

Same palette and faces as the demo video and the architecture diagram.
Deterministic: same code, same pixels.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BG = (26, 26, 25)
PANEL = (37, 38, 40)
LINE = (90, 92, 96)
INK = (232, 233, 236)
MUTED = (150, 153, 160)
BLUE = (57, 135, 229)
ORANGE = (217, 89, 38)

HELV = "/System/Library/Fonts/Helvetica.ttc"
MENLO = "/System/Library/Fonts/Menlo.ttc"


def font(path, size, bold=False):
    return ImageFont.truetype(path, size, index=1 if bold else 0)


F_TITLE = font(HELV, 54, bold=True)
F_SUB = font(HELV, 28)
F_HEAD = font(HELV, 28, bold=True)
F_MSG = font(HELV, 26)
F_NOTE = font(HELV, 24)
F_MONO = font(MENLO, 22)

ROW = 96
TOP = 260


def render(path, title, subtitle, parts, steps, note_w=430):
    """parts: [(name, accent)] ; steps: list of tuples
    ("msg", frm, to, label, mono?)      solid arrow, label above
    ("ret", frm, to, label)             dashed return arrow
    ("self", who, label, accent?)       self-note box on the lifeline
    ("note", text, accent)              full-width annotation strip
    ("gap",)                            breathing room
    """
    W = 2200
    H = TOP + ROW * len(steps) + 140
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((70, 46), title, font=F_TITLE, fill=INK)
    d.text((70, 118), subtitle, font=F_SUB, fill=MUTED)

    n = len(parts)
    xs = [int(140 + i * (W - 280) / (n - 1)) for i in range(n)]

    def wrap(text, fnt, width):
        words, lines, cur = text.split(), [], ""
        for w_ in words:
            t = f"{cur} {w_}".strip()
            if d.textlength(t, font=fnt) <= width:
                cur = t
            else:
                lines.append(cur)
                cur = w_
        if cur:
            lines.append(cur)
        return lines

    # lifeline headers
    for (name, accent), x in zip(parts, xs):
        tw = max(d.textlength(l, font=F_HEAD) for l in name.split("\n")) + 44
        x0, x1 = x - tw / 2, x + tw / 2
        d.rounded_rectangle((x0, 170, x1, 236), 12, fill=PANEL,
                            outline=accent or LINE, width=3)
        for i, l in enumerate(name.split("\n")):
            d.text((x - d.textlength(l, font=F_HEAD) / 2, 180 + i * 30),
                   l, font=F_HEAD, fill=INK)
        # dashed lifeline
        y = 236
        while y < H - 90:
            d.line((x, y, x, y + 12), fill=LINE, width=2)
            y += 22

    def head(x0, y0, x1, y1, color):
        import math
        a = math.atan2(y1 - y0, x1 - x0)
        for da in (0.42, -0.42):
            d.line((x1, y1, x1 - 16 * math.cos(a + da),
                    y1 - 16 * math.sin(a + da)), fill=color, width=3)

    y = TOP + 40
    for step in steps:
        kind = step[0]
        if kind == "gap":
            y += ROW // 2
            continue
        if kind == "note":
            _, text, accent = step
            lines = wrap(text, F_NOTE, W - 460)
            hgt = 24 + 30 * len(lines)
            d.rounded_rectangle((180, y - 10, W - 180, y - 10 + hgt), 10,
                                fill=PANEL, outline=accent, width=3)
            for i, l in enumerate(lines):
                d.text((204, y + 2 + 30 * i), l, font=F_NOTE, fill=INK)
            y += ROW + (len(lines) - 1) * 26
            continue
        if kind == "self":
            _, who, label, *rest = step
            accent = rest[0] if rest else LINE
            x = xs[who]
            lines = wrap(label, F_NOTE, note_w - 40)
            hgt = 22 + 28 * len(lines)
            bx0 = max(50, min(x - note_w / 2, W - 50 - note_w))
            d.rounded_rectangle((bx0, y - 8, bx0 + note_w,
                                 y - 8 + hgt), 10, fill=PANEL,
                                outline=accent, width=3)
            for i, l in enumerate(lines):
                d.text((bx0 + 20, y + 28 * i), l,
                       font=F_NOTE, fill=INK)
            y += ROW + (len(lines) - 1) * 24
            continue

        frm, to, label = step[1], step[2], step[3]
        mono = step[4] if len(step) > 4 else None
        x0, x1 = xs[frm], xs[to]
        color = BLUE if kind == "msg" else LINE
        ay = y + 34
        if kind == "ret":
            x = x0
            seg = 16 if x1 > x0 else -16
            while (x < x1 - 14) if x1 > x0 else (x > x1 + 14):
                d.line((x, ay, x + seg * 0.7, ay), fill=color, width=3)
                x += seg
        else:
            d.line((x0, ay, x1, ay), fill=color, width=3)
        head(x0, ay, x1, ay, color)
        mid = (x0 + x1) / 2
        tw = d.textlength(label, font=F_MSG)
        d.text((mid - tw / 2, y - 4), label, font=F_MSG, fill=INK)
        if mono:
            mw = d.textlength(mono, font=F_MONO)
            d.text((mid - mw / 2, ay + 8), mono, font=F_MONO, fill=MUTED)
        y += ROW

    img.save(path)
    print(path, img.size)


# ---------------------------------------------------------------- the gate
render(
    ROOT / "docs" / "sequence-evolution.png",
    "One generation of gated self-evolution",
    "the proposer never sees the held-out seeds, never runs the scorer, and never writes above raw",
    parts=[("Gemini proposer\n3.6-flash", BLUE), ("Promotion gate", BLUE),
           ("24 held-out worlds", ORANGE), ("Firestore ledger", None),
           ("Auditor\n3.5-flash-lite", BLUE)],
    steps=[
        ("ret", 1, 0, "champion knobs + observed weaknesses",
         "never: seeds, scorer, canon"),
        ("msg", 0, 1, "challenger  (diff + rationale)"),
        ("msg", 1, 2, "evaluate champion and challenger",
         "accuracy and cost, separately"),
        ("ret", 2, 1, "both scores"),
        ("self", 1, "verdict: challenger ≥ champion + ε ?   "
                    "ε = 0.02 — a gate without a margin ratchets on noise",
         BLUE),
        ("msg", 1, 3, "receipt — promotion and refusal alike",
         "diff · scores · margin · seeds · decomposition"),
        ("msg", 1, 4, "promotion receipt (only if promoted)"),
        ("ret", 4, 3, "audit: legitimate / flagged, in writing",
         "advisory — dissent on the record, no veto"),
        ("ret", 1, 0, "verdict as structured history",
         "refused diffs are not re-proposed"),
        ("note", "In the three published runs: one promotion and two refusals, "
                 "every time. Four of the six refusals were of candidates that "
                 "scored HIGHER and missed the margin — refusing a real gain is "
                 "what stops a system ratcheting itself forward on noise.",
         ORANGE),
    ])

# ------------------------------------------------------------ the refutation
render(
    ROOT / "docs" / "sequence-discovery.png",
    "One hypothesis through the discovery loop",
    "the prediction is committed before the experiment; the model is never asked whether it was right",
    parts=[("Discovery loop", None), ("Gemini reasoner", BLUE),
           ("Anonymised world", ORANGE), ("Trace / receipts", None)],
    steps=[
        ("msg", 0, 2, "observe(n) — passive samples",
         "opaque labels X1..Xn, banned lexicon enforced"),
        ("ret", 2, 0, "observations"),
        ("msg", 0, 1, "rank candidate (cause, effect) pairs",
         "associations only — advisory"),
        ("ret", 1, 0, "ranking",
         "a bad ranking costs experiments, never correctness"),
        ("msg", 0, 3, "COMMIT prediction: sign and magnitude",
         "before the experiment — after, it is a description"),
        ("msg", 0, 2, "intervene(var, value, n)",
         "independent noise per arm — paired arms flattered the metric"),
        ("ret", 2, 0, "outcomes"),
        ("self", 0, "verdict computed: prediction vs measured effect — "
                    "CONFIRMED or REFUTED, never solicited", BLUE),
        ("msg", 0, 3, "verdict + effect, joined to ground truth",
         "GET /export.csv — one row per hypothesis"),
        ("note", "The confounded templates invert: observational correlation "
                 "carries the OPPOSITE sign of the true causal effect (83.9% of "
                 "confounded worlds). Reading alone concludes the opposite of "
                 "the truth — 0/4 recovered by observation, 4/4 by intervention.",
         ORANGE),
    ])
