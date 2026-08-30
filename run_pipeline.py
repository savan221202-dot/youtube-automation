#!/usr/bin/env python3
"""
run_pipeline.py — The single entry point for the automated agent.
Runs, in order:
  1. generate_script.py     -> script.json
  2. generate_voiceover.py  -> narration.mp3 + captions.srt
  3. generate_images.py     -> visuals/*.png
  4. edit_video.py           -> final_video.mp4

Each step is a separate script so you can debug or re-run any single stage.
This file just calls them in sequence and stops on the first failure.

Required environment variable (set as a GitHub Actions secret in production):
  GEMINI_API_KEY   - free, from https://aistudio.google.com/apikey
                     (used for both script writing and Nano Banana image generation)

Usage:
    python3 run_pipeline.py --topics-file topics.txt
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

STEPS_DIR = Path(__file__).parent


def run_step(description, cmd):
    print(f"\n=== {description} ===")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Step failed: {description}")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="A specific topic (skip for random from --topics-file)")
    ap.add_argument("--topics-file", default="topics.txt")
    ap.add_argument("--voice", default="hi-IN-MadhurNeural")
    ap.add_argument("--music", help="Optional background music file for the final video")
    ap.add_argument("--output", default="final_video.mp4")
    args = ap.parse_args()

    script_cmd = [sys.executable, str(STEPS_DIR / "generate_script.py"), "--output", "script.json"]
    script_cmd += ["--topic", args.topic] if args.topic else ["--topics-file", args.topics_file]
    run_step("1/4 Generating script", script_cmd)

    run_step("2/4 Generating voiceover", [
        sys.executable, str(STEPS_DIR / "generate_voiceover.py"),
        "--script", "script.json", "--voice", args.voice,
        "--output-audio", "narration.mp3", "--output-srt", "captions.srt",
    ])

    run_step("3/4 Generating images", [
        sys.executable, str(STEPS_DIR / "generate_images.py"),
        "--script", "script.json", "--output-dir", "visuals",
    ])

    edit_cmd = [
        sys.executable, str(STEPS_DIR / "edit_video.py"),
        "--narration", "narration.mp3", "--visuals", "visuals",
        "--captions", "captions.srt", "--output", args.output,
    ]
    if args.music:
        edit_cmd += ["--music", args.music]
    run_step("4/5 Assembling final video", edit_cmd)

    run_step("5/5 Sending Telegram notification", [
        sys.executable, str(STEPS_DIR / "telegram_notify.py"),
        "--video", args.output,
        "--title", json.loads(Path("script.json").read_text()).get("title", ""),
    ])

    print(f"\nPipeline complete: {args.output}")
    print("Check your Telegram for the preview. Upload to YouTube yourself when ready.")


if __name__ == "__main__":
    main()
