#!/usr/bin/env python3
"""The submission video, built from components.

Each clip is a function registered in CLIPS — intro, a corpus of scenes, outro.
Rebuild any subset (`python3 video/build.py corpus_refutation`) or everything
(`python3 video/build.py`); clips render to video/out/<name>.mp4 and concatenate
into video/out/final.mp4. All content is drawn from REAL captured output — the
deterministic demo transcript, the frozen study, live generation results — so the
video shows what the system does, in the system's own palette.

No voiceover by design: the narration is on screen, timed for reading.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
W, H = 1920, 1080
FPS = 30

# The site's dark palette — the video and the artifact are one system.
BG = (26, 26, 25)
CARD = (34, 34, 32)
LINE = (51, 50, 47)
INK1 = (255, 255, 255)
INK2 = (195, 194, 183)
INK3 = (138, 137, 131)
BLUE = (57, 135, 229)
ORANGE = (217, 89, 38)

MENLO = "/System/Library/Fonts/Menlo.ttc"
HELV = "/System/Library/Fonts/Helvetica.ttc"


def font(path: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=1 if bold else 0)


F_TITLE = font(HELV, 92, bold=True)
F_SUB = font(HELV, 46)
F_H = font(HELV, 56, bold=True)
F_BODY = font(HELV, 42)
F_MONO = font(MENLO, 34)
F_MONO_S = font(MENLO, 27)
F_FOOT = font(HELV, 28)
STIX = "/System/Library/Fonts/Supplemental/STIXGeneral.otf"
F_GREEK_H = ImageFont.truetype(STIX, 88)
F_GREEK = ImageFont.truetype(STIX, 46)
F_MATH = ImageFont.truetype(STIX, 54)
F_MATH_S = ImageFont.truetype(STIX, 38)
# A philosopher's hand for the Latin marginalia.
F_QUILL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Apple Chancery.ttf", 46)


class Scene:
    """Accumulates (image, duration) stills; renders to one mp4 via concat."""

    def __init__(self, name: str):
        self.name = name
        self.frames: list[tuple[Image.Image, float]] = []

    def base(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, H - 74, W, H], fill=CARD)
        d.line([0, H - 74, W, H - 74], fill=LINE, width=2)
        d.text((60, H - 56), "meta-science", font=F_FOOT, fill=INK2)
        d.text((W - 60, H - 56),
               "Marco Vanadia · mova  ·  github.com/meta-agentic/meta-science  ·  GPL-3.0",
               font=F_FOOT, fill=INK3, anchor="ra")
        return img, d

    def hold(self, img: Image.Image, seconds: float) -> None:
        self.frames.append((img, seconds))

    def render(self) -> Path:
        clip_dir = OUT / self.name
        clip_dir.mkdir(parents=True, exist_ok=True)
        concat = []
        for i, (img, dur) in enumerate(self.frames):
            p = clip_dir / f"f{i:04d}.png"
            img.save(p)
            concat.append(f"file '{p.name}'\nduration {dur:.3f}\n")
        concat.append(f"file '{self.frames[-1][0] and f'f{len(self.frames)-1:04d}.png'}'\n")
        (clip_dir / "list.txt").write_text("".join(concat))
        out = OUT / f"{self.name}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(clip_dir / "list.txt"),
             "-vf", f"fps={FPS},format=yuv420p", str(out)], check=True)
        print(f"  {out.name}")
        return out


def wrap(d: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = f"{cur} {w_}".strip()
        if d.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def text_block(d, x, y, text, fnt, fill, max_w=1700, lh=1.35) -> int:
    for line in wrap(d, text, fnt, max_w):
        d.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * lh)
    return y


def reveal(scene: Scene, build_fn, items: list, per_item: float, tail: float) -> None:
    """Component animation: re-draw with 1..n items visible, then hold."""
    for n in range(1, len(items) + 1):
        img = build_fn(items[:n])
        scene.hold(img, per_item)
    scene.hold(build_fn(items), tail)


# ── intro ────────────────────────────────────────────────────────────────────

def intro() -> Scene:
    s = Scene("intro")
    img, d = s.base()
    d.text((W // 2, 400), "meta-science", font=F_TITLE, fill=INK1, anchor="ma")
    s.hold(img, 1.6)
    img, d = s.base()
    d.text((W // 2, 400), "meta-science", font=F_TITLE, fill=INK1, anchor="ma")
    d.text((W // 2, 540), "An agent that does science on worlds it has never seen —",
           font=F_SUB, fill=INK2, anchor="ma")
    d.text((W // 2, 605), "and that can be refuted. Including about itself.",
           font=F_SUB, fill=INK2, anchor="ma")
    s.hold(img, 3.4)
    img, d = s.base()
    d.text((W // 2, 340), "Every self-improvement demo shows you successes.",
           font=F_H, fill=INK1, anchor="ma")
    d.text((W // 2, 470), "A system that reports it improved is indistinguishable",
           font=F_BODY, fill=INK2, anchor="ma")
    d.text((W // 2, 530), 'from one that logs "improved!" and changes nothing.',
           font=F_BODY, fill=INK2, anchor="ma")
    d.text((W // 2, 680), "So we built the one that can refuse itself.",
           font=F_H, fill=BLUE, anchor="ma")
    s.hold(img, 6.0)
    return s


def axioms() -> Scene:
    """The project's invariants, staged like a proof — because they are the proof
    obligations everything else discharges. The mathematical script is reserved for
    the mathematics; everything a judge must read is plain English."""
    s = Scene("axioms")

    BLOCKS = [
        ("AXIOM", [
            # ⊢ is syntactic (derives), ⊨ is semantic (holds): an agent's own
            # derivation never entails truth. The earlier "A ⊬ ⊨ c(A)" juxtaposed
            # two turnstiles with no operand between them — malformed, caught by
            # the author.
            ("A1", "No agent is the judge of its own claims.", "A ⊢ c  ⇏  ⊨ c",
             "⊢ derives (syntax) · ⊨ holds (semantics) — derivation never entails truth",
             "Ex probatione propria non sequitur veritas."),
            # ≢, not ≠: for an unconfounded X the two quantities ARE equal — that
            # is what randomised experiments buy. The axiom says the operators are
            # not identical; they coincide only when it has been earned.
            ("A2", "Seeing is not doing.", "P(Y | do(X)) ≢ P(Y | X)",
             "not identical — they coincide only when confounding is absent"),
        ]),
        ("HYPOTHESIS", [
            ("", "A model can improve its own method.", "∃ Μ′ : Μ′ ≻ Μ", ""),
        ]),
        ("THESIS", [
            ("", "Improvement counts only when proven on worlds the proposer "
                 "cannot see — by a margin, or not at all.",
             "Μ′ ≻ Μ  ⟺  S(Μ′, W) ≥ S(Μ, W) + ε ,   W ∩ view(Μ′) = ∅", ""),
        ]),
    ]

    def build(n_blocks):
        img, d = s.base()
        d.text((W // 2, 56), "Μ Ε Τ Α · Ε Π Ι Σ Τ Η Μ Η", font=F_GREEK, fill=INK3,
               anchor="ma")
        d.text((W // 2, 120), "The axioms", font=F_H, fill=INK1, anchor="ma")
        d.line([W // 2 - 220, 208, W // 2 + 220, 208], fill=LINE, width=2)
        y = 250
        for title, rows in BLOCKS[:n_blocks]:
            d.text((120, y), title, font=F_FOOT, fill=BLUE)
            y += 46
            for row in rows:
                tag, maxim, formula, gloss = row[:4]
                latin = row[4] if len(row) > 4 else None
                x = 160
                if tag:
                    d.text((x, y + 8), tag, font=F_FOOT, fill=INK3)
                x += 60
                wide = d.textlength(formula, font=F_MATH) > 820
                if wide:
                    # A formula too long for the right column goes UNDER its maxim,
                    # full width, rather than colliding with it.
                    yy = text_block(d, x, y, maxim, F_BODY, INK1, max_w=1560)
                    d.text((x + 40, yy + 14), formula, font=F_MATH_S, fill=INK2)
                    y = yy + 78
                else:
                    d.text((x, y), maxim, font=F_BODY, fill=INK1)
                    d.text((1060, y - 6), formula, font=F_MATH, fill=INK2)
                    if gloss:
                        # Helvetica has no turnstiles — a gloss carrying logic
                        # symbols renders in the math face or it renders as tofu.
                        gf = (ImageFont.truetype(STIX, 30)
                              if any(ord(ch) > 0x2200 for ch in gloss) else F_FOOT)
                        d.text((x, y + 56), gloss, font=gf, fill=INK3)
                    y += 104 if gloss else 78
                    if latin:
                        d.text((x + 30, y - 2), latin, font=F_QUILL, fill=(176, 148, 96))
                        y += 76
            y += 30
        return img

    for n, dur in ((1, 6.5), (2, 3.5), (3, 7.0)):
        s.hold(build(n), dur)
    return s


# ── corpus ───────────────────────────────────────────────────────────────────

def corpus_world() -> Scene:
    s = Scene("corpus_world")
    demo = (ROOT / "assets" / "demo.txt").read_text().splitlines()
    brief = [l for l in demo if l.startswith("  {'world_id'")][:1]

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "1 · What the agent is allowed to know", font=F_H, fill=INK1)
        y = 210
        for kind, line in shown:
            color = {"h": INK1, "m": BLUE, "d": INK3}[kind]
            fnt = F_MONO if kind == "m" else F_BODY
            y = text_block(d, 100, y, line, fnt, color) + 18
        return img

    items = [
        ("m", brief[0].strip() if brief else
         "{'world_id': 'W-7', 'variables': ['X2','X1'], 'affordances': ['observe(n)', 'intervene(var, value, n)']}"),
        ("h", "Opaque labels. No units, no documentation, no structure."),
        ("d", "Two affordances: observe passively, or intervene and watch."),
        ("d", "Worlds are drawn from real scientific structures — then anonymised, "
              "so the model cannot recognise the system and recite a law from memory. "
              "It must discover, because it cannot retrieve."),
    ]
    reveal(s, build, items, 2.4, 4.5)
    return s


def corpus_trap() -> Scene:
    s = Scene("corpus_trap")

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "2 · The trap in the data", font=F_H, fill=INK1)
        y = 210
        for kind, line in shown:
            if kind == "big":
                d.text((W // 2, y), line, font=F_TITLE, fill=ORANGE, anchor="ma")
                y += 150
            elif kind == "table":
                d.rectangle([300, y, W - 300, y + 170], fill=CARD, outline=LINE, width=2)
                d.text((360, y + 30), "Gemini, observation only", font=F_BODY, fill=INK2)
                d.text((W - 360, y + 30), "0 / 4 worlds", font=F_BODY, fill=ORANGE, anchor="ra")
                d.text((360, y + 100), "The same loop, allowed to intervene", font=F_BODY, fill=INK2)
                d.text((W - 360, y + 100), "4 / 4 worlds", font=F_BODY, fill=BLUE, anchor="ra")
                y += 210
            else:
                y = text_block(d, 100, y, line, F_BODY,
                               INK2 if kind == "d" else INK1) + 18
        return img

    items = [
        ("h", "The agent observes a confounded world. The correlation is strong, clean —"),
        ("big", "corr = −0.96      truth = +1.25"),
        ("d", "— and it points the wrong way. A hidden common cause dominates the data."),
        ("table", ""),
        ("d", "Identical worlds. The only difference is the ability to act. "
              "That is also the adversarial proof that anonymisation holds."),
    ]
    reveal(s, build, items, 3.0, 5.5)
    return s


def _verdict_panel(d, y, title, lines, note=None):
    d.text((120, y), title, font=F_MONO, fill=INK3)
    y += 60
    d.rectangle([80, y - 16, W - 80, y + 14 + 56 * len(lines)], fill=CARD,
                outline=LINE, width=2)
    for line in lines:
        verdict = "REFUTED" if "REFUTED" in line else "SUPPORTED"
        body = line.replace(verdict, "").rstrip()
        d.text((120, y), body, font=F_MONO_S, fill=INK1)
        d.text((W - 140, y), verdict, font=F_MONO_S,
               fill=ORANGE if verdict == "REFUTED" else BLUE, anchor="ra")
        y += 56
    if note:
        # Menlo, not Helvetica: the note carries arrows (X1→X4) and Helvetica has
        # no glyph for U+2192, which rendered as a tofu box in the shipped cut.
        d.text((120, y + 18), note, font=F_MONO_S, fill=INK3)
        y += 50
    return y + 40


def corpus_refutation() -> Scene:
    s = Scene("corpus_refutation")
    demo = (ROOT / "assets" / "demo.txt").read_text().splitlines()
    trap = [l.strip() for l in demo if "predicted" in l and "measured" in l]
    mixed = (ROOT / "assets" / "mixed.txt").read_text().splitlines()

    def build(stage):
        img, d = s.base()
        d.text((60, 70), "3 · Confirmed — and refuted — by experiment", font=F_H, fill=INK1)
        y = 210
        y = _verdict_panel(d, y, "an ordinary world — both verdicts, earned", mixed,
                           note="X1→X4 supported, X4→X1 refuted: directionality, discovered.")
        if stage >= 2:
            y = _verdict_panel(d, y, "the confounded world — its best hypothesis dies", trap)
        if stage >= 3:
            text_block(d, 100, y,
                       "The prediction is committed BEFORE the experiment runs; the "
                       "verdict is a comparison, never a question put to the model.",
                       F_BODY, INK1)
        return img

    for stage, dur in ((1, 6.0), (2, 5.0), (3, 6.0)):
        s.hold(build(stage), dur)
    return s


def _ghost_panel(d, y, label, text, upto=None):
    """Verbatim model reasoning, revealed as it 'thinks'. Nothing paraphrased —
    the whole point is that this text came out of the model, not out of us."""
    d.text((120, y), label, font=F_FOOT, fill=BLUE)
    y += 42
    shown = text if upto is None else text[:upto] + "▌"
    box_h = 46 * len(wrap(ImageDraw.Draw(Image.new('RGB', (1, 1))), text,
                          F_MONO_S, 1560)) + 18
    d.rectangle([80, y - 14, W - 80, y + box_h], fill=(22, 30, 40),
                outline=BLUE, width=2)
    yy = y + 6
    dd = d
    for line in wrap(dd, shown, F_MONO_S, 1560):
        dd.text((130, yy), line, font=F_MONO_S, fill=INK1)
        yy += 46
    return y + box_h + 30


def corpus_evolution() -> Scene:
    import json as _json
    s = Scene("corpus_evolution")
    ghost = _json.loads((ROOT / "assets" / "ghost.json").read_text())
    reasoning = '"' + ghost["proposer"]["rationale"].strip() + '"'
    audit_reasoning = '"' + ghost["auditor"] + '"'
    gens = [
        ("gen 1", "PROMOTED", "gemini-1260  {'samples_per_arm': (200, 400)}",
         "beat the champion on 24 held-out worlds it never saw"),
        ("audit", "FLAGGED", "a second model reviewed the receipt",
         "accuracy fell 0.0278 to buy the efficiency — on the record, no veto"),
        ("gen 2", "REFUSED", "gained +0.0139, needed +0.02",
         "a real improvement — refused for being under the margin"),
        ("gen 3", "REFUSED", "moved to a different knob after its refusals",
         "gained +0.0056 — refusing marginal gains is what stops drift on noise"),
    ]

    def build(shown, ghost_chars=None, show_audit_ghost=False):
        img, d = s.base()
        d.text((60, 70), "4 · It improves its own method — through a gate", font=F_H, fill=INK1)
        d.text((60, 170), "Gemini proposes. It never sees the benchmark, never scores "
                          "itself, never writes to canon.", font=F_BODY, fill=INK2)
        y = 260
        y = _ghost_panel(d, y, "GEMINI · reasoning, verbatim", reasoning, ghost_chars)
        for tag, verdict, line1, line2 in shown:
            d.rectangle([80, y, W - 80, y + 128], fill=CARD, outline=LINE, width=2)
            d.text((130, y + 22), tag, font=F_MONO, fill=INK3)
            d.text((320, y + 22), verdict, font=F_MONO,
                   fill=BLUE if verdict == "PROMOTED" else ORANGE)
            d.text((640, y + 26), line1, font=F_MONO_S, fill=INK1)
            d.text((320, y + 76), line2, font=F_MONO_S, fill=INK2)
            y += 148
            if tag == "audit" and show_audit_ghost:
                y = _ghost_panel(d, y, "AUDITOR · a different model, verbatim",
                                 audit_reasoning)
        return img

    # Two acts, so nothing ever runs off screen.
    # Act 1 — the ghosts: the proposal types itself out, the gate promotes, the
    # auditor dissents in its own voice. Only the first two cards appear here.
    step = max(6, len(reasoning) // 14)
    for n in range(step, len(reasoning) + step, step):
        s.hold(build([], min(n, len(reasoning))), 0.45)
    s.hold(build([]), 1.0)
    s.hold(build(gens[:1]), 3.6)
    s.hold(build(gens[:2], show_audit_ghost=True), 6.0)

    # Act 2 — the ghosts leave; the full verdict sequence gets the room.
    def build_act2(shown):
        img, d = s.base()
        d.text((60, 70), "4 · It improves its own method — through a gate", font=F_H, fill=INK1)
        d.text((60, 170), "The verdicts, in sequence — refusing marginal gains is what "
                          "stops a system ratcheting on noise.", font=F_BODY, fill=INK2)
        y = 290
        for tag, verdict, line1, line2 in shown:
            d.rectangle([80, y, W - 80, y + 128], fill=CARD, outline=LINE, width=2)
            d.text((130, y + 22), tag, font=F_MONO, fill=INK3)
            d.text((320, y + 22), verdict, font=F_MONO,
                   fill=BLUE if verdict == "PROMOTED" else ORANGE)
            d.text((640, y + 26), line1, font=F_MONO_S, fill=INK1)
            d.text((320, y + 76), line2, font=F_MONO_S, fill=INK2)
            y += 152
        return img

    for i in range(3, len(gens) + 1):
        s.hold(build_act2(gens[:i]), 3.4)
    s.hold(build_act2(gens), 5.0)
    return s


def corpus_evidence() -> Scene:
    s = Scene("corpus_evidence")
    stats = [
        ("384", "recorded runs, frozen study"),
        ("2,560", "hypotheses tested"),
        ("1,800", "refuted by experiment"),
        ("83.9%", "of observational priors inverted on the confounded worlds"),
        ("recall 1.000 · precision 0.786", "edges vs hidden ground truth — never misses, over-claims 1 in 5"),
    ]

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "5 · Every run is evidence", font=F_H, fill=INK1)
        y = 230
        for big, small in shown:
            d.text((120, y), big, font=F_H, fill=BLUE)
            d.text((120, y + 78), small, font=F_BODY, fill=INK2)
            y += 155
        return img

    reveal(s, build, stats, 2.6, 4.0)
    s2, d2 = s.base()
    d2.text((60, 70), "5 · Every run is evidence", font=F_H, fill=INK1)
    text_block(d2, 100, 300,
               "Each record carries its seeds, strategy and code commit — enough to "
               "recompute the result, not merely read it. Regenerable by anyone, "
               "offline, without credentials. When our own axis clipped real failure "
               "cases, an independent reviewer caught it — the correction is printed "
               "on the figure.", F_BODY, INK2)
    s.hold(s2, 7.0)

    # The backend, live: the Cloud Run monitoring console for this project —
    # the checklist's own preferred form of proof, shown rather than claimed.
    s3, d3 = s.base()
    d3.text((60, 70), "5 · Every run is evidence — including this one", font=F_H, fill=INK1)
    shot = Image.open(ROOT / "assets" / "cloudrun-dashboard.png").convert("RGB")
    shot.thumbnail((1380, 700))
    s3.paste(shot, ((W - shot.width) // 2, 190))
    d3 = ImageDraw.Draw(s3)
    d3.text((W // 2, 190 + shot.height + 26),
            "Cloud Run monitoring · project meta-science · europe-west1 · 0% errors",
            font=F_MONO, fill=INK2, anchor="ma")
    s.hold(s3, 6.0)
    return s


def corpus_stats() -> Scene:
    """Charts, not tables: the same encodings as the deployed evidence page — a strip
    plot where the finding is the variance, sorted bars for the ranking."""
    import json as _json
    s = Scene("corpus_stats")
    acc = _json.loads((ROOT / "assets" / "acc_values.json").read_text())
    ref_rows = []
    for line in (ROOT / "assets" / "stats_templates.txt").read_text().splitlines():
        tid, frac, pct = line.split()
        ref_rows.append((tid, frac, float(pct.rstrip("%"))))

    ARMS = [("champion", "champion 400×1", INK1),
            ("frugal-100", "frugal 100×1", INK1),
            ("lean-25", "lean 25×1", ORANGE),
            ("paired-lean-25", "paired lean 25", BLUE)]

    def strip_plot(d, x0, y0, w, h):
        d.text((x0, y0 - 40), "held-out accuracy per world — every dot is one of 48 worlds",
               font=F_FOOT, fill=INK3)
        lo, hi = 0.30, 1.02
        px = lambda v: x0 + 170 + (v - lo) / (hi - lo) * (w - 260)
        for gx in (0.4, 0.6, 0.8, 1.0):
            d.line([px(gx), y0, px(gx), y0 + h], fill=LINE, width=1)
            d.text((px(gx), y0 + h + 10), f"{gx:.1f}", font=F_FOOT, fill=INK3, anchor="ma")
        row_h = h / len(ARMS)
        for i, (key, label, color) in enumerate(ARMS):
            cy = y0 + row_h * i + row_h / 2
            d.text((x0 + 150, cy), label, font=F_FOOT, fill=color, anchor="rm")
            vals = acc[key]
            for j, v in enumerate(vals):
                jit = ((j * 2654435761 % 97) / 97 - 0.5) * (row_h * 0.55)
                x, yy = px(v), cy + jit
                d.ellipse([x - 6, yy - 6, x + 6, yy + 6], fill=color + (140,))
            m = sum(vals) / len(vals)
            d.line([px(m), cy - row_h * 0.42, px(m), cy + row_h * 0.42],
                   fill=INK1, width=4)
            d.text((x0 + w - 60, cy), f"{m:.3f}", font=F_MONO_S, fill=INK1, anchor="lm")

    def bar_chart(d, x0, y0, w):
        d.text((x0, y0 - 40), "hypotheses refuted by experiment, per world topology",
               font=F_FOOT, fill=INK3)
        bh, gap = 33, 9
        for i, (tid, frac, pct) in enumerate(ref_rows):
            yy = y0 + i * (bh + gap)
            hot = tid in ("T5", "T6")
            d.text((x0 + 60, yy + bh / 2), tid, font=F_MONO_S,
                   fill=ORANGE if hot else INK2, anchor="rm")
            bw = (w - 320) * pct / 100
            d.rounded_rectangle([x0 + 80, yy, x0 + 80 + bw, yy + bh], radius=6,
                                fill=ORANGE if hot else CARD,
                                outline=None if hot else LINE, width=2)
            d.text((x0 + 95 + bw, yy + bh / 2), f"{pct:.1f}%   {frac}",
                   font=F_MONO_S, fill=INK1, anchor="lm")

    def build(stage):
        img, d0 = s.base()
        img_rgba = img.convert("RGBA")
        from PIL import ImageDraw as _ID
        d = _ID.Draw(img_rgba, "RGBA")
        d.text((60, 70), "6 · The statistics, not the anecdote", font=F_H, fill=INK1)
        strip_plot(d, 100, 220, W - 220, 350)
        if stage >= 2:
            bar_chart(d, 100, 690, W - 220)
        if stage >= 3:
            d.text((100, H - 116),
                   "Cutting to 25 samples quadruples the spread (orange scatter); its "
                   "paired twin hides it entirely. T5/T6 refute nearly everything — by design.",
                   font=F_FOOT, fill=INK2)
        return img_rgba.convert("RGB")

    for stage, dur in ((1, 7.0), (2, 6.5), (3, 6.0)):
        s.hold(build(stage), dur)
    return s


def corpus_replication() -> Scene:
    s = Scene("corpus_replication")

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "7 · We asked it whether science needs repetition", font=F_H, fill=INK1)
        y = 220
        for kind, line in shown:
            if kind == "mono":
                d.rectangle([80, y - 15, W - 80, y + 130], fill=CARD, outline=LINE, width=2)
                d.text((130, y + 10), "champion 400×1          acc 0.9815   score +0.8704", font=F_MONO, fill=INK1)
                d.text((130, y + 70), "replicated 80×5         acc 0.9815   score +0.8704", font=F_MONO, fill=BLUE)
                y += 170
            else:
                y = text_block(d, 100, y, line, F_BODY, INK2 if kind == "d" else INK1) + 18
        return img

    items = [
        ("h", "Replication is now a knob the evolver itself can tune — charged, never free."),
        ("mono", ""),
        ("d", "The gate's answer: at equal budget, cost-neutral — exactly what statistics "
              "predicts under iid noise. Replication earns its keep against what these "
              "worlds don't yet contain: heavy tails, outlier seeds, drift."),
        ("h", "A benchmark that tells you which world would change its answer."),
    ]
    reveal(s, build, items, 3.4, 5.5)
    return s


# ── outro ────────────────────────────────────────────────────────────────────

def outro() -> Scene:
    """Timed against the measured narration, not by eye. Relative to this clip:
    0.0s "One gated turn today ... show a receipt", 11.8s "One more thing.",
    13.6s the reveal, 25.4s "Free for everyone — human, or A.I."

    The concat demuxer repeats the final still, so the last frame plays for twice
    its hold: 2.3 here gives the 4.6s the closing card actually needs.
    """
    s = Scene("outro")
    img, d = s.base()
    d.text((60, 70), "Built on", font=F_H, fill=INK1)
    y = 210
    for line in ["Gemini 3.6-flash + 3.5-flash-lite auditor  ·  Google GenAI SDK",
                 "Firestore ledger  ·  Cloud Run  ·  Terraform",
                 "live on Cloud Run:  metascience-o6a5u2jdvq-ew.a.run.app",
                 "78 tests  ·  every published figure pinned to code"]:
        d.text((100, y), line, font=F_BODY, fill=INK2)
        y += 75
    text_block(d, 100, y + 40,
               "Not the first AI scientist, and it does not claim to be. The claim is "
               "narrower and checkable: falsifiable self-improvement — every promotion "
               "earned against evidence the proposer cannot see, score, or tune against, "
               "with a receipt either way.", F_BODY, INK1)
    s.hold(img, 4.4)

    img, d = s.base()
    d.text((W // 2, 380), "Today it does one gated turn.", font=F_H, fill=INK1, anchor="ma")
    d.text((W // 2, 490), "The architecture exists so that a thousand turns", font=F_H, fill=BLUE, anchor="ma")
    d.text((W // 2, 580), "would still be falsifiable.", font=F_H, fill=BLUE, anchor="ma")
    # The memorable link last; the .run URL keeps its place on the "Built on"
    # frame, where it serves as backend proof rather than a call to action.
    d.text((W // 2, 740), "science.meta-agentic.ai", font=F_MONO, fill=BLUE, anchor="ma")
    d.text((W // 2, 810), "github.com/meta-agentic/meta-science", font=F_MONO, fill=INK2, anchor="ma")
    s.hold(img, 7.4)

    # The reveal, landing with the voice that makes it true.
    img, d = s.base()
    d.text((W // 2, 400), "One more thing.", font=F_H, fill=INK2, anchor="ma")
    s.hold(img, 1.8)

    img, d = s.base()
    # "is" joins the line above so the reveal word stands alone, and the screen
    # says nothing more — the narrator is already saying it.
    d.text((W // 2, 330), "One more thing.", font=F_H, fill=INK2, anchor="ma")
    d.text((W // 2, 470), "The voice you've been listening to is", font=F_H, fill=INK1, anchor="ma")
    d.text((W // 2, 570), "Gemini.", font=F_TITLE, fill=BLUE, anchor="ma")
    s.hold(img, 11.8)

    img, d = s.base()
    d.text((W // 2, 400), "meta-science", font=F_TITLE, fill=INK1, anchor="ma")
    d.text((W // 2, 545), "free for everyone", font=F_H, fill=INK2, anchor="ma")
    d.text((W // 2, 635), "human or AI", font=F_H, fill=BLUE, anchor="ma")
    s.hold(img, 2.3)
    return s


CLIPS = [intro, axioms, corpus_world, corpus_trap, corpus_refutation,
         corpus_evolution, corpus_evidence, corpus_stats, corpus_replication, outro]


def main() -> None:
    wanted = set(sys.argv[1:])
    OUT.mkdir(exist_ok=True)
    paths = []
    for fn in CLIPS:
        if wanted and fn.__name__ not in wanted:
            existing = OUT / f"{fn.__name__}.mp4"
            if existing.exists():
                paths.append(existing)
            continue
        paths.append(fn().render())
    if not wanted:
        listfile = OUT / "final_list.txt"
        listfile.write_text("".join(f"file '{p.name}'\n" for p in paths))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", str(listfile), "-c", "copy",
                        str(OUT / "final.mp4")], check=True)
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "csv=p=0",
                                str(OUT / "final.mp4")], capture_output=True, text=True)
        print(f"final.mp4  ·  {float(probe.stdout):.0f}s")


if __name__ == "__main__":
    main()
