"""Re-segment an existing SRT into readable cues, without touching the audio.

The renderer emits one cue per clip, which is correct in time and unreadable on
screen: a single 126-character line held for twelve seconds. This re-splits each
cue using the same `cues()` function the renderer now uses, so a subtitle file
can be fixed without re-synthesising narration or re-muxing video.

The split is safe by construction: every original cue's start and end are kept
exactly, and only its interior is subdivided, so an estimated boundary can never
push text outside the clip it belongs to. The re-segmentation is also asserted
lossless — the words that come out are the words that went in.

    python3 scripts/resplit_srt.py video/final/final.srt
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "video"))

from narrate import MAX_LINE, cues, ts  # noqa: E402

TIME = re.compile(r"(\d+):(\d\d):(\d\d),(\d+)\s*-->\s*(\d+):(\d\d):(\d\d),(\d+)")


def seconds(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse(text: str):
    for block in [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]:
        lines = block.strip().splitlines()
        m = TIME.search(lines[1] if len(lines) > 1 else "")
        if not m:
            continue
        g = m.groups()
        # Line breaks are meaningful in a cue, so they survive the round trip;
        # the lossless check normalises whitespace itself.
        yield (seconds(*g[:4]), seconds(*g[4:]),
               "\n".join(l.rstrip() for l in lines[2:]).strip())


def words(text: str) -> list[str]:
    return re.sub(r"\s+", " ", text).split()


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "video/final/final.srt")
    original = list(parse(path.read_text()))

    out, idx = [], 1
    for start, end, text in original:
        for c_start, c_end, c_text in cues(" ".join(text.split()), start, end):
            out.append(f"{idx}\n{ts(c_start)} --> {ts(c_end)}\n{c_text}\n")
            idx += 1

    rebuilt = "\n".join(out)

    # Nothing may be lost, reordered, or overlapped.
    assert words(" ".join(t for _, _, t in original)) == \
        words(" ".join(t for _, _, t in parse(rebuilt))), "text changed"
    last = -1.0
    for s, e, t in parse(rebuilt):
        assert s >= last - 1e-6, f"cue starts before the previous ends at {s}"
        assert e > s, f"non-positive duration at {s}"
        for line in t.splitlines():
            assert len(line) <= MAX_LINE, f"line too long ({len(line)}): {line}"
        assert len(t.splitlines()) <= 2, f"more than two lines: {t}"
        last = e

    path.write_text(rebuilt)
    lens = [len(l) for _, _, t in parse(rebuilt) for l in t.splitlines()]
    print(f"{len(original)} cues -> {idx - 1}; longest line {max(lens)} chars; "
          f"checks passed")


if __name__ == "__main__":
    main()
