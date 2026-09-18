"""Tests for GCS integration: signed URLs, expiry, and local fallback."""

from datetime import timedelta

import pytest

import app.gcs as gcs
from app.config import SIGNED_URL_EXPIRY_HOURS


class _FakeBlob:
    def __init__(self, name):
        self.name = name
        self.kwargs = None

    def generate_signed_url(self, **kwargs):
        self.kwargs = kwargs
        return f"signed://{self.name}"


class _FakeBucket:
    def __init__(self):
        self.blobs = {}

    def blob(self, name):
        blob = self.blobs.get(name)
        if blob is None:
            blob = self.blobs[name] = _FakeBlob(name)
        return blob


class _FakeClient:
    def __init__(self):
        self.buckets = {}

    def bucket(self, name):
        bucket = self.buckets.get(name)
        if bucket is None:
            bucket = self.buckets[name] = _FakeBucket()
        return bucket


@pytest.fixture
def fake_gcs(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(gcs, "GCS_BUCKET", "test-bucket")
    monkeypatch.setattr(gcs, "_on_gcp", lambda: True)
    monkeypatch.setattr(gcs, "_get_client", lambda: client)
    monkeypatch.setattr(gcs, "_get_signing_credentials", lambda: object())
    return client


def _last_blob(client, name):
    return client.buckets["test-bucket"].blobs[name]


class TestOnGcp:
    def test_true_with_k_service(self, monkeypatch):
        monkeypatch.setattr(gcs, "_on_cloud_run", None)
        monkeypatch.setenv("K_SERVICE", "store-catalog-backend")
        assert gcs._on_gcp() is True

    def test_false_without_k_service(self, monkeypatch):
        monkeypatch.setattr(gcs, "_on_cloud_run", None)
        monkeypatch.delenv("K_SERVICE", raising=False)
        assert gcs._on_gcp() is False


class TestResolveImageUrl:
    def test_none_url_returns_none(self):
        assert gcs.resolve_image_url(None) is None

    def test_no_bucket_returns_url_unchanged(self, monkeypatch):
        monkeypatch.setattr(gcs, "GCS_BUCKET", "")
        assert gcs.resolve_image_url("/uploads/x.jpg") == "/uploads/x.jpg"

    def test_fallback_without_google_libs(self, monkeypatch):
        monkeypatch.setattr(gcs, "GCS_BUCKET", "test-bucket")
        monkeypatch.setattr(gcs, "_on_gcp", lambda: True)

        def _no_google():
            raise ModuleNotFoundError("No module named 'google'")

        monkeypatch.setattr(gcs, "_get_client", _no_google)
        assert gcs.resolve_image_url("/uploads/x.jpg") == "/uploads/x.jpg"

    def test_off_gcp_returns_url_without_signing(self, monkeypatch):
        monkeypatch.setattr(gcs, "GCS_BUCKET", "test-bucket")
        monkeypatch.setattr(gcs, "_on_gcp", lambda: False)

        def _should_not_be_called():
            raise AssertionError("_get_client must not be called off-GCP")

        monkeypatch.setattr(gcs, "_get_client", _should_not_be_called)
        assert gcs.resolve_image_url("/uploads/x.jpg") == "/uploads/x.jpg"

    def test_credentials_error_falls_back(self, monkeypatch):
        monkeypatch.setattr(gcs, "GCS_BUCKET", "test-bucket")
        monkeypatch.setattr(gcs, "_on_gcp", lambda: True)
        monkeypatch.setattr(gcs, "_get_client", lambda: _FakeClient())

        def _no_credentials():
            raise RuntimeError("Default credentials were not found.")

        monkeypatch.setattr(gcs, "_get_signing_credentials", _no_credentials)
        assert gcs.resolve_image_url("/uploads/x.jpg") == "/uploads/x.jpg"

    def test_signed_with_default_expiry(self, fake_gcs):
        assert gcs.resolve_image_url("/uploads/avatar_1.jpg") == "signed://avatar_1.jpg"
        blob = _last_blob(fake_gcs, "avatar_1.jpg")
        assert blob.kwargs["expiration"] == timedelta(hours=SIGNED_URL_EXPIRY_HOURS)
        assert blob.kwargs["credentials"] is not None

    def test_signed_with_expires_hours(self, fake_gcs):
        assert gcs.resolve_image_url("/uploads/img.jpg", expires_hours=168) == "signed://img.jpg"
        blob = _last_blob(fake_gcs, "img.jpg")
        assert blob.kwargs["expiration"] == timedelta(hours=168)


class TestGenerateSignedUrl:
    def test_explicit_expiry(self, fake_gcs):
        url = gcs.generate_signed_url("obj", expires_hours=5)
        assert url == "signed://obj"
        blob = _last_blob(fake_gcs, "obj")
        assert blob.kwargs["expiration"] == timedelta(hours=5)

    def test_default_expiry(self, fake_gcs):
        gcs.generate_signed_url("obj")
        blob = _last_blob(fake_gcs, "obj")
        assert blob.kwargs["expiration"] == timedelta(hours=SIGNED_URL_EXPIRY_HOURS)