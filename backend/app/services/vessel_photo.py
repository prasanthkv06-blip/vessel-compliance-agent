"""Vessel photo fetcher — MarineTraffic public photo CDN.

Fetches a vessel photo by IMO (no API key required) and returns it
as a base64-encoded data URL suitable for embedding in HTML/PDF.
"""
import base64
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# MarineTraffic public photo CDN — returns JPEG, no auth needed
_PHOTO_URL = "https://photos.marinetraffic.com/ais/showphoto.aspx"

# Minimum byte size — responses smaller than this are placeholder/error images
_MIN_PHOTO_BYTES = 10_000


async def fetch_vessel_photo(imo: str, mmsi: str = "") -> Optional[str]:
    """
    Fetch vessel photo from MarineTraffic CDN.

    Tries IMO first, then MMSI as fallback.
    Returns a base64 data URI string ("data:image/jpeg;base64,...") or None.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
        ),
        "Referer": "https://www.marinetraffic.com/",
    }

    candidates = []
    if imo:
        candidates.append({"imo": imo})
    if mmsi:
        candidates.append({"mmsi": mmsi})

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15) as client:
        for params in candidates:
            try:
                resp = await client.get(_PHOTO_URL, params=params)
                if resp.status_code == 200 and len(resp.content) >= _MIN_PHOTO_BYTES:
                    ct = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                    b64 = base64.b64encode(resp.content).decode()
                    logger.info(
                        "Fetched vessel photo for %s: %d bytes (%s)",
                        params, len(resp.content), ct,
                    )
                    return f"data:{ct};base64,{b64}"
            except Exception as e:
                logger.debug("Photo fetch failed for params %s: %s", params, e)

    logger.info("No vessel photo found for IMO %s", imo)
    return None
