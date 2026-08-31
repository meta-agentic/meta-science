#!/usr/bin/env python3
"""Narration for the video, as components.

Emits per-clip caption text (video/out/captions/<clip>.txt) — the script for any
TTS or human read — plus a timed final.srt, per-clip AIFF via macOS `say`, and a
muxed final_narrated.mp4. Speech rate is fitted per clip so the narration lands
inside the clip's own duration.
"""
import re
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

OUT = Path(__file__).resolve().parent / "out"
CAP = OUT / "captions"

# Gemini's own TTS narrates the system's own demo — and when the API is not
# reachable, macOS `say` keeps the build reproducible offline.
# Model cascade: the 3.1 preview has the fresher quota today; 2.5 is the fallback.
TTS_MODELS = ("gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts")
TTS_VOICE = "Kore"          # female, firm — documentary register
STYLE = ("Read as a calm, confident documentary narrator. Measured pace, "
         "no hype, slight warmth: ")


def synthesize(text: str, out_wav: Path, clip_dur: float) -> None:
    # Cache per clip: a .voice marker records which engine produced the wav, so a
    # rerun only re-synthesizes clips that are missing or fell back — the free-tier
    # TTS quota is small, and burning it on already-good audio is how a mixed-voice
    # video happens.
    marker = out_wav.with_suffix(".voice")
    if out_wav.exists() and marker.exists() and marker.read_text() == "gemini":
        return
    import time
    last = None
    for attempt in range(4):
        try:
            _gemini_tts(text, out_wav)
            marker.write_text("gemini")
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            if "429" in str(exc) and attempt < 3:
                print(f"    quota — waiting 35s (attempt {attempt + 1}/4)")
                time.sleep(35)
            else:
                break
    else:
        pass
    if not marker.exists() or marker.read_text() != "gemini":
        print(f"    gemini tts unavailable ({str(last)[:60]}) — falling back to say")
        subprocess.run(["say", "-v", "Samantha", "-o", str(out_wav.with_suffix(".aiff")),
                        text], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-i", str(out_wav.with_suffix(".aiff")), str(out_wav)], check=True)
        marker.write_text("say")
    _fit(out_wav, clip_dur)


def _gemini_tts(text: str, out_wav: Path) -> None:
    if True:
        from metascience.config import api_key, load_env
        load_env(Path(__file__).resolve().parents[1] / ".env")
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key())
        last = None
        for model in TTS_MODELS:
            try:
                r = client.models.generate_content(
                    model=model,
                    contents=STYLE + text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=TTS_VOICE)))))
                break
            except Exception as exc:  # noqa: BLE001
                last = exc
        else:
            raise last
        pcm = r.candidates[0].content.parts[0].inline_data.data
        with wave.open(str(out_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)


def _fit(out_wav: Path, clip_dur: float) -> None:
    # If the read runs longer than the clip, speed it gently rather than truncate.
    adur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(out_wav)], capture_output=True, text=True).stdout)
    if adur > clip_dur - 0.3:
        factor = min(1.3, adur / (clip_dur - 0.3))
        fitted = out_wav.with_name(out_wav.stem + "_fit.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_wav),
                        "-af", f"atempo={factor:.3f}", str(fitted)], check=True)
        fitted.replace(out_wav)

NARRATION = {
    # Written to COMPLEMENT the slides, not read them: the screen carries the
    # specifics; the voice carries the frame and the stakes.
    "intro":
        "What would it take to trust a machine that says it made itself better? "
        "Not a bigger claim — a smaller one, that can be checked.",
    "axioms":
        "Every science begins with what it refuses to assume. No agent judges "
        "its own claims — derivation is not truth. Seeing is not doing — the two "
        "coincide only when confounding is absent, which is exactly what may "
        "never be assumed. And improvement only counts when it is proven, on "
        "worlds the prover cannot see. The rest is engineering.",
    "corpus_world":
        "Start by taking everything away. No names, no context, no textbook to "
        "remember. What is left is the only thing that cannot be faked: the "
        "ability to find out.",
    "corpus_trap":
        "Data can be perfectly clear, and perfectly wrong. The only way past a "
        "hidden cause is to reach into the world and move something. Reading "
        "alone fails every time. Acting succeeds every time.",
    "corpus_refutation":
        "Real science cuts both ways. Some guesses survive their experiment, "
        "some die by it — and the machine finds out which, the hard way. It "
        "wrote its predictions down first, so there is no taking them back.",
    "corpus_evolution":
        "And here is the ghost in the shell — the model thinking about its own "
        "method, in its own words. Its idea was good, so it passed. Its next "
        "two ideas were also good. Not good enough. That is the whole point.",
    "corpus_evidence":
        "None of this rests on a lucky run. Hundreds of worlds, thousands of "
        "tests — and any of them can be re-run by anyone, from a single seed.",
    "corpus_stats":
        "Spend a quarter of the budget: same answers. Spend even less, and the "
        "spread gives you away — unless the benchmark is rigged to hide it. "
        "Ours was, once. We found it, fixed it, and published both.",
    "corpus_replication":
        "In the end we asked the system the oldest question in science: do you "
        "need repetition? It gave the statistician's answer — not here, not yet "
        "— and told us exactly what kind of world would change its mind.",
    "outro":
        "One gated turn today. A thousand tomorrow — and every one of them would "
        "still have to show a receipt. ... One more thing. The voice you have "
        "been listening to... is Gemini. The system just narrated its own demo. "
        "Meta-science. Free for everyone — human, or A.I.",
}


def dur(p: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def ts(sec: float) -> str:
    h, m = divmod(int(sec), 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{int((sec % 1) * 1000):03d}"


# Subtitle segmentation. The TTS gives no word-level timings, so a cue's interior
# splits are estimated by character count — but the cue's OUTER boundaries come from
# the measured audio, and splitting only inside them means an estimate can never
# drift past the clip it belongs to. Broadcast shape: <=42 chars a line, two lines.
MAX_LINE = 42
MAX_CUE = MAX_LINE * 2
MIN_CUE_SEC = 1.0


def _chunk(text: str, max_chars: int = MAX_CUE) -> list[str]:
    """Sentence boundaries first, then clauses, then words — never mid-word."""
    out: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if not sentence:
            continue
        if len(sentence) <= max_chars:
            out.append(sentence)
            continue
        buf = ""
        for seg in re.split(r"(?<=[,;:—])\s+", sentence):
            if buf and len(buf) + 1 + len(seg) > max_chars:
                out.append(buf)
                buf = seg
            else:
                buf = f"{buf} {seg}".strip()
        if buf:
            out.append(buf)

    hard: list[str] = []
    for c in out:
        while len(c) > max_chars:
            cut = c.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            hard.append(c[:cut].strip())
            c = c[cut:].strip()
        if c:
            hard.append(c)

    # A stray fragment ("...") reads as a flicker; fold it back if it fits.
    merged: list[str] = []
    for c in hard:
        if merged and len(c) < 20 and len(merged[-1]) + 1 + len(c) <= max_chars:
            merged[-1] = f"{merged[-1]} {c}"
        else:
            merged.append(c)
    return merged


def _wrap(text: str) -> str | None:
    """Two balanced lines, or None when no break leaves both within MAX_LINE.

    Choosing the space nearest the middle is not enough: it can leave one side
    a character over the limit. Only breaks where BOTH sides fit are eligible,
    and the most balanced of those wins.
    """
    if len(text) <= MAX_LINE:
        return text
    best = None
    for i, ch in enumerate(text):
        if ch != " ":
            continue
        left, right = i, len(text) - i - 1
        if left <= MAX_LINE and right <= MAX_LINE:
            balance = abs(left - right)
            if best is None or balance < best[0]:
                best = (balance, i)
    if best is None:
        return None
    cut = best[1]
    return text[:cut] + "\n" + text[cut + 1:]


def cues(text: str, start: float, end: float) -> list[tuple[float, float, str]]:
    """Re-segment one spoken line across its measured window.

    Time is apportioned by character count, which tracks speech duration closely
    at a steady TTS pace. The first cue starts exactly at `start` and the last
    ends exactly at `end`, so the clip's own timing is preserved exactly.
    """
    parts = []
    for part in _chunk(text):
        # A part no two-line break can hold is re-cut to single-line pieces.
        parts.extend([part] if _wrap(part) else _chunk(part, MAX_LINE))
    if len(parts) < 2:
        return [(start, end, _wrap(parts[0]) or parts[0])]
    total = sum(len(p) for p in parts)
    span = end - start
    out, t = [], start
    for i, part in enumerate(parts):
        stop = end if i == len(parts) - 1 else t + span * len(part) / total
        if stop - t < MIN_CUE_SEC:
            stop = min(t + MIN_CUE_SEC, end)
        out.append((t, stop, _wrap(part) or part))
        t = stop
    return out


def main() -> None:
    CAP.mkdir(exist_ok=True)
    t0, srt, idx, narrated = 0.0, [], 1, []
    for name, text in NARRATION.items():
        clip = OUT / f"{name}.mp4"
        d = dur(clip)
        (CAP / f"{name}.txt").write_text(text + "\n")

        aiff = CAP / f"{name}.wav"
        synthesize(text, aiff, d)
        # Awkward-pause control: a clip may outlast its narration by the trailing
        # static hold. Trim at most that hold (bounded at 6s) so the voice never
        # dies into dead air — but never cut into mid-scene reveals, and always
        # leave breathing room to read. A 0.4s delay keeps the voice from slamming
        # in on the first frame.
        adur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(aiff)], capture_output=True, text=True).stdout)
        target = max(adur + 2.6, d - 6.0)
        target = min(d, target)
        merged = CAP / f"{name}_narrated.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-i", str(aiff),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-af", "adelay=400|400,apad", "-t", f"{target:.3f}", str(merged)],
            check=True)
        narrated.append(merged)

        for c_start, c_end, c_text in cues(text, t0 + 0.4, t0 + target - 0.2):
            srt.append(f"{idx}\n{ts(c_start)} --> {ts(c_end)}\n{c_text}\n")
            idx += 1
        t0 += target
        print(f"  {name:22s} clip {d:5.1f}s -> {target:5.1f}s (voice {adur:4.1f}s)")

    (OUT / "final.srt").write_text("\n".join(srt))
    listfile = OUT / "narrated_list.txt"
    listfile.write_text("".join(f"file 'captions/{p.name}'\n" for p in narrated))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listfile), "-c", "copy", str(OUT / "final_narrated.mp4")],
                   check=True)
    print(f"final.srt + final_narrated.mp4 ({dur(OUT / 'final_narrated.mp4'):.0f}s)")


if __name__ == "__main__":
    main()
