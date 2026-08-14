import io

import pytest
from PIL import Image

from app.services import vision


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModel:
    def __init__(self, text=None, raise_exc=None):
        self._text = text
        self._raise_exc = raise_exc

    def generate_content(self, *_args, **_kwargs):
        if self._raise_exc:
            raise self._raise_exc
        return FakeResponse(self._text)


def _tiny_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def configured_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.settings, "google_ai_api_key", "fake-key")


def test_reads_valid_integer_reading(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.genai, "GenerativeModel", lambda *_a, **_k: FakeModel(text="123456"))

    miles, warnings = vision.scan_odometer_photo(_tiny_jpeg_bytes())

    assert miles == pytest.approx(123456)
    assert warnings == []


def test_reads_decimal_reading(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.genai, "GenerativeModel", lambda *_a, **_k: FakeModel(text="123456.7"))

    miles, warnings = vision.scan_odometer_photo(_tiny_jpeg_bytes())

    assert miles == pytest.approx(123456.7)
    assert warnings == []


def test_none_response_returns_warning_not_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.genai, "GenerativeModel", lambda *_a, **_k: FakeModel(text="NONE"))

    miles, warnings = vision.scan_odometer_photo(_tiny_jpeg_bytes())

    assert miles is None
    assert warnings == ["Could not read odometer from photo"]


def test_non_numeric_response_returns_warning_not_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.genai, "GenerativeModel", lambda *_a, **_k: FakeModel(text="looks blurry"))

    miles, warnings = vision.scan_odometer_photo(_tiny_jpeg_bytes())

    assert miles is None
    assert warnings == ["Could not read odometer from photo"]


def test_api_exception_does_not_raise(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.genai, "GenerativeModel", lambda *_a, **_k: FakeModel(raise_exc=TimeoutError("boom")))

    miles, warnings = vision.scan_odometer_photo(_tiny_jpeg_bytes())

    assert miles is None
    assert warnings == ["Could not read odometer from photo"]


def test_missing_api_key_short_circuits_without_calling_gemini(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vision.settings, "google_ai_api_key", "")

    def fail_if_called(*_a, **_k):
        raise AssertionError("should not call Gemini without an API key configured")

    monkeypatch.setattr(vision.genai, "GenerativeModel", fail_if_called)

    miles, warnings = vision.scan_odometer_photo(_tiny_jpeg_bytes())

    assert miles is None
    assert warnings == ["Odometer photo scanning isn't configured"]
