"""Best-effort EXIF extraction for fill-up photos.

Used only by the `POST /api/gas/fillups/scan-odometer` endpoint to prefill
the add-fillup form -- GPS coordinates and capture date are read straight
out of the uploaded image's EXIF data, then the image itself is discarded
(never written to disk or a DB column). Phone photos frequently have this
metadata stripped (messaging apps, screenshots, privacy settings), so every
extractor here returns None rather than raising on anything missing or
malformed -- the scan endpoint reports that as a warning and the user fills
the gap in manually, it never blocks adding a fill-up.
"""

import datetime as dt
import logging

import pillow_heif
from PIL import ExifTags, Image

# Registers HEIC/HEIF decoding with Pillow -- iPhones (the realistic source
# of fill-up photos) save in this format by default, and stock Pillow can't
# open it otherwise. Idempotent, safe to call from multiple modules.
pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

_DATE_TIME_ORIGINAL_TAG = 36867  # Exif SubIFD
_DATE_TIME_TAG = 306  # IFD0, falls back to "last modified" if no capture time
_EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"


def _dms_to_decimal(dms, ref: str | bytes) -> float:
    degrees, minutes, seconds = (float(part) for part in dms)
    decimal = degrees + minutes / 60 + seconds / 3600
    ref_str = ref.decode() if isinstance(ref, bytes) else ref
    if ref_str in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_gps(image: Image.Image) -> tuple[float, float] | None:
    """Returns (lat, lon) in signed decimal degrees from the image's GPS
    EXIF IFD, or None if absent/malformed."""
    try:
        gps_ifd = image.getexif().get_ifd(ExifTags.IFD.GPSInfo)
        lat = _dms_to_decimal(gps_ifd[2], gps_ifd[1])
        lon = _dms_to_decimal(gps_ifd[4], gps_ifd[3])
    except Exception as exc:
        logger.warning("could not extract GPS EXIF: %s", exc)
        return None
    return lat, lon


def extract_capture_date(image: Image.Image) -> dt.date | None:
    """Parses DateTimeOriginal (falling back to DateTime) into a date, or
    None if absent/malformed."""
    try:
        exif = image.getexif()
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        raw = exif_ifd.get(_DATE_TIME_ORIGINAL_TAG) or exif.get(_DATE_TIME_TAG)
        if not raw:
            return None
        return dt.datetime.strptime(raw, _EXIF_DATE_FORMAT).date()
    except Exception as exc:
        logger.warning("could not extract capture date EXIF: %s", exc)
        return None
