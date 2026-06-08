import logging
import os
import requests
import base64
import mimetypes
from tenacity import retry
from io import BytesIO
from typing import List, Optional, Dict
import cv2
from PIL import Image


@retry
def download_image(url, save_path):
    try:
        logging.info(f"Downloading image from {url} to {save_path}")

        response = requests.get(url, stream=True, proxies={"http": None, "https": None})
        response.raise_for_status() # Check for HTTP errors

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        logging.info(f"Image downloaded successfully to {save_path}")

    except Exception as e:
        logging.error(f"Error downloading image: {e}")
        raise e


def image_path_to_b64(image_path, mime: bool = True) -> str:
    with open(image_path, 'rb') as image_file:
        b64 = base64.b64encode(image_file.read()).decode('utf-8')

    if mime:
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        return f"data:{mime_type};base64,{b64}"

    return b64


def pil_to_b64(image, mime: bool = True) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    if mime:
        return f"data:image/png;base64,{b64}"

    return b64


def save_base64_image(b64_string, save_path):
    # If the base64 string has a data URL prefix, remove it
    if ',' in b64_string:
        b64_string = b64_string.split(',')[1]

    with open(save_path, 'wb') as image_file:
        image_file.write(base64.b64decode(b64_string))


def image_output_to_pil(image_output) -> Image.Image:
    """Convert any ImageOutput format to a PIL Image.

    Args:
        image_output: ImageOutput object with fmt in ("b64", "url", "pil", "np")

    Returns:
        PIL.Image object
    """
    fmt = image_output.fmt
    data = image_output.data

    if fmt == "pil":
        return data
    elif fmt == "np":
        # OpenCV BGR -> PIL RGB
        return Image.fromarray(cv2.cvtColor(data, cv2.COLOR_BGR2RGB))
    elif fmt == "b64":
        b64_str = data
        if ',' in b64_str:
            b64_str = b64_str.split(',')[1]
        return Image.open(BytesIO(base64.b64decode(b64_str)))
    elif fmt == "url":
        resp = requests.get(data, proxies={"http": None, "https": None})
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    else:
        raise ValueError(f"Unsupported ImageOutput format: {fmt}")


def crop_turnaround_views(
    sheet_pil: Image.Image,
    character_dir: str,
    view_names: Optional[List[str]] = None,
    horizontal: bool = True,
) -> Dict[str, str]:
    """Crop a turnaround sheet into individual view portraits and save to disk.

    Splits the image into equal-width (or equal-height) strips and saves each
    as a separate PNG file.

    Args:
        sheet_pil: PIL Image of the turnaround sheet with multiple views.
        character_dir: Directory path to save the cropped view images.
        view_names: Names for each view (default: ["front", "side", "back"]).
        horizontal: True if views are arranged left-to-right, False for top-to-bottom.

    Returns:
        Dict mapping view_name -> absolute file path, e.g. {"front": "/path/to/front.png", ...}
    """
    if view_names is None:
        view_names = ["front", "side", "back"]

    os.makedirs(character_dir, exist_ok=True)

    if horizontal:
        width, height = sheet_pil.size
        view_width = width // len(view_names)
        views = []
        for i in range(len(view_names)):
            left = i * view_width
            right = (i + 1) * view_width if i < len(view_names) - 1 else width
            views.append(sheet_pil.crop((left, 0, right, height)))
    else:
        width, height = sheet_pil.size
        view_height = height // len(view_names)
        views = []
        for i in range(len(view_names)):
            top = i * view_height
            bottom = (i + 1) * view_height if i < len(view_names) - 1 else height
            views.append(sheet_pil.crop((0, top, width, bottom)))

    paths = {}
    for view_name, view_pil in zip(view_names, views):
        path = os.path.join(character_dir, f"{view_name}.png")
        view_pil.save(path, "PNG")
        paths[view_name] = path

    return paths

