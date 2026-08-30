#!/usr/bin/env python3
"""
generate_voiceover.py — Reads script.json (from generate_script.py) and
produces a single narration.mp3 covering all sections, plus a matching
captions.srt, using Microsoft Edge's free TTS engine (no API key needed).

Setup:
  pip install edge-tts

Default voice is hi-IN-MadhurNeural (deep male Hindi) at a slightly slower
rate, for a natural documentary-narrator feel. Other good documentary-style
options:
  hi-IN-SwaraNeural    - Hindi, female
  en-US-GuyNeural       - English, male
  en-US-AriaNeural      - English, female

List all available voices:
  edge-tts --list-voices | grep hi-IN

Usage:
    python3 generate_voiceover.py --script script.json \
        --output-audio narration.mp3 --output-srt captions.srt

    # Faster/slower pace, or a different voice:
    python3 generate_voiceover.py --voice hi-IN-SwaraNeural --rate "-5%"
"""

import argparse
import asyncio
import json
from pathlib import Path

import edge_tts


def srt_timestamp(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def synthesize(text, voice, audio_out, rate="-10%"):
    # A slightly reduced rate reads as more measured and documentary-like
    # than the default TTS pace.
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    word_boundaries = []
    with open(audio_out, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append(chunk)
    return word_boundaries


def build_srt(sections, word_boundaries, srt_out, words_per_caption=10):
    """Groups word-level timing into short caption blocks."""
    lines = []
    idx = 1
    buf_words = []
    buf_start = None

    for wb in word_boundaries:
        start = wb["offset"] / 10_000_000  # 100-ns units -> seconds
        end = start + wb["duration"] / 10_000_000
        if buf_start is None:
            buf_start = start
        buf_words.append(wb["text"])
        if len(buf_words) >= words_per_caption:
            lines.append(f"{idx}\n{srt_timestamp(buf_start)} --> {srt_timestamp(end)}\n{' '.join(buf_words)}\n")
            idx += 1
            buf_words = []
            buf_start = None

    if buf_words:
        lines.append(f"{idx}\n{srt_timestamp(buf_start)} --> {srt_timestamp(end)}\n{' '.join(buf_words)}\n")

    Path(srt_out).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="script.json")
    ap.add_argument("--voice", default="hi-IN-MadhurNeural",
                     help="e.g. hi-IN-MadhurNeural, hi-IN-SwaraNeural, en-US-GuyNeural — run 'edge-tts --list-voices' for full list")
    ap.add_argument("--rate", default="-10%", help="Speaking rate adjustment, e.g. -10%%, +5%%")
    ap.add_argument("--output-audio", default="narration.mp3")
    ap.add_argument("--output-srt", default="captions.srt")
    args = ap.parse_args()

    data = json.loads(Path(args.script).read_text())
    full_text = " ".join(s["text"] for s in data["sections"])

    word_boundaries = asyncio.run(synthesize(full_text, args.voice, args.output_audio, args.rate))
    build_srt(data["sections"], word_boundaries, args.output_srt)

    print(f"Voiceover saved: {args.output_audio}")
    print(f"Captions saved: {args.output_srt}")


if __name__ == "__main__":
    main()
