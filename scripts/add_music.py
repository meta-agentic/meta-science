"""Lay a music bed under the narrated cut, without re-rendering a frame.

The video stream is copied verbatim — only the audio is rebuilt — so the
picture that was verified stays bit-identical and this can be run, judged,
and reverted in seconds.

    python3 scripts/add_music.py --intro intro.wav --outro outro.wav

Mix discipline: the narration is the subject and the music is the room. The
bed sits ~20 dB under the voice, fades in from silence, and ducks further
wherever the voice is actually speaking (a real sidechain compressor, keyed
off the narration track — not a static level that fights the words).
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "video" / "final" / "meta-science-submission.mp4"


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


ap = argparse.ArgumentParser()
ap.add_argument("--intro", type=Path, help="opening sting, played from 0s")
ap.add_argument("--outro", type=Path, help="closing bed, aligned to the end")
ap.add_argument("--source", type=Path, default=SRC)
ap.add_argument("--out", type=Path,
                default=ROOT / "video" / "out" / "final_scored.mp4")
ap.add_argument("--bed-db", type=float, default=-20.0,
                help="music level under the voice, in dB")
ap.add_argument("--tail", type=float, default=1.5,
                help="seconds of music fade at each edge")
args = ap.parse_args()

if not args.intro and not args.outro:
    sys.exit("nothing to add: pass --intro and/or --outro")

total = duration(args.source)
inputs, filters, beds = ["-i", str(args.source)], [], []
idx = 1

if args.intro:
    d = duration(args.intro)
    inputs += ["-i", str(args.intro)]
    filters.append(
        f"[{idx}:a]afade=t=in:st=0:d=0.4,"
        f"afade=t=out:st={max(0.0, d - args.tail):.2f}:d={args.tail},"
        f"volume={args.bed_db}dB[m{idx}]")
    beds.append(f"[m{idx}]")
    idx += 1

if args.outro:
    d = duration(args.outro)
    start = max(0.0, total - d)
    inputs += ["-i", str(args.outro)]
    filters.append(
        f"[{idx}:a]afade=t=in:st=0:d={args.tail},"
        f"afade=t=out:st={max(0.0, d - 2.0):.2f}:d=2.0,"
        f"adelay={int(start * 1000)}|{int(start * 1000)},"
        f"volume={args.bed_db}dB[m{idx}]")
    beds.append(f"[m{idx}]")
    idx += 1

# One bed, then duck it against the voice: the narration is the sidechain key,
# so the music retreats only while words are actually being spoken.
filters.append(f"{''.join(beds)}amix=inputs={len(beds)}:normalize=0[bed]")
filters.append("[0:a]asplit=2[voice][key]")
filters.append("[bed][key]sidechaincompress=threshold=0.03:ratio=6:"
               "attack=15:release=420[ducked]")
filters.append("[voice][ducked]amix=inputs=2:normalize=0,"
               "alimiter=limit=0.95[out]")

cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs,
       "-filter_complex", ";".join(filters),
       "-map", "0:v", "-c:v", "copy",
       "-map", "[out]", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", str(args.out)]
subprocess.run(cmd, check=True)

print(f"{args.out}  ({duration(args.out):.1f}s, video stream copied)")
