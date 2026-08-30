#!/usr/bin/env python3
"""Narration for the video, as components.

Emits per-clip caption text (video/out/captions/<clip>.txt) — the script for any
TTS or human read — plus a timed final.srt, per-clip AIFF via macOS `say`, and a
muxed final_narrated.mp4. Speech rate is fitted per clip so the narration lands
inside the clip's own duration.
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
CAP = OUT / "captions"
VOICE = "Samantha"

NARRATION = {
    "intro":
        "Meta-science. Every self-improvement demo shows you successes — but a system "
        "that reports it improved is indistinguishable from one that just logs the word. "
        "So we built the one that can refuse itself.",
    "corpus_world":
        "The agent is given almost nothing. Opaque labels, and two moves: observe, or "
        "intervene. The worlds come from real science, then every recognisable surface "
        "is stripped — so the model cannot recite a law from memory. It must discover, "
        "because it cannot retrieve.",
    "corpus_trap":
        "Here is the trap. The correlation is strong, clean — and wrong. A hidden common "
        "cause dominates the data. Reading only observations, Gemini gets zero of four "
        "confounded worlds right. Allowed to intervene, the same loop gets four of four. "
        "The only difference is the ability to act.",
    "corpus_refutation":
        "Science confirms and refutes. In an ordinary world, the agent's predictions are "
        "supported one way and refuted the other — directionality, discovered. In the "
        "confounded world, its best hypothesis dies. Every prediction is committed before "
        "the experiment runs; the verdict is a comparison, never an opinion.",
    "corpus_evolution":
        "Now one level up — and here is the ghost in the shell: Gemini's own reasoning, "
        "verbatim, as it proposes a change to its own method. The gate promoted it. An "
        "independent auditor flagged the trade-off, on the record. The next two proposals "
        "were refused — real improvements, under the margin. Refusing marginal gains is "
        "what stops a system ratcheting on noise.",
    "corpus_evidence":
        "None of this is an anecdote. Three hundred eighty-four recorded runs, two and a "
        "half thousand hypotheses, and every record carries its seeds, strategy and code "
        "commit — enough to recompute the result, not merely to read it.",
    "corpus_stats":
        "The statistics hold up. Cutting measurement fourfold keeps the same accuracy — "
        "but cut to twenty-five samples and the variance quadruples, unless the arms "
        "share noise, in which case the metric measures nothing. And the confounded "
        "topologies refute nearly everything, by design. We report both.",
    "corpus_replication":
        "Finally we asked the system itself whether science needs repetition. Replication "
        "is now a knob its own evolver can tune — charged, never free. Its answer: at "
        "equal budget, cost neutral under clean noise — and it told us exactly which "
        "kind of world would change that answer.",
    "outro":
        "Built on Gemini, the Gen AI SDK, Firestore and Cloud Run. Not the first AI "
        "scientist — the claim is narrower, and checkable: falsifiable self-improvement, "
        "with a receipt either way. Today it does one gated turn. The architecture "
        "exists so that a thousand turns would still be falsifiable.",
}


def dur(p: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def ts(sec: float) -> str:
    h, m = divmod(int(sec), 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{int((sec % 1) * 1000):03d}"


def main() -> None:
    CAP.mkdir(exist_ok=True)
    t0, srt, idx, narrated = 0.0, [], 1, []
    for name, text in NARRATION.items():
        clip = OUT / f"{name}.mp4"
        d = dur(clip)
        (CAP / f"{name}.txt").write_text(text + "\n")

        words = len(text.split())
        rate = max(150, min(215, int(words / max(d - 1.0, 1) * 60)))
        aiff = CAP / f"{name}.aiff"
        subprocess.run(["say", "-v", VOICE, "-r", str(rate), "-o", str(aiff), text],
                       check=True)
        merged = CAP / f"{name}_narrated.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-i", str(aiff),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-af", "apad", "-t", f"{d:.3f}", str(merged)], check=True)
        narrated.append(merged)

        srt.append(f"{idx}\n{ts(t0 + 0.3)} --> {ts(t0 + d - 0.2)}\n{text}\n")
        idx += 1
        t0 += d
        print(f"  {name:22s} clip {d:5.1f}s  rate {rate} wpm")

    (OUT / "final.srt").write_text("\n".join(srt))
    listfile = OUT / "narrated_list.txt"
    listfile.write_text("".join(f"file 'captions/{p.name}'\n" for p in narrated))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listfile), "-c", "copy", str(OUT / "final_narrated.mp4")],
                   check=True)
    print(f"final.srt + final_narrated.mp4 ({dur(OUT / 'final_narrated.mp4'):.0f}s)")


if __name__ == "__main__":
    main()
