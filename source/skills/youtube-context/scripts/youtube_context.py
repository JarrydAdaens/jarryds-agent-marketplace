#!/usr/bin/env python3
"""Collect YouTube captions, audio, and frames into a per-video context folder.

The helper never installs a dependency and never picks a write location. Every
subcommand that writes requires an explicit folder argument.

Subcommands:
    doctor      Report which external tools are available.
    fetch       Create the video folder from metadata and published captions.
    audio       Download the audio track for local transcription.
    transcribe  Transcribe downloaded audio with faster-whisper.
    frames      Extract still frames so a multimodal agent can read the screen.
    clean       Remove the large intermediates and keep the readable output.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SUB_LANGS = "en.*,en"
DEFAULT_BLOCK_SPAN = 30.0
DEFAULT_FRAME_INTERVAL = 30.0
DEFAULT_FRAME_LIMIT = 60
DEFAULT_SCENE_THRESHOLD = 0.3
DEFAULT_FRAME_HEIGHT = 720

METADATA_SUFFIX = "-metadata.json"
PROVENANCE_SUFFIX = "-provenance.json"
TRANSCRIPT_SUFFIX = "-transcript.txt"
NOTES_SUFFIX = "-notes.md"
FRAME_INDEX_SUFFIX = "-frames-index.json"

AUDIO_SUFFIXES = (".m4a", ".mp3", ".opus", ".webm")
VIDEO_SUFFIXES = (".mp4", ".mkv", ".webm")
MEDIA_SUFFIXES = (".m4a", ".mp3", ".opus", ".webm", ".mp4", ".mkv", ".part")


# --------------------------------------------------------------------------
# process helpers
# --------------------------------------------------------------------------

def fail(message: str) -> None:
    print("error: " + message, file=sys.stderr)
    raise SystemExit(1)


def run(cmd, check: bool = True):
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        fail("command failed ({0}): {1}\n{2}".format(proc.returncode, " ".join(cmd), detail))
    return proc


def yt_dlp_cmd():
    """Prefer the console script, fall back to the importable module."""
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    probe = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--version"], capture_output=True, text=True
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]
    return None


def require_yt_dlp():
    cmd = yt_dlp_cmd()
    if cmd is None:
        fail(
            "yt-dlp not found. Ask the user before installing; the command is:\n"
            "  " + sys.executable + " -m pip install --upgrade yt-dlp"
        )
    return cmd


def ffmpeg_cmd():
    override = os.environ.get("FFMPEG")
    if override and Path(override).exists():
        return [override]
    exe = shutil.which("ffmpeg")
    return [exe] if exe else None


def require_ffmpeg():
    cmd = ffmpeg_cmd()
    if cmd is None:
        fail(
            "ffmpeg not found. Ask the user before installing; on Windows the usual\n"
            "command is:  winget install Gyan.FFmpeg\n"
            "Set FFMPEG=<path to ffmpeg.exe> to point at an existing copy."
        )
    return cmd


# --------------------------------------------------------------------------
# naming and time formatting
# --------------------------------------------------------------------------

VIDEO_ID_PATTERNS = (
    r"[?&]v=([0-9A-Za-z_-]{11})",
    r"youtu\.be/([0-9A-Za-z_-]{11})",
    r"/(?:shorts|live|embed)/([0-9A-Za-z_-]{11})",
)


def video_id(url: str):
    for pattern in VIDEO_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url):
        return url
    return None


def slugify(text: str, limit: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:limit].strip("-") or "video"


def stamp(seconds: float) -> str:
    """Readable timestamp for prose, for example 12:05 or 1:02:30."""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "{0:d}:{1:02d}:{2:02d}".format(hours, minutes, secs)
    return "{0:02d}:{1:02d}".format(minutes, secs)


def file_stamp(seconds: float) -> str:
    """Filename-safe timestamp; colons are illegal in Windows filenames."""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return "{0:02d}h{1:02d}m{2:02d}s".format(hours, minutes, secs)


def duration_label(seconds):
    return stamp(seconds) if seconds else None


# --------------------------------------------------------------------------
# caption parsing
# --------------------------------------------------------------------------

CUE_TIME = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[.,]\d{3})"
)
TAG = re.compile(r"<[^>]+>")
PTS_TIME = re.compile(r"pts_time:([0-9.]+)")


def vtt_seconds(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def dedupe_cues(cues, window: int = 4):
    """Drop the rolling repeats that auto-generated captions emit.

    Auto captions republish the previous line alongside each new one, so the raw
    cue list repeats most text two or three times. Comparing against the last few
    kept lines removes those repeats without collapsing a phrase that genuinely
    recurs much later in the video.
    """
    kept = []
    for start, line in cues:
        recent = set(text for _, text in kept[-window:])
        if line in recent:
            continue
        kept.append((start, line))
    return kept


def parse_vtt(text: str):
    """Return [(start_seconds, line)] from WebVTT or SRT content."""
    cues = []
    start = None
    in_cue = False
    for raw in text.splitlines():
        line = raw.strip()
        match = CUE_TIME.search(line)
        if match:
            start = vtt_seconds(match.group("start"))
            in_cue = True
            continue
        if not line:
            in_cue = False
            continue
        if not in_cue or start is None:
            continue
        cleaned = html.unescape(TAG.sub("", line)).strip()
        if cleaned:
            cues.append((start, cleaned))
    return dedupe_cues(cues)


def group_cues(cues, span: float = DEFAULT_BLOCK_SPAN):
    """Merge short cues into timestamped paragraphs of roughly `span` seconds."""
    blocks = []
    block_start = None
    words = []
    for start, line in cues:
        if block_start is None:
            block_start = start
        if words and start - block_start >= span:
            blocks.append((block_start, " ".join(words)))
            block_start = start
            words = []
        words.append(line)
    if words and block_start is not None:
        blocks.append((block_start, " ".join(words)))
    return blocks


def render_transcript(blocks) -> str:
    return "\n\n".join("[{0}] {1}".format(stamp(start), text) for start, text in blocks)


def parse_scene_log(text: str):
    """Pull frame presentation times out of an ffmpeg metadata print log."""
    return [float(match.group(1)) for match in PTS_TIME.finditer(text)]


def subtitle_tag(path, slug: str) -> str:
    """Return the language tag from `<slug>.<tag>.vtt`."""
    name = path.name
    if name.startswith(slug + ".") and name.endswith(".vtt"):
        return name[len(slug) + 1 : -len(".vtt")]
    return name


def pick_subtitle(paths, slug: str):
    """Choose one caption track and return (chosen, discarded).

    A language pattern such as `en.*` matches several published tracks at once,
    so yt-dlp writes `en`, `en-US`, and `en-orig` side by side. They are usually
    the same text. Prefer the plain tag, then the shortest, and treat the
    `-orig` track as the last resort because its language follows the uploader
    rather than the request.
    """
    if not paths:
        return None, []

    def rank(path):
        tag = subtitle_tag(path, slug)
        return (tag.endswith("-orig"), len(tag), tag)

    ordered = sorted(paths, key=rank)
    return ordered[0], ordered[1:]


# --------------------------------------------------------------------------
# folder layout
# --------------------------------------------------------------------------

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_folder(raw: str):
    """Return (folder, slug, metadata) for an existing video folder."""
    folder = Path(raw).expanduser().resolve()
    if not folder.is_dir():
        fail("not a folder: " + str(folder))
    matches = sorted(folder.glob("*" + METADATA_SUFFIX))
    if not matches:
        fail("no *{0} in {1}. Run `fetch` first.".format(METADATA_SUFFIX, folder))
    slug = matches[0].name[: -len(METADATA_SUFFIX)]
    return folder, slug, read_json(matches[0])


def find_media(folder: Path, slug: str, suffixes):
    for candidate in sorted(folder.glob(slug + ".*")):
        if candidate.suffix.lower() in suffixes:
            return candidate
    return None


def write_transcript(folder: Path, slug: str, cues, span: float) -> Path:
    blocks = group_cues(cues, span)
    path = folder / (slug + TRANSCRIPT_SUFFIX)
    path.write_text(render_transcript(blocks) + "\n", encoding="utf-8")
    return path


def update_provenance(folder: Path, slug: str, patch: dict) -> None:
    path = folder / (slug + PROVENANCE_SUFFIX)
    payload = read_json(path) if path.exists() else {}
    payload.update(patch)
    write_json(path, payload)


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------

def cmd_doctor(args) -> None:
    rows = []

    ytdlp = yt_dlp_cmd()
    if ytdlp:
        version = run(ytdlp + ["--version"], check=False).stdout.strip()
        rows.append(("yt-dlp", "available", version or "unknown version"))
    else:
        rows.append(("yt-dlp", "MISSING", "pip install --upgrade yt-dlp"))

    ffmpeg = ffmpeg_cmd()
    if ffmpeg:
        lines = run(ffmpeg + ["-version"], check=False).stdout.splitlines()
        rows.append(("ffmpeg", "available", lines[0] if lines else ""))
    else:
        rows.append(("ffmpeg", "MISSING", "winget install Gyan.FFmpeg"))

    probe = subprocess.run(
        [sys.executable, "-c", "import faster_whisper; print(faster_whisper.__version__)"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        rows.append(("faster-whisper", "available", probe.stdout.strip()))
    else:
        rows.append(("faster-whisper", "MISSING", "pip install faster-whisper"))

    width = max(len(name) for name, _, _ in rows)
    for name, state, detail in rows:
        print("{0}  {1}  {2}".format(name.ljust(width), state.ljust(9), detail))

    print("")
    print("Tier 1 (captions) needs yt-dlp only.")
    print("Tier 2 (local transcription) needs yt-dlp and faster-whisper.")
    print("Tier 3 (frames) needs yt-dlp and ffmpeg.")


def write_notes_scaffold(folder: Path, slug: str, metadata: dict, force: bool) -> None:
    path = folder / (slug + NOTES_SUFFIX)
    if path.exists() and not force:
        return
    header = [
        "# " + str(metadata.get("title") or slug),
        "",
        "- Source: " + str(metadata.get("url")),
        "- Channel: " + str(metadata.get("channel") or "unknown"),
        "- Length: " + str(metadata.get("duration") or "unknown"),
        "- Published: " + str(metadata.get("upload_date") or "unknown"),
        "",
    ]
    chapters = metadata.get("chapters") or []
    if chapters:
        header += ["## Chapters", ""]
        for chapter in chapters:
            if chapter.get("start"):
                header.append("- [{0}] {1}".format(chapter["start"], chapter.get("title") or ""))
        header.append("")
    body = [
        "## Summary",
        "",
        "_Pending._",
        "",
        "## Key points",
        "",
        "_Pending. Cite a [MM:SS] timestamp for every claim._",
        "",
        "## Commands and code",
        "",
        "_Pending. Remove this section if the video contains none._",
        "",
        "## Open questions",
        "",
        "_Pending._",
        "",
    ]
    path.write_text("\n".join(header + body), encoding="utf-8")


def cmd_fetch(args) -> None:
    ytdlp = require_yt_dlp()
    root = Path(args.output).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    probe = run(ytdlp + ["--dump-single-json", "--skip-download", "--no-warnings", args.url])
    raw = json.loads(probe.stdout)
    if raw.get("_type") == "playlist":
        fail("that URL is a playlist or channel. Pass a single video URL.")

    identifier = raw.get("id") or video_id(args.url) or "unknown"
    slug = slugify(raw.get("title") or "video") + "-" + identifier
    folder = root / slug
    if folder.exists() and any(folder.iterdir()) and not args.force:
        fail(str(folder) + " already has content. Pass --force to refresh it.")
    folder.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": identifier,
        "title": raw.get("title"),
        "channel": raw.get("channel") or raw.get("uploader"),
        "channel_url": raw.get("channel_url") or raw.get("uploader_url"),
        "upload_date": raw.get("upload_date"),
        "duration_seconds": raw.get("duration"),
        "duration": duration_label(raw.get("duration")),
        "url": raw.get("webpage_url") or args.url,
        "chapters": [
            {
                "title": chapter.get("title"),
                "start_seconds": chapter.get("start_time"),
                "start": duration_label(chapter.get("start_time")),
            }
            for chapter in (raw.get("chapters") or [])
        ],
        "description": raw.get("description"),
    }
    write_json(folder / (slug + METADATA_SUFFIX), metadata)

    # Published captions beat auto-generated ones, so try each flag separately.
    source = None
    subtitle_file = None
    discarded = []
    for flag, label in (("--write-subs", "published-captions"),
                        ("--write-auto-subs", "auto-captions")):
        run(
            ytdlp
            + [
                "--skip-download",
                "--no-warnings",
                flag,
                "--sub-langs",
                args.lang,
                "--sub-format",
                "vtt",
                "-o",
                str(folder / (slug + ".%(ext)s")),
                metadata["url"],
            ],
            check=False,
        )
        found = sorted(folder.glob(slug + "*.vtt"))
        if found:
            subtitle_file, extras = pick_subtitle(found, slug)
            # The duplicate tracks are large and identical often enough that
            # keeping them only clutters the folder.
            for extra in extras:
                discarded.append(subtitle_tag(extra, slug))
                extra.unlink()
            source = label
            break

    write_json(
        folder / (slug + PROVENANCE_SUFFIX),
        {
            "url": metadata["url"],
            "fetched_at": now_utc(),
            "transcript_source": source,
            "subtitle_file": subtitle_file.name if subtitle_file else None,
            "subtitle_languages_requested": args.lang,
            "subtitle_tracks_discarded": discarded,
        },
    )

    transcript_path = None
    if subtitle_file:
        cues = parse_vtt(subtitle_file.read_text(encoding="utf-8", errors="replace"))
        transcript_path = write_transcript(folder, slug, cues, args.span)

    write_notes_scaffold(folder, slug, metadata, force=args.force)

    print("folder: " + str(folder))
    print("title: {0}  ({1})".format(metadata["title"], metadata["duration"] or "unknown length"))
    if transcript_path:
        words = len(transcript_path.read_text(encoding="utf-8").split())
        print("transcript: {0}  [{1}, ~{2} words]".format(transcript_path.name, source, words))
        print("captions: kept {0}".format(subtitle_tag(subtitle_file, slug)), end="")
        print(", discarded {0}".format(", ".join(discarded)) if discarded else "")
    else:
        print("transcript: NONE - this video publishes no captions.")
        print("next: run `audio` then `transcribe` to produce one locally.")


def cmd_audio(args) -> None:
    ytdlp = require_yt_dlp()
    folder, slug, metadata = resolve_folder(args.folder)

    cmd = ytdlp + ["--no-warnings", "-f", "bestaudio", "-o", str(folder / (slug + ".%(ext)s"))]
    if ffmpeg_cmd():
        # Re-encoding to m4a keeps the file small and widely readable.
        cmd += ["--extract-audio", "--audio-format", "m4a"]
    cmd.append(metadata["url"])
    run(cmd)

    audio = find_media(folder, slug, AUDIO_SUFFIXES)
    if audio is None:
        fail("yt-dlp reported success but no audio file was written.")
    size_mb = audio.stat().st_size / (1024 * 1024)
    print("audio: {0}  ({1:.1f} MB)".format(audio.name, size_mb))


def cmd_transcribe(args) -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        fail(
            "faster-whisper not installed. Ask the user before installing; the command is:\n"
            "  " + sys.executable + " -m pip install faster-whisper"
        )

    folder, slug, _ = resolve_folder(args.folder)
    audio = find_media(folder, slug, AUDIO_SUFFIXES)
    if audio is None:
        fail("no audio in {0}. Run `audio` first.".format(folder))

    print("loading model '{0}' (the first run downloads it)...".format(args.model), file=sys.stderr)
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments, info = model.transcribe(str(audio), vad_filter=True, language=args.language)

    cues = [(seg.start, seg.text.strip()) for seg in segments if seg.text.strip()]
    if not cues:
        fail("transcription produced no speech segments.")
    path = write_transcript(folder, slug, cues, args.span)

    update_provenance(
        folder,
        slug,
        {
            "transcript_source": "faster-whisper:" + args.model,
            "transcript_language": getattr(info, "language", None),
            "transcribed_at": now_utc(),
        },
    )
    print("transcript: {0}  [whisper:{1}, {2} segments]".format(path.name, args.model, len(cues)))


def download_video(ytdlp, folder: Path, slug: str, url: str, height: int) -> Path:
    selector = "bv*[height<={0}]+ba/b[height<={0}]/b".format(height)
    run(
        ytdlp
        + [
            "--no-warnings",
            "-f",
            selector,
            "--merge-output-format",
            "mp4",
            "-o",
            str(folder / (slug + ".%(ext)s")),
            url,
        ]
    )
    video = find_media(folder, slug, VIDEO_SUFFIXES)
    if video is None:
        fail("yt-dlp reported success but no video file was written.")
    return video


def cmd_frames(args) -> None:
    ffmpeg = require_ffmpeg()
    folder, slug, metadata = resolve_folder(args.folder)

    video = find_media(folder, slug, VIDEO_SUFFIXES)
    if video is None:
        print("no local video; downloading...", file=sys.stderr)
        video = download_video(require_yt_dlp(), folder, slug, metadata["url"], args.height)

    frames_dir = folder / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    extension = "png" if args.format == "png" else "jpg"
    pattern = str(frames_dir / ("raw-%04d." + extension))
    scene_log = folder / "scene-log.txt"

    if args.scene is not None:
        video_filter = "select='gt(scene,{0})',metadata=print:file={1}".format(
            args.scene, scene_log.as_posix()
        )
        cmd = ffmpeg + ["-nostdin", "-y", "-i", str(video), "-vf", video_filter, "-vsync", "vfr"]
    else:
        cmd = ffmpeg + ["-nostdin", "-y", "-i", str(video), "-vf", "fps=1/{0}".format(args.interval)]

    if extension == "jpg":
        cmd += ["-q:v", str(args.quality)]
    cmd += ["-frames:v", str(args.max_frames), pattern]
    run(cmd)

    times = []
    if args.scene is not None and scene_log.exists():
        times = parse_scene_log(scene_log.read_text(encoding="utf-8", errors="replace"))
        scene_log.unlink()

    index = []
    for position, raw in enumerate(sorted(frames_dir.glob("raw-*." + extension))):
        seconds = times[position] if position < len(times) else position * args.interval
        target = frames_dir / "{0}-frame-{1:03d}-{2}.{3}".format(
            slug, position + 1, file_stamp(seconds), extension
        )
        raw.rename(target)
        index.append(
            {"file": target.name, "seconds": round(seconds, 2), "timestamp": stamp(seconds)}
        )

    write_json(folder / (slug + FRAME_INDEX_SUFFIX), {"frames": index})
    update_provenance(
        folder,
        slug,
        {
            "frames_mode": "scene" if args.scene is not None else "interval:{0}s".format(args.interval),
            "frames_count": len(index),
            "frames_extracted_at": now_utc(),
        },
    )

    if len(index) == args.max_frames:
        print(
            "note: stopped at the --max-frames limit of {0}; later parts of the "
            "video are not covered.".format(args.max_frames),
            file=sys.stderr,
        )
    print("frames: {0} in {1}".format(len(index), frames_dir))


def cmd_clean(args) -> None:
    folder, slug, _ = resolve_folder(args.folder)
    removed = []
    for candidate in sorted(folder.glob(slug + ".*")):
        if candidate.suffix.lower() in MEDIA_SUFFIXES:
            removed.append(candidate.name)
            candidate.unlink()
    leftover = folder / "scene-log.txt"
    if leftover.exists():
        removed.append(leftover.name)
        leftover.unlink()
    print("removed: " + (", ".join(removed) if removed else "nothing"))
    print("kept: metadata, provenance, captions, transcript, notes, frames")


# --------------------------------------------------------------------------
# argument parsing
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="youtube_context.py", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="report available external tools")
    doctor.set_defaults(func=cmd_doctor)

    fetch = subparsers.add_parser("fetch", help="create the video folder from captions")
    fetch.add_argument("--url", required=True)
    fetch.add_argument("--output", required=True, help="root folder that holds video folders")
    fetch.add_argument("--lang", default=DEFAULT_SUB_LANGS)
    fetch.add_argument("--span", type=float, default=DEFAULT_BLOCK_SPAN)
    fetch.add_argument("--force", action="store_true", help="refresh a folder that already exists")
    fetch.set_defaults(func=cmd_fetch)

    audio = subparsers.add_parser("audio", help="download the audio track")
    audio.add_argument("--folder", required=True)
    audio.set_defaults(func=cmd_audio)

    transcribe = subparsers.add_parser("transcribe", help="transcribe audio locally")
    transcribe.add_argument("--folder", required=True)
    transcribe.add_argument("--model", default="small.en")
    transcribe.add_argument("--device", default="auto")
    transcribe.add_argument("--compute-type", default="int8")
    transcribe.add_argument("--language", default=None)
    transcribe.add_argument("--span", type=float, default=DEFAULT_BLOCK_SPAN)
    transcribe.set_defaults(func=cmd_transcribe)

    frames = subparsers.add_parser("frames", help="extract still frames")
    frames.add_argument("--folder", required=True)
    frames.add_argument("--interval", type=float, default=DEFAULT_FRAME_INTERVAL)
    frames.add_argument(
        "--scene",
        type=float,
        nargs="?",
        const=DEFAULT_SCENE_THRESHOLD,
        default=None,
        help="use scene-change detection instead of a fixed interval",
    )
    frames.add_argument("--max-frames", type=int, default=DEFAULT_FRAME_LIMIT)
    frames.add_argument("--height", type=int, default=DEFAULT_FRAME_HEIGHT)
    frames.add_argument("--format", choices=("jpg", "png"), default="jpg")
    frames.add_argument("--quality", type=int, default=2, help="jpg quality; 2 is near-lossless")
    frames.set_defaults(func=cmd_frames)

    clean = subparsers.add_parser("clean", help="remove audio and video intermediates")
    clean.add_argument("--folder", required=True)
    clean.set_defaults(func=cmd_clean)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
