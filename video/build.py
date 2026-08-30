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


def corpus_refutation() -> Scene:
    s = Scene("corpus_refutation")
    demo = (ROOT / "assets" / "demo.txt").read_text().splitlines()
    exp = [l for l in demo if "predicted" in l and "measured" in l]

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "3 · Refuted by its own experiment", font=F_H, fill=INK1)
        y = 230
        d.rectangle([80, y - 30, W - 80, y + 90 + 62 * len(exp)], fill=CARD,
                    outline=LINE, width=2)
        d.text((120, y), "$ python3 demo.py", font=F_MONO, fill=INK3)
        y += 80
        for line in exp:
            verdict = "REFUTED" if "REFUTED" in line else "SUPPORTED"
            body = line.strip().replace("REFUTED", "").replace("SUPPORTED", "").rstrip()
            d.text((120, y), body, font=F_MONO, fill=INK1)
            d.text((W - 140, y), verdict, font=F_MONO,
                   fill=ORANGE if verdict == "REFUTED" else BLUE, anchor="ra")
            y += 62
        y += 40
        for kind, line in shown:
            y = text_block(d, 100, y, line, F_BODY, INK2 if kind == "d" else INK1) + 16
        return img

    items = [
        ("h", "The prediction is committed BEFORE the experiment runs."),
        ("d", "The verdict is a comparison, never a question put to the model — "
              "a hypothesis recorded after the result would just be a description."),
    ]
    reveal(s, build, items, 3.2, 5.0)
    return s


def corpus_evolution() -> Scene:
    s = Scene("corpus_evolution")
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

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "4 · It improves its own method — through a gate", font=F_H, fill=INK1)
        d.text((60, 170), "Gemini proposes. It never sees the benchmark, never scores "
                          "itself, never writes to canon.", font=F_BODY, fill=INK2)
        y = 290
        for tag, verdict, line1, line2 in shown:
            d.rectangle([80, y, W - 80, y + 150], fill=CARD, outline=LINE, width=2)
            d.text((130, y + 28), tag, font=F_MONO, fill=INK3)
            d.text((320, y + 28), verdict, font=F_MONO,
                   fill=BLUE if verdict == "PROMOTED" else ORANGE)
            d.text((620, y + 28), line1, font=F_MONO_S, fill=INK1)
            d.text((320, y + 88), line2, font=F_MONO_S, fill=INK2)
            y += 175
        return img

    reveal(s, build, gens, 4.0, 5.0)
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
    return s


def corpus_replication() -> Scene:
    s = Scene("corpus_replication")

    def build(shown):
        img, d = s.base()
        d.text((60, 70), "6 · We asked it whether science needs repetition", font=F_H, fill=INK1)
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
    s = Scene("outro")
    img, d = s.base()
    d.text((60, 70), "Built on", font=F_H, fill=INK1)
    y = 210
    for line in ["Gemini 3.6-flash + 3.5-flash-lite auditor  ·  Google GenAI SDK",
                 "Firestore ledger  ·  Cloud Run  ·  Terraform",
                 "71 tests  ·  62 commits  ·  every figure pinned to code"]:
        d.text((100, y), line, font=F_BODY, fill=INK2)
        y += 75
    text_block(d, 100, y + 40,
               "Not the first AI scientist, and it does not claim to be. The claim is "
               "narrower and checkable: falsifiable self-improvement — every promotion "
               "earned against evidence the proposer cannot see, score, or tune against, "
               "with a receipt either way.", F_BODY, INK1)
    s.hold(img, 8.0)
    img, d = s.base()
    d.text((W // 2, 380), "Today it does one gated turn.", font=F_H, fill=INK1, anchor="ma")
    d.text((W // 2, 490), "The architecture exists so that a thousand turns", font=F_H, fill=BLUE, anchor="ma")
    d.text((W // 2, 580), "would still be falsifiable.", font=F_H, fill=BLUE, anchor="ma")
    d.text((W // 2, 760), "github.com/meta-agentic/meta-science", font=F_MONO, fill=INK2, anchor="ma")
    s.hold(img, 6.5)
    return s


CLIPS = [intro, corpus_world, corpus_trap, corpus_refutation,
         corpus_evolution, corpus_evidence, corpus_replication, outro]


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
