import logging
import requests
import subprocess
import os
import re
import shutil
import tempfile
from typing import List, Optional, Union
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


def ensure_valid_cached_video(path: str, label: str = "cached video") -> bool:
    """Return True when an existing cached video is readable; delete corrupt leftovers."""
    if not os.path.exists(path):
        return False
    try:
        _probe_video(path)
        return True
    except Exception as exc:
        logging.warning("Removing invalid %s at %s: %s", label, path, exc)
        try:
            os.remove(path)
        except OSError as remove_exc:
            logging.warning("Could not remove invalid %s at %s: %s", label, path, remove_exc)
        return False


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
    if duration is not None:
        try:
            return float(duration)
        except (TypeError, ValueError):
            pass

    ffmpeg = _resolve_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, '-hide_banner', '-i', path],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=60,
    )
    parsed = _parse_ffmpeg_duration(result.stderr or "")
    if parsed is not None:
        return parsed

    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(os.path.abspath(path))
        try:
            return float(clip.duration) if clip.duration is not None else None
        finally:
            clip.close()
    except Exception as exc:
        logging.warning("Could not determine duration for %s: %s", path, exc)
        return None


def _parse_ffmpeg_duration(stderr_text: str) -> Optional[float]:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr_text or "")
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    try:
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
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


def _run_ffmpeg_frame_extract(cmd: List[str], output_path: str) -> Optional[str]:
    """Run ffmpeg; return stderr tail on failure."""
    stderr_path = output_path + ".ffmpeg.stderr.txt"
    with open(stderr_path, "w", encoding="utf-8") as stderr_f:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=stderr_f,
            timeout=120,
        )
    stderr_text = _read_stderr_file(stderr_path)
    if os.path.exists(stderr_path):
        os.remove(stderr_path)
    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return None
    tail = stderr_text[-1500:] if stderr_text else ""
    if os.path.exists(output_path):
        os.remove(output_path)
    return tail or "unknown ffmpeg error"


def _extract_last_frame_by_dumping_frames(video_path: str, output_path: str) -> None:
    """Most reliable path for short generated clips: export frames, keep the last valid PNG."""
    ffmpeg = _resolve_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmpdir:
        frame_pattern = os.path.join(tmpdir, "frame_%06d.png")
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            video_path,
            "-map",
            "0:v:0",
            "-vsync",
            "0",
            frame_pattern,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        frames = [
            os.path.join(tmpdir, name)
            for name in sorted(os.listdir(tmpdir))
            if name.endswith(".png")
        ]
        frames = [path for path in frames if os.path.getsize(path) > 0]
        if result.returncode != 0 or not frames:
            tail = (result.stderr or "")[-1500:]
            raise RuntimeError(_meaningful_ffmpeg_error(tail))
        shutil.copyfile(frames[-1], output_path)


def _extract_last_frame_moviepy(video_path: str, output_path: str) -> None:
    """Fallback frame grab when ffmpeg single-frame export fails."""
    from moviepy import VideoFileClip
    from PIL import Image

    clip = VideoFileClip(os.path.abspath(video_path))
    try:
        if clip.duration is None or clip.duration <= 0:
            timestamp = 0.0
        else:
            fps = clip.fps or 24
            timestamp = max(0.0, float(clip.duration) - (1.0 / fps))
        frame = clip.get_frame(timestamp)
        Image.fromarray(frame.astype("uint8"), "RGB").save(output_path)
    finally:
        clip.close()


def extract_last_frame_from_video(video_path: str, output_path: str) -> str:
    """Save the final visible frame from a video clip as a PNG reference."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    abs_video = os.path.abspath(video_path)
    abs_output = os.path.abspath(output_path)
    parent = os.path.dirname(abs_output)
    if parent:
        os.makedirs(parent, exist_ok=True)

    errors: List[str] = []
    try:
        _extract_last_frame_by_dumping_frames(abs_video, abs_output)
        if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
            logging.info(
                "Extracted last frame from %s -> %s (ffmpeg frame dump)",
                video_path,
                abs_output,
            )
            return abs_output
    except Exception as exc:
        errors.append(f"ffmpeg frame dump: {exc}")

    ffmpeg = _resolve_ffmpeg_exe()
    png_args = ["-map", "0:v:0", "-frames:v", "1", "-f", "image2", "-c:v", "png"]

    strategies: List[List[str]] = [
        [ffmpeg, "-y", "-sseof", "-0.08", "-i", abs_video, *png_args, abs_output],
    ]

    duration = _format_duration_seconds(abs_video)
    if duration is not None and duration > 0.12:
        seek = max(0.0, duration - 0.08)
        strategies.append(
            [ffmpeg, "-y", "-ss", f"{seek:.3f}", "-i", abs_video, *png_args, abs_output],
        )

    for index, cmd in enumerate(strategies, start=1):
        error_tail = _run_ffmpeg_frame_extract(cmd, abs_output)
        if error_tail is None:
            logging.info(
                "Extracted last frame from %s -> %s (ffmpeg strategy %s)",
                video_path,
                abs_output,
                index,
            )
            return abs_output
        errors.append(f"ffmpeg {index}: {_meaningful_ffmpeg_error(error_tail)}")

    try:
        _extract_last_frame_moviepy(abs_video, abs_output)
        if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
            logging.info(
                "Extracted last frame from %s -> %s (moviepy fallback)",
                video_path,
                abs_output,
            )
            return abs_output
    except Exception as exc:
        errors.append(f"moviepy: {exc}")

    raise RuntimeError(
        f"Failed to extract last frame from {video_path}: {' | '.join(errors)}"
    )


def _meaningful_ffmpeg_error(stderr_text: str) -> str:
    """Prefer explicit error lines over codec banner noise."""
    for line in reversed(stderr_text.splitlines()):
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            continue
        if any(token in lower for token in ("error", "invalid", "failed", "could not", "no such file")):
            return stripped
    compact = " ".join(stderr_text.split())
    return compact[-240:] if compact else "unknown ffmpeg error"


def concat_videos(video_paths: List[str], output_path: str,
                  target_width: int = 720, target_height: int = 1280,
                  preserve_audio: bool = True,
                  crossfade_seconds: Union[float, List[float]] = 0.35) -> str:
    """Concatenate videos with per-input normalize + optional crossfade.

    ``crossfade_seconds`` may be a float (uniform) or a list of length N-1
    with per-join fade durations. Use 0 for a hard cut between adjacent clips.
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
    if isinstance(crossfade_seconds, list):
        fade_list = [float(value) for value in crossfade_seconds]
        if len(fade_list) != max(0, n - 1):
            raise ValueError(
                f"crossfade_seconds list must have length {n - 1}, got {len(fade_list)}"
            )
    else:
        fade_list = [float(crossfade_seconds)] * (n - 1) if n > 1 else []

    cmd = [ffmpeg, '-y']
    for path in abs_paths:
        cmd.extend(['-i', path])

    vf_parts = []
    for i in range(n):
        vf_parts.append(
            f"[{i}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
            f"setpts=PTS-STARTPTS,fps=24,settb=AVTB,format=yuv420p[v{i}]"
        )

    use_crossfade = (
        n == 2
        and any(fade > 0 for fade in fade_list)
        and all(d is not None for d in input_durations)
    )
    if n >= 2:
        logging.info("Concat crossfade schedule: %s", [round(f, 3) for f in fade_list])
    if n > 2 and any(fade > 0 for fade in fade_list):
        logging.warning(
            "Crossfade disabled for %d clips; using stable concat to avoid chained xfade frame loss.",
            n,
        )
    if n >= 2 and any(fade > 0 for fade in fade_list) and not all(d is not None for d in input_durations):
        logging.warning(
            "Crossfade disabled because one or more input durations are unknown: %s",
            input_durations,
        )
    uniform_fade = (
        use_crossfade
        and len(set(round(f, 4) for f in fade_list)) == 1
        and fade_list[0] > 0
        and all(d > fade_list[0] for d in input_durations)
    )

    if uniform_fade:
        fade = fade_list[0]
        v_chain = vf_parts[:]
        current_v = "v0"
        accumulated = input_durations[0]
        for i in range(1, n):
            out_v = f"vx{i}"
            tmp_v = f"vxf{i}"
            offset = max(0.0, accumulated - fade)
            v_chain.append(
                f"[{current_v}][v{i}]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[{tmp_v}];"
                f"[{tmp_v}]fps=24,settb=AVTB,format=yuv420p[{out_v}]"
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
    elif use_crossfade:
        fade = max(f for f in fade_list if f > 0)
        v_chain = vf_parts[:]
        a_chain = []
        if preserve_audio_effective:
            for i in range(n):
                a_chain.append(
                    f"[{i}:a]aresample=44100:async=1:first_pts=0,"
                    f"aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]"
                )
        current_v = "v0"
        current_a = "a0" if preserve_audio_effective else None
        accumulated = input_durations[0]
        for i in range(1, n):
            join_fade = fade_list[i - 1]
            if join_fade > 0 and accumulated > join_fade and input_durations[i] > join_fade:
                out_v = f"vx{i}"
                tmp_v = f"vxf{i}"
                offset = max(0.0, accumulated - join_fade)
                v_chain.append(
                    f"[{current_v}][v{i}]xfade=transition=fade:duration={join_fade:.3f}:offset={offset:.3f}[{tmp_v}];"
                    f"[{tmp_v}]fps=24,settb=AVTB,format=yuv420p[{out_v}]"
                )
                current_v = out_v
                accumulated = accumulated + input_durations[i] - join_fade
                if preserve_audio_effective and current_a is not None:
                    out_a = f"ax{i}"
                    a_chain.append(
                        f"[{current_a}][a{i}]acrossfade=d={join_fade:.3f}:c1=tri:c2=tri[{out_a}]"
                    )
                    current_a = out_a
            else:
                out_v = f"vc{i}"
                v_chain.append(f"[{current_v}][v{i}]concat=n=2:v=1:a=0[{out_v}]")
                current_v = out_v
                accumulated = accumulated + input_durations[i]
                if preserve_audio_effective and current_a is not None:
                    out_a = f"ac{i}"
                    a_chain.append(f"[{current_a}][a{i}]concat=n=2:v=0:a=1[{out_a}]")
                    current_a = out_a
        filter_complex = ";".join(v_chain + a_chain)
        if preserve_audio_effective and current_a is not None:
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', f'[{current_v}]', '-map', f'[{current_a}]',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart',
                output_path,
            ])
        else:
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', f'[{current_v}]',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-an',
                '-movflags', '+faststart',
                output_path,
            ])
        logging.info(
            "Using variable crossfade schedule %s between %d clips (expected duration ~%.2fs)",
            [round(f, 3) for f in fade_list], n, accumulated,
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
        if use_crossfade and _is_xfade_cfr_error(stderr_text):
            logging.warning(
                "ffmpeg xfade failed because of invalid frame-rate metadata; "
                "retrying final concat without crossfade. Error tail: %s",
                _meaningful_ffmpeg_error(tail),
            )
            if os.path.exists(output_path):
                os.remove(output_path)
            return concat_videos(
                video_paths,
                output_path,
                target_width=target_width,
                target_height=target_height,
                preserve_audio=preserve_audio,
                crossfade_seconds=0.0,
            )
        raise RuntimeError(f"ffmpeg concat failed: {tail}")

    out_duration = _format_duration_seconds(output_path)
    expected = _concat_expected_duration(
        input_durations,
        fade_list if use_crossfade else [0.0] * max(0, len(fade_list)),
    )
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


def _is_xfade_cfr_error(stderr_text: str) -> bool:
    lower = (stderr_text or "").lower()
    return "xfade" in lower and (
        "constant frame rate" in lower
        or "current rate of 1/0" in lower
        or "failed to configure output pad" in lower
    )


def _concat_expected_duration(
    input_durations: List[Optional[float]], fade_list: List[float]
) -> Optional[float]:
    if not input_durations or any(d is None for d in input_durations):
        return None
    total = float(sum(input_durations))
    if fade_list and len(input_durations) >= 2:
        for index, fade in enumerate(fade_list):
            if fade > 0 and index < len(input_durations) - 1:
                total -= fade
    return total
