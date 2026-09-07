#!/usr/bin/env python3
"""
generate_script.py — Given a topic (or a rotating topic list), generates a
structured long-form video script using the free Gemini API.

Setup:
  pip install google-genai
  Get a free API key: https://aistudio.google.com/apikey
  export GEMINI_API_KEY="your-key-here"

Output: script.json with:
  {
    "title": "...",
    "description": "...",
    "tags": ["...", "..."],
    "sections": [
      {"text": "narration text for this section", "image_prompt": "visual description for this section"},
      ...
    ]
  }

This structure is what generate_voiceover.py and generate_images.py both read.

Usage:
    python3 generate_script.py --topic "world war 2 secret weapons" --output script.json
    python3 generate_script.py --topics-file topics.txt --output script.json   # picks one at random
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

from google import genai

PROMPT_TEMPLATE = """You are writing a script for a faceless long-form YouTube video (9-11 minutes spoken, ~1400-1700 words total) in the "{topic}" niche/topic. Write it in natural, conversational Hindi (Devanagari script), in the tone of a calm documentary narrator — measured, factual, slightly dramatic pacing, no filler words.

Return ONLY valid JSON (no markdown fences, no preamble) matching exactly this shape:
{{
  "title": "a punchy, clickable YouTube title in Hindi, under 70 characters",
  "description": "a 2-3 sentence YouTube description in Hindi with the topic naturally included",
  "tags": ["8 to 12 relevant lowercase English tags for YouTube search"],
  "sections": [
    {{"text": "narration text in Hindi, documentary-narrator spoken style, 110-150 words", "image_prompt": "a short visual description IN ENGLISH for an AI image generator to illustrate this section, concrete, cinematic, photorealistic"}}
  ]
}}

Write 9 to 11 sections total (to reach ~10 minutes of narration). The first section must open with a
strong hook (a striking claim or question) delivered in a documentary-narrator tone. The last section
must close with a reflective final line, then a brief natural call-to-action to subscribe.
Do not use headers like "Section 1" inside the text — it should read as continuous spoken narration.
Topic: {topic}
"""


def pick_topic(args):
    if args.topic:
        return args.topic
    if args.topics_file:
        topics = [t.strip() for t in Path(args.topics_file).read_text().splitlines() if t.strip()]
        if not topics:
            print("Topics file is empty.")
            sys.exit(1)
        return random.choice(topics)
    print("Provide --topic or --topics-file")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="A specific topic")
    ap.add_argument("--topics-file", help="A text file with one topic per line; one is picked at random")
    ap.add_argument("--output", default="script.json")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY environment variable (free key from https://aistudio.google.com/apikey)")
        sys.exit(1)

    topic = pick_topic(args)
    print(f"Topic: {topic}")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=PROMPT_TEMPLATE.format(topic=topic),
    )
    raw = response.text.strip()

    # Strip accidental markdown fences if the model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print("Model did not return valid JSON:", e)
        print(raw[:1000])
        sys.exit(1)

    Path(args.output).write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Script saved: {args.output} ({len(data.get('sections', []))} sections)")


if __name__ == "__main__":
    main()
