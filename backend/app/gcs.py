"""Google Cloud Storage integration — upload, download, and signed URL generation.

All functions are no-ops when ``GCS_BUCKET`` is not configured, allowing the
application to fall back to local disk storage in development.
"""

import logging
import time
from datetime import timedelta

from app.config import GCS_BUCKET, SIGNING_CREDENTIALS_LIFETIME, SIGNED_URL_EXPIRY_HOURS

logger = logging.getLogger(__name__)

_client = None
_signing_credentials = None
_signing_expiry = 0


def _get_client():
    """Lazy-initialize the GCS client (avoids import-time credential checks)."""
    global _client
    if _client is None:
        from google.cloud import storage
        _client = storage.Client()
    return _client


def _get_service_account_email():
    """Get the runtime service account email from the metadata server."""
    import urllib.request
    req = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
        headers={"Metadata-Flavor": "Google"},
    )
    return urllib.request.urlopen(req, timeout=5).read().decode()


def _get_signing_credentials():
    """Build impersonated credentials that can sign via IAM signBlob.

    On Cloud Run the compute-engine default credentials have no private
    key.  Impersonating the runtime service account lets us use the IAM
    Credentials signBlob API for URL signing.

    Requires:
      - IAM Service Account Credentials API enabled on the project
      - The runtime service account has ``roles/iam.serviceAccountTokenCreator``
        on itself (project-level binding).

    The credentials are cached and refreshed automatically after
    ``SIGNING_CREDENTIALS_LIFETIME`` seconds (with a 60s buffer).
    """
    global _signing_credentials, _signing_expiry

    now = time.time()
    if _signing_credentials and now < _signing_expiry - 60:
        return _signing_credentials

    from google.auth import impersonated_credentials
    from google.auth import compute_engine

    source_credentials = compute_engine.Credentials()
    service_account_email = _get_service_account_email()

    _signing_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=service_account_email,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        lifetime=SIGNING_CREDENTIALS_LIFETIME,
    )
    _signing_expiry = now + SIGNING_CREDENTIALS_LIFETIME
    logger.info("Refreshed signing credentials for %s (lifetime=%ds)", service_account_email, SIGNING_CREDENTIALS_LIFETIME)
    return _signing_credentials


def _bucket():
    return _get_client().bucket(GCS_BUCKET)


def upload_to_gcs(data: bytes, filename: str) -> str:
    """Upload bytes to GCS and return the object name.

    Args:
        data: File content bytes.
        filename: GCS object name (e.g. ``uuid.jpg``).

    Returns:
        The object name on success.

    Raises:
        Exception: If the upload fails.
    """
    blob = _bucket().blob(filename)
    blob.upload_from_string(data)
    logger.info("Uploaded %s to GCS bucket %s", filename, GCS_BUCKET)
    return filename


def generate_signed_url(object_name: str) -> str:
    """Generate a v4 signed URL for a GCS object.

    Works on Cloud Run without a service-account JSON key file by
    delegating the signing to the IAM signBlob API.

    Args:
        object_name: The GCS object name.

    Returns:
        A signed URL string.
    """
    blob = _bucket().blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=SIGNED_URL_EXPIRY_HOURS),
        method="GET",
        credentials=_get_signing_credentials(),
    )


def download_from_gcs(object_name: str) -> bytes:
    """Download blob content from GCS.

    Args:
        object_name: The GCS object name.

    Returns:
        The file content as bytes.
    """
    blob = _bucket().blob(object_name)
    return blob.download_as_bytes()


def resolve_image_url(url: str | None) -> str | None:
    """Convert ``/uploads/file.jpg`` to a signed URL when GCS is configured.

    In development (no ``GCS_BUCKET``), returns the original URL unchanged.

    Args:
        url: An image URL like ``/uploads/<filename>``.

    Returns:
        A signed URL, or the original URL if GCS is not configured.
    """
    if not url or not GCS_BUCKET:
        return url
    return generate_signed_url(url.removeprefix("/uploads/"))


def delete_from_gcs(url: str | None) -> None:
    """Delete an object from GCS given its ``/uploads/...`` URL.

    No-op when ``GCS_BUCKET`` is not configured or *url* is empty.

    Args:
        url: An image URL like ``/uploads/<filename>``.
    """
    if not url or not GCS_BUCKET:
        return
    object_name = url.removeprefix("/uploads/")
    try:
        blob = _bucket().blob(object_name)
        blob.delete()
        logger.info("Deleted %s from GCS bucket %s", object_name, GCS_BUCKET)
    except Exception:
        logger.warning("Failed to delete %s from GCS", object_name)


def image_url_to_object(url: str | None) -> str | None:
    """Extract the GCS object name from a ``/uploads/...`` URL.

    Args:
        url: An image URL like ``/uploads/<filename>``.

    Returns:
        The object name, or *None* if *url* is empty.
    """
    if not url:
        return None
    return url.removeprefix("/uploads/")
