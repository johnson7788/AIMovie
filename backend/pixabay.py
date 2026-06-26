"""Pixabay image search integration."""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

PIXABAY_API_KEY = "32260505-27c339ca85b95b5e9455472c8"
_PIXABAY_API_URL = "https://pixabay.com/api/"


async def search_images(
    q: str,
    *,
    image_type: str = "photo",
    orientation: str = "",
    category: str = "",
    per_page: int = 20,
    page: int = 1,
    safesearch: bool = True,
) -> dict:
    """Search Pixabay for images.

    Returns a dict with ``total``, ``totalHits``, and ``hits`` list.
    Each hit contains: id, preview, webformat, large, tags, author, page.
    """
    params: dict = {
        "key": PIXABAY_API_KEY,
        "q": q,
        "image_type": image_type,
        "per_page": min(max(per_page, 3), 200),
        "page": page,
        "safesearch": str(safesearch).lower(),
    }
    if orientation:
        params["orientation"] = orientation
    if category:
        params["category"] = category

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_PIXABAY_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    hits: List[dict] = []
    for hit in data.get("hits", []):
        hits.append(
            {
                "id": hit["id"],
                "tags": hit.get("tags", ""),
                "preview": hit.get("previewURL", ""),
                "webformat": hit.get("webformatURL", ""),
                "large": hit.get("largeImageURL", ""),
                "author": hit.get("user", ""),
                "page": hit.get("pageURL", ""),
            }
        )

    return {
        "total": data.get("total", 0),
        "totalHits": data.get("totalHits", 0),
        "hits": hits,
    }
