"""Render docs/architecture.png — the system, one screen, video-styled.

Same palette and faces as the demo video so every artifact looks like one
project. Deterministic: same code, same pixels.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 2200, 1400
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


F_TITLE = font(HELV, 64, bold=True)
F_SUB = font(HELV, 32)
F_BOX = font(HELV, 30, bold=True)
F_BODY = font(HELV, 25)
F_MONO = font(MENLO, 22)
F_LBL = font(HELV, 23)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


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


def box(x0, y0, x1, y1, title, body, border=LINE, mono=None):
    d.rounded_rectangle((x0, y0, x1, y1), 14, fill=PANEL, outline=border, width=3)
    y = y0 + 18
    d.text((x0 + 22, y), title, font=F_BOX, fill=INK)
    y += 44
    for line in wrap(body, F_BODY, x1 - x0 - 44):
        d.text((x0 + 22, y), line, font=F_BODY, fill=MUTED)
        y += 33
    if mono:
        d.text((x0 + 22, y1 - 44), mono, font=F_MONO, fill=BLUE)


def arrow(x0, y0, x1, y1, label=None, color=LINE):
    d.line((x0, y0, x1, y1), fill=color, width=3)
    import math
    a = math.atan2(y1 - y0, x1 - x0)
    for da in (0.42, -0.42):
        d.line((x1, y1, x1 - 18 * math.cos(a + da), y1 - 18 * math.sin(a + da)),
               fill=color, width=3)
    if label:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        tw = d.textlength(label, font=F_LBL)
        d.rectangle((mx - tw / 2 - 8, my - 26, mx + tw / 2 + 8, my + 4), fill=BG)
        d.text((mx - tw / 2, my - 22), label, font=F_LBL, fill=INK)


# ---- title
d.text((80, 56), "meta-science — architecture", font=F_TITLE, fill=INK)
d.text((80, 140), "an agent does science on worlds it has never seen; a gate decides — never the agent",
       font=F_SUB, fill=MUTED)

# ---- request path
box(80, 250, 420, 420, "Judge / anyone", "browser or curl — no credentials needed")
box(520, 250, 900, 420, "science.meta-agentic.ai",
    "Cloudflare DNS, 307 redirect, path preserved")
arrow(420, 335, 520, 335)
arrow(900, 335, 990, 335, "HTTPS")

# ---- Cloud Run
d.rounded_rectangle((990, 200, 2120, 900), 16, outline=BLUE, width=4)
d.text((1020, 222), "Cloud Run  ·  FastAPI  ·  europe-west1",
       font=F_BOX, fill=INK)
d.text((1815, 228), "app:v20 · GPL-3.0", font=F_MONO, fill=BLUE)

box(1020, 290, 1360, 560, "Generated worlds",
    "anonymised causal SCMs — six frozen templates, banned lexicon, "
    "deterministic from seed", mono="sha-256, not hash()")
box(1385, 290, 1725, 560, "Discovery loop",
    "predict before experiment — intervene — refute; the model is never "
    "asked if it was right")
box(1750, 290, 2090, 560, "Promotion gate",
    "champion vs challenger; promoted only past the margin",
    border=BLUE, mono="margin ε = 0.02")

box(1020, 600, 1725, 860, "Inspector & evidence UI",
    "what the agent may know beside the truth it may not; the 384-run study; "
    "raw export", mono="/world/{seed}/inspect · /evidence · /export.csv")
box(1750, 600, 2090, 860, "24 held-out worlds",
    "never shown to the proposer; cannot be enumerated, scored, or tuned against",
    border=ORANGE)

# ---- services row
box(80, 980, 560, 1180, "Secret Manager",
    "GEMINI_API_KEY at runtime; service account scoped to datastore.user only")
box(1000, 980, 1560, 1180, "Gemini · GenAI SDK",
    "proposer 3.6-flash, fallback 3.5-flash; auditor 3.5-flash-lite — advisory, cannot "
    "veto; narrator 3.1-flash-tts", border=BLUE)
box(1640, 980, 2120, 1180, "Firestore ledger",
    "tiers raw / wiki / output — a record's tier IS its status; every verdict "
    "writes a replayable receipt")

arrow(560, 1080, 990, 640, "key")
arrow(1280, 980, 1280, 900, "proposes · audits", BLUE)
arrow(1880, 900, 1880, 980, "verdicts + receipts")

# ---- terraform strip
d.rounded_rectangle((80, 1240, 2120, 1330), 14, outline=LINE, width=3)
d.text((110, 1264), "declared in Terraform — Cloud Run · Firestore · Secret Manager · IAM",
       font=F_BOX, fill=INK)
d.text((1520, 1268), "terraform apply, nothing by hand", font=F_MONO, fill=MUTED)

out = ROOT / "docs" / "architecture.png"
img.save(out)
print(out, img.size)
