#!/usr/bin/env bash
# Morning finalizer: synthesize the last narration lines once TTS quota resets,
# with retries, and refuse to publish anything mixed-voice.
#
# narrate.py caches per clip — only clips whose .voice marker is not "gemini" are
# re-synthesized, so retries are cheap and cannot burn quota on finished audio.
set -uo pipefail
cd "$(dirname "$0")/.."

EXPECTED=10   # intro, axioms, six corpus scenes, stats, outro — one .voice each

for attempt in 1 2 3; do
  echo "=== attempt $attempt/3 ==="
  python3 video/narrate.py 2>&1 | grep -vE "^Direct use|AFC"
  done_count=$(grep -l '^gemini$' video/out/captions/*.voice 2>/dev/null | wc -l | tr -d ' ')
  echo "gemini-voiced: $done_count/$EXPECTED"
  if [ "$done_count" -eq "$EXPECTED" ]; then
    cp video/out/final_narrated.mp4 video/final/meta-science-submission.mp4
    cp video/out/final.mp4 video/final/meta-science-silent.mp4
    cp video/out/final.srt video/final/
    git add video/final && git commit -q -m "Final narrated render: every clip in Gemini's voice" \
      && git push origin main 2>&1 | tail -1
    echo "FINALIZED OK"
    exit 0
  fi
  [ "$attempt" -lt 3 ] && { echo "waiting 180s before retry"; sleep 180; }
done
echo "FINALIZE FAILED after 3 attempts — do NOT publish a mixed-voice render"
exit 1
