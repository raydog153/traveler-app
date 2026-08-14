import datetime

import pytest
from PIL import ExifTags

from app.services import exif_extract


class FakeExif(dict):
    """Duck-types PIL's Image.Exif enough for exif_extract.py's purposes:
    a dict of IFD0 tags plus get_ifd() for the GPS/Exif sub-IFDs. Building
    real encoded EXIF bytes via Pillow for these round-trips is brittle and
    tests Pillow's writer more than our parsing logic -- this isolates the
    parsing/DMS-conversion/error-handling behavior under test instead."""

    def __init__(self, base=None, gps_ifd=None, exif_ifd=None):
        super().__init__(base or {})
        self._gps_ifd = gps_ifd or {}
        self._exif_ifd = exif_ifd or {}

    def get_ifd(self, tag):
        if tag == ExifTags.IFD.GPSInfo:
            return self._gps_ifd
        if tag == ExifTags.IFD.Exif:
            return self._exif_ifd
        return {}


class FakeImage:
    def __init__(self, exif: FakeExif):
        self._exif = exif

    def getexif(self):
        return self._exif


class TestExtractGps:
    def test_converts_dms_to_decimal_with_north_east_sign(self):
        # Real Pillow GPS IFD values are tuples of IFDRational (float()-able
        # directly) -- plain ints/floats stand in fine for that here.
        gps_ifd = {1: "N", 2: (42, 30, 0), 3: "E", 4: (91, 0, 0)}
        image = FakeImage(FakeExif(gps_ifd=gps_ifd))

        result = exif_extract.extract_gps(image)

        assert result == pytest.approx((42.5, 91.0))

    def test_south_and_west_refs_negate(self):
        gps_ifd = {1: "S", 2: (42, 30, 0), 3: "W", 4: (91, 0, 0)}
        image = FakeImage(FakeExif(gps_ifd=gps_ifd))

        result = exif_extract.extract_gps(image)

        assert result == pytest.approx((-42.5, -91.0))

    def test_missing_gps_ifd_returns_none(self):
        image = FakeImage(FakeExif())

        assert exif_extract.extract_gps(image) is None

    def test_malformed_gps_ifd_does_not_raise(self):
        image = FakeImage(FakeExif(gps_ifd={1: "N", 2: "not-a-tuple"}))

        assert exif_extract.extract_gps(image) is None


class TestExtractCaptureDate:
    def test_parses_date_time_original_from_exif_subifd(self):
        image = FakeImage(FakeExif(exif_ifd={36867: "2026:08:13 14:10:56"}))

        assert exif_extract.extract_capture_date(image) == datetime.date(2026, 8, 13)

    def test_falls_back_to_ifd0_datetime_when_no_capture_time(self):
        image = FakeImage(FakeExif(base={306: "2025:01:02 03:04:05"}))

        assert exif_extract.extract_capture_date(image) == datetime.date(2025, 1, 2)

    def test_no_date_anywhere_returns_none(self):
        image = FakeImage(FakeExif())

        assert exif_extract.extract_capture_date(image) is None

    def test_malformed_date_string_does_not_raise(self):
        image = FakeImage(FakeExif(exif_ifd={36867: "not-a-date"}))

        assert exif_extract.extract_capture_date(image) is None
