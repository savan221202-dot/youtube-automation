#!/usr/bin/env python3
"""
generate_images.py — Reads script.json and generates one image per section
(using each section's "image_prompt") via Google's Nano Banana image model
(gemini-2.5-flash-image) — the same free model family behind Google Flow's
free image tier, but accessible through a real API for automation.

Note: Google Flow itself (flow.google.com) is a manual web app with no
official free automation API. This uses the underlying Gemini image model
directly instead, which gives comparable quality and is genuinely scriptable.

Setup:
  pip install google-generativeai pillow
  Free API key: https://aistudio.google.com/apikey (same key as generate_script.py)
  export GEMINI_API_KEY="your-key-here"

  Check your current free-tier daily image quota at https://aistudio.google.com
  before relying on this daily — Google's free limits change over time.

Usage:
    python3 generate_images.py --script script.json --output-dir visuals
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

import google.generativeai as genai
from PIL import Image

MODEL_NAME = "gemini-2.5-flash-image"


def generate_image(model, prompt, retries=4):
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return Image.open(io.BytesIO(part.inline_data.data))
            raise RuntimeError("No image data in response")
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"  Attempt {attempt+1} failed ({e}); retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Failed to generate image for prompt: {prompt}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="script.json")
    ap.add_argument("--output-dir", default="visuals")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY environment variable (free key from https://aistudio.google.com/apikey)")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    data = json.loads(Path(args.script).read_text())
    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    for i, section in enumerate(data["sections"]):
        prompt = section.get("image_prompt", data.get("title", "abstract background"))
        # Documentary look: photorealistic, cinematic, no text/watermarks
        full_prompt = f"{prompt}. Photorealistic, cinematic documentary style, 16:9, no text, no watermark."
        print(f"[{i+1}/{len(data['sections'])}] {prompt[:70]}")
        image = generate_image(model, full_prompt)
        out_path = out_dir / f"{i:03d}.png"
        image.save(out_path)

    print(f"\nDone. {len(data['sections'])} images saved to {out_dir}/")


if __name__ == "__main__":
    main()
