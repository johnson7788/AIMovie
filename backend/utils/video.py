import logging
import requests
import subprocess
import os
import shutil
import tempfile
from typing import List, Optional
from tenacity import retry


def _resolve_ffmpeg_exe() -> str:
    """Return ffmpeg executable path (system PATH or imageio_ffmpeg bundle)."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    raise RuntimeError(
        "ffmpeg not found. Install ffmpeg and add it to PATH, "
        "or ensure imageio-ffmpeg is installed."
    )


def _resolve_ffprobe_exe() -> Optional[str]:
    """Return ffprobe path if available (often not bundled with imageio_ffmpeg)."""
    exe = shutil.which("ffprobe")
    if exe:
        return exe
    ffmpeg = _resolve_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg)
    for name in ("ffprobe.exe", "ffprobe"):
        candidate = os.path.join(ffmpeg_dir, name)
        if os.path.isfile(candidate):
            return candidate
    if "ffmpeg" in os.path.basename(ffmpeg):
        candidate = ffmpeg.replace("ffmpeg", "ffprobe")
        if os.path.isfile(candidate):
            return candidate
    return None


def _read_stderr_file(stderr_path: str) -> str:
    """Safely read stderr output from a temp file."""
    try:
        with open(stderr_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ""


@retry
def download_video(url, save_path):
    try:
        logging.info(f"Downloading video from {url} to {save_path}")

        response = requests.get(url, stream=True)
        response.raise_for_status()  # 检查请求是否成功

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info(f"Video downloaded successfully to {save_path}")

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise e


def _probe_video(path: str) -> dict:
    """Quick sanity check: file exists, not empty, and probe tool can parse it."""
    import json
    if not os.path.exists(path):
        raise FileNotFoundError(f"Video file not found: {path}")
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb < 0.01:
        raise ValueError(f"Video file is too small ({size_mb:.2f} MB): {path}")

    ffprobe = _resolve_ffprobe_exe()
    if ffprobe:
        result = subprocess.run(
            [ffprobe, '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed for {path}: {result.stderr}")
        info = json.loads(result.stdout)
        logging.info(f"Probed {path}: {size_mb:.1f} MB, "
                     f"format={info.get('format', {}).get('format_name')}, "
                     f"duration={info.get('format', {}).get('duration')}s")
        return info

    # imageio_ffmpeg bundles ffmpeg only — use it to verify the container is readable
    ffmpeg = _resolve_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, '-hide_banner', '-i', path],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=60,
    )
    stderr = result.stderr or ""
    if "Invalid data" in stderr or "No such file" in stderr or "does not contain" in stderr:
        raise RuntimeError(f"ffmpeg probe failed for {path}: {stderr[-500:]}")
    logging.info(f"Probed {path}: {size_mb:.1f} MB (ffmpeg probe, ffprobe unavailable)")
    return {}


def concat_videos(video_paths: List[str], output_path: str,
                  target_width: int = 960, target_height: int = 960) -> str:
    """Concatenate videos using ffmpeg concat demuxer.

    Reliably handles mixed resolutions by normalizing all inputs to the
    target resolution. Uses libx264 with CRF 23 for consistent quality.
    """
    if not video_paths:
        raise ValueError("video_paths must not be empty")

    if len(video_paths) == 1:
        # Single video, just copy it
        import shutil
        shutil.copy2(video_paths[0], output_path)
        return output_path

    logging.info(f"Concatenating {len(video_paths)} videos to {output_path}")

    # Pre-validate all input videos
    for path in video_paths:
        _probe_video(path)

    # Write ffmpeg concat file (must use absolute paths — ffmpeg concat
    # demuxer resolves relative paths relative to the concat file's directory,
    # not the process CWD)
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for path in video_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    # Normalize all inputs to target resolution during concatenation
    vf = (f"scale={target_width}:{target_height}"
          f":force_original_aspect_ratio=decrease,"
          f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2")

    ffmpeg = _resolve_ffmpeg_exe()
    cmd = [
        ffmpeg, '-y',
        '-f', 'concat', '-safe', '0', '-i', concat_file,
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-an',  # no audio
        output_path,
    ]

    logging.info(f"Running ffmpeg: {' '.join(cmd)}")

    # Use a temp file for stderr to avoid pipe-buffer deadlock
    # (ffmpeg writes extensive progress info to stderr, which would fill
    #  the default 64KB pipe buffer and deadlock if using PIPE)
    stderr_path = output_path + ".ffmpeg.stderr.txt"
    try:
        with open(stderr_path, 'w', encoding='utf-8') as stderr_f:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=stderr_f,
                timeout=600,
            )
    except subprocess.TimeoutExpired:
        if os.path.exists(stderr_path):
            os.remove(stderr_path)
        raise RuntimeError(
            f"ffmpeg concat timed out after 600s. "
            f"Input videos: {video_paths}"
        )
    finally:
        if os.path.exists(concat_file):
            os.remove(concat_file)

    stderr_text = _read_stderr_file(stderr_path)
    if os.path.exists(stderr_path):
        os.remove(stderr_path)

    if result.returncode != 0:
        # Log last 2000 chars of stderr (most relevant for error diagnosis)
        tail = stderr_text[-2000:] if len(stderr_text) > 2000 else stderr_text
        raise RuntimeError(f"ffmpeg concat failed: {tail}")

    logging.info(f"Concatenation complete: {output_path}")
    return output_path
