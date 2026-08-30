#!/usr/bin/env python3
"""
edit_video.py — Assembles a long-form faceless YouTube video from:
  - a narration audio file (from your TTS step)
  - a folder of images (applies Ken Burns pan/zoom to each)
  - OR a folder of video clips (used as-is, trimmed to fit)
  - optional background music (mixed at low volume under narration)
  - optional .srt captions (burned into the video)

Requires only the `ffmpeg` binary (already installed almost everywhere,
including GitHub Actions ubuntu-latest runners — no extra install needed).

Usage:
    python3 edit_video.py \
        --narration audio/narration.mp3 \
        --visuals visuals/ \
        --music music/bg.mp3 \
        --captions captions.srt \
        --output final_video.mp4
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    """Run a shell command, raise with clear output on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Command failed:\n", " ".join(cmd))
        print("stderr:\n", result.stderr[-2000:])
        sys.exit(1)
    return result.stdout


def get_audio_duration(path):
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path)
    ])
    return float(json.loads(out)["format"]["duration"])


def is_video(path):
    return path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}


def build_visual_segment(src, out_path, seg_duration, w=1920, h=1080):
    """
    For an image: apply a slow Ken Burns zoom/pan over seg_duration seconds.
    For a video clip: trim/loop it to seg_duration seconds.
    Output is a silent video segment at 30fps, ready to be concatenated.
    """
    if is_video(src):
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
            "-t", str(seg_duration),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30",
            "-an", str(out_path),
        ]
    else:
        # Ken Burns: slow zoom-in over the duration, using zoompan filter.
        frames = int(seg_duration * 30)
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(src),
            "-vf",
            (
                f"scale={w*2}:{h*2},"
                f"zoompan=z='min(zoom+0.0007,1.3)':d={frames}:s={w}x{h}:fps=30"
            ),
            "-t", str(seg_duration),
            str(out_path),
        ]
    run(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--narration", required=True, help="Path to narration audio (mp3/wav)")
    ap.add_argument("--visuals", required=True, help="Folder of images and/or video clips")
    ap.add_argument("--music", help="Optional background music file")
    ap.add_argument("--captions", help="Optional .srt captions file to burn in")
    ap.add_argument("--output", default="final_video.mp4")
    ap.add_argument("--music-volume", type=float, default=0.12, help="Background music volume (0-1)")
    args = ap.parse_args()

    work = Path("_work")
    work.mkdir(exist_ok=True)

    narration = Path(args.narration)
    visuals_dir = Path(args.visuals)
    total_duration = get_audio_duration(narration)

    visual_files = sorted(
        p for p in visuals_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".webm"}
    )
    if not visual_files:
        print("No images or clips found in --visuals folder.")
        sys.exit(1)

    seg_duration = total_duration / len(visual_files)

    print(f"Narration length: {total_duration:.1f}s | {len(visual_files)} visuals | "
          f"{seg_duration:.1f}s each")

    segment_paths = []
    for i, src in enumerate(visual_files):
        seg_out = work / f"seg_{i:03d}.mp4"
        build_visual_segment(src, seg_out, seg_duration)
        segment_paths.append(seg_out)

    concat_list = work / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in segment_paths))

    silent_video = work / "video_only.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent_video),
    ])

    # Mix narration + optional background music
    audio_out = work / "audio_mix.aac"
    if args.music:
        run([
            "ffmpeg", "-y", "-i", str(narration), "-stream_loop", "-1", "-i", args.music,
            "-filter_complex",
            f"[1:a]volume={args.music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "[a]", "-t", str(total_duration), str(audio_out),
        ])
    else:
        run(["ffmpeg", "-y", "-i", str(narration), "-t", str(total_duration), str(audio_out)])

    # Combine video + audio, optionally burning in captions
    final_cmd = ["ffmpeg", "-y", "-i", str(silent_video), "-i", str(audio_out)]
    if args.captions:
        final_cmd += ["-vf", f"subtitles={args.captions}"]
    final_cmd += ["-c:v", "libx264", "-c:a", "aac", "-shortest", args.output]
    run(final_cmd)

    print(f"\nDone: {args.output}")


if __name__ == "__main__":
    main()
