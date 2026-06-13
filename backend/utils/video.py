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


def _input_has_audio(path: str) -> bool:
    """Return True if the file contains at least one audio stream."""
    ffprobe = _resolve_ffprobe_exe()
    if ffprobe:
        result = subprocess.run(
            [
                ffprobe, '-v', 'error', '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', path,
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
        )
        return result.returncode == 0 and 'audio' in (result.stdout or '').lower()

    ffmpeg = _resolve_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, '-hide_banner', '-i', path],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=60,
    )
    return 'Audio:' in (result.stderr or '')


def _format_duration_seconds(path: str) -> Optional[float]:
    info = _probe_video(path)
    duration = info.get('format', {}).get('duration')
    if duration is None:
        return None
    try:
        return float(duration)
    except (TypeError, ValueError):
        return None


def _normalize_video_to_size(
    input_path: str,
    output_path: str,
    target_width: int,
    target_height: int,
    preserve_audio: bool = True,
) -> str:
    """Re-encode a single clip to the exact target canvas size."""
    preserve_audio_effective = preserve_audio and _input_has_audio(input_path)
    ffmpeg = _resolve_ffmpeg_exe()
    vf = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24"
    )
    cmd = [ffmpeg, "-y", "-i", input_path, "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p"]
    if preserve_audio_effective:
        cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ar", "44100"])
    else:
        cmd.append("-an")
    cmd.extend(["-movflags", "+faststart", output_path])

    stderr_path = output_path + ".ffmpeg.stderr.txt"
    with open(stderr_path, "w", encoding="utf-8") as stderr_f:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=stderr_f, timeout=600)
    stderr_text = _read_stderr_file(stderr_path)
    if os.path.exists(stderr_path):
        os.remove(stderr_path)
    if result.returncode != 0:
        tail = stderr_text[-2000:] if len(stderr_text) > 2000 else stderr_text
        raise RuntimeError(f"ffmpeg normalize failed: {tail}")
    return output_path


def concat_videos(video_paths: List[str], output_path: str,
                  target_width: int = 720, target_height: int = 1280,
                  preserve_audio: bool = True,
                  crossfade_seconds: float = 0.35) -> str:
    """Concatenate videos with per-input normalize + optional crossfade.

    Normalizes resolution/fps and resets PTS on each clip. When
    crossfade_seconds > 0, uses xfade/acrossfade between adjacent clips to
    reduce visible hard cuts between shots.
    """
    if not video_paths:
        raise ValueError("video_paths must not be empty")

    if len(video_paths) == 1:
        return _normalize_video_to_size(
            video_paths[0],
            output_path,
            target_width,
            target_height,
            preserve_audio=preserve_audio,
        )

    logging.info(f"Concatenating {len(video_paths)} videos to {output_path}")

    abs_paths = [os.path.abspath(path) for path in video_paths]
    for path in abs_paths:
        _probe_video(path)

    input_durations = [_format_duration_seconds(path) for path in abs_paths]
    if all(d is not None for d in input_durations):
        logging.info(
            "Input durations (s): %s (sum=%.2fs)",
            [f"{d:.2f}" for d in input_durations],
            sum(input_durations),
        )

    preserve_audio_effective = preserve_audio and all(
        _input_has_audio(path) for path in abs_paths
    )
    if preserve_audio and not preserve_audio_effective:
        logging.warning(
            "Some inputs lack audio streams; concatenating video only (-an)."
        )

    ffmpeg = _resolve_ffmpeg_exe()
    n = len(abs_paths)
    cmd = [ffmpeg, '-y']
    for path in abs_paths:
        cmd.extend(['-i', path])

    vf_parts = []
    for i in range(n):
        vf_parts.append(
            f"[{i}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,"
            f"setpts=PTS-STARTPTS[v{i}]"
        )

    use_crossfade = (
        crossfade_seconds > 0
        and n >= 2
        and all(d is not None and d > crossfade_seconds for d in input_durations)
    )

    if use_crossfade:
        fade = crossfade_seconds
        v_chain = vf_parts[:]
        current_v = "v0"
        accumulated = input_durations[0]
        for i in range(1, n):
            out_v = f"vx{i}"
            offset = max(0.0, accumulated - fade)
            v_chain.append(
                f"[{current_v}][v{i}]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[{out_v}]"
            )
            current_v = out_v
            accumulated = accumulated + input_durations[i] - fade

        if preserve_audio_effective:
            af_parts = []
            for i in range(n):
                af_parts.append(
                    f"[{i}:a]aresample=44100:async=1:first_pts=0,"
                    f"aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]"
                )
            a_chain = af_parts[:]
            current_a = "a0"
            for i in range(1, n):
                out_a = f"ax{i}"
                a_chain.append(
                    f"[{current_a}][a{i}]acrossfade=d={fade:.3f}:c1=tri:c2=tri[{out_a}]"
                )
                current_a = out_a
            filter_complex = ";".join(v_chain + a_chain)
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', f'[{current_v}]', '-map', f'[{current_a}]',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart',
                output_path,
            ])
        else:
            filter_complex = ";".join(v_chain)
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', f'[{current_v}]',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-an',
                '-movflags', '+faststart',
                output_path,
            ])
        logging.info(
            "Using %.2fs crossfade between %d clips (expected duration ~%.2fs)",
            fade, n, accumulated,
        )
    elif preserve_audio_effective:
        af_parts = []
        for i in range(n):
            af_parts.append(
                f"[{i}:a]aresample=44100:async=1:first_pts=0,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]"
            )
        v_in = ''.join(f'[v{i}]' for i in range(n))
        a_in = ''.join(f'[a{i}]' for i in range(n))
        filter_complex = ';'.join(vf_parts + af_parts + [
            f'{v_in}concat=n={n}:v=1:a=0[vout]',
            f'{a_in}concat=n={n}:v=0:a=1[aout]',
        ])
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[vout]', '-map', '[aout]',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            output_path,
        ])
    else:
        v_in = ''.join(f'[v{i}]' for i in range(n))
        filter_complex = ';'.join(vf_parts + [f'{v_in}concat=n={n}:v=1:a=0[vout]'])
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[vout]',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
            '-an',
            '-movflags', '+faststart',
            output_path,
        ])

    logging.info(f"Running ffmpeg: {' '.join(cmd)}")

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

    stderr_text = _read_stderr_file(stderr_path)
    if os.path.exists(stderr_path):
        os.remove(stderr_path)

    if result.returncode != 0:
        tail = stderr_text[-2000:] if len(stderr_text) > 2000 else stderr_text
        raise RuntimeError(f"ffmpeg concat failed: {tail}")

    out_duration = _format_duration_seconds(output_path)
    expected = _concat_expected_duration(input_durations, crossfade_seconds if use_crossfade else 0.0)
    if out_duration is not None and expected is not None:
        logging.info(
            "Concatenation complete: %s (duration=%.2fs, expected~%.2fs)",
            output_path, out_duration, expected,
        )
        if out_duration > expected * 1.15:
            logging.warning(
                "Output duration %.2fs exceeds expected ~%.2fs by >15%%",
                out_duration, expected,
            )
    else:
        logging.info(f"Concatenation complete: {output_path}")

    return output_path


def _concat_expected_duration(
    input_durations: List[Optional[float]], crossfade_seconds: float
) -> Optional[float]:
    if not input_durations or any(d is None for d in input_durations):
        return None
    total = float(sum(input_durations))
    if crossfade_seconds > 0 and len(input_durations) >= 2:
        total -= crossfade_seconds * (len(input_durations) - 1)
    return total
