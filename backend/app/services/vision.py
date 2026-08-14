"""Odometer-reading OCR via Google Gemini vision.

Used only by the `POST /api/gas/fillups/scan-odometer` endpoint. Never
raises -- a missing API key, network failure, timeout, or a reading Gemini
can't confidently make out all fall back to (None, [warning]) so a bad scan
never blocks adding a fill-up; the user just types the odometer manually.
"""

import io
import logging
import re

import google.generativeai as genai
import pillow_heif
from PIL import Image

from app.config import settings

# Registers HEIC/HEIF decoding with Pillow -- see exif_extract.py for why.
pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

# "-latest" alias rather than a pinned version -- gemini-1.5-flash (the
# original pin) was retired by Google and started 404ing with no code change
# on our side; tracking the rolling flash alias avoids repeating that.
_MODEL_NAME = "gemini-flash-latest"
_MAX_DIMENSION = 1024
_JPEG_QUALITY = 80
_REQUEST_TIMEOUT_SECONDS = 15
_NUMERIC_RE = re.compile(r"^\d+(\.\d+)?$")
_PROMPT = (
    "This is a photo of a car odometer. Reply with ONLY the numeric mileage "
    "reading shown (digits only, no units, no commentary). If you cannot "
    "read it, reply exactly NONE."
)


def _resize_for_upload(image_bytes: bytes) -> bytes:
    """Downscales/re-encodes as JPEG before sending to Gemini, regardless of
    the source format/size -- bounds payload size, latency, and cost."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=_JPEG_QUALITY)
    return out.getvalue()


def scan_odometer_photo(image_bytes: bytes) -> tuple[float | None, list[str]]:
    """Returns (odometer_miles, warnings). Never raises."""
    if not settings.google_ai_api_key:
        logger.warning("google_ai_api_key not configured -- skipping odometer OCR")
        return None, ["Odometer photo scanning isn't configured"]

    try:
        jpeg_bytes = _resize_for_upload(image_bytes)
        genai.configure(api_key=settings.google_ai_api_key)
        model = genai.GenerativeModel(_MODEL_NAME)
        response = model.generate_content(
            [_PROMPT, {"mime_type": "image/jpeg", "data": jpeg_bytes}],
            request_options={"timeout": _REQUEST_TIMEOUT_SECONDS},
        )
        text = (response.text or "").strip()
    except Exception as exc:
        logger.warning("odometer OCR request failed: %s", exc)
        return None, ["Could not read odometer from photo"]

    if text == "NONE" or not _NUMERIC_RE.match(text):
        logger.warning("odometer OCR returned an unreadable response: %r", text)
        return None, ["Could not read odometer from photo"]

    return float(text), []
