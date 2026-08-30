#!/usr/bin/env python3
"""
telegram_notify.py — Sends the finished video to your Telegram bot once
the pipeline completes, so you can preview it immediately on your phone.

Setup (one-time, see earlier steps):
  1. Create a bot via @BotFather on Telegram -> get a bot token
  2. Message your bot once, then visit
     https://api.telegram.org/bot<TOKEN>/getUpdates to find your chat id
  3. pip install requests
  4. export TELEGRAM_BOT_TOKEN="..."
     export TELEGRAM_CHAT_ID="..."

Usage:
    python3 telegram_notify.py --video final_video.mp4 --title "Video title"
"""

import argparse
import os
import sys
from pathlib import Path

import requests

MAX_TELEGRAM_VIDEO_MB = 50


def send_video(token, chat_id, video_path, caption):
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"video": f},
            timeout=300,
        )
    return resp


def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
        sys.exit(1)

    video_path = Path(args.video)
    size_mb = video_path.stat().st_size / (1024 * 1024)
    caption = f"Ready to review: {args.title}" if args.title else "New video ready to review"

    if size_mb <= MAX_TELEGRAM_VIDEO_MB:
        resp = send_video(token, chat_id, video_path, caption)
    else:
        # Too large for Telegram's direct upload limit — send a text alert instead
        # so you know to check GitHub Actions Artifacts for the file.
        resp = send_message(
            token, chat_id,
            f"{caption}\n\nFile is {size_mb:.0f}MB — too large to send directly. "
            f"Check GitHub Actions Artifacts to download it."
        )

    if resp.status_code != 200:
        print(f"Telegram API error {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    print("Telegram notification sent.")


if __name__ == "__main__":
    main()
