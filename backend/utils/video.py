import logging
import requests
import subprocess
import os
import tempfile
from typing import List
from tenacity import retry


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

    # Write ffmpeg concat file
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    # Normalize all inputs to target resolution during concatenation
    vf = (f"scale={target_width}:{target_height}"
          f":force_original_aspect_ratio=decrease,"
          f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2")

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', concat_file,
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-an',  # no audio
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(concat_file)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")

    logging.info(f"Concatenation complete: {output_path}")
    return output_path
