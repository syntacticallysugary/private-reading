"""OCI Function API handler for Private Reading service."""

import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

NOSQL_TABLE = os.environ["NOSQL_TABLE_NAME"]
NOSQL_COMPARTMENT = os.environ["NOSQL_COMPARTMENT_ID"]
AUDIOBOOKS_BUCKET = os.environ["AUDIOBOOKS_BUCKET"]
OCI_NAMESPACE = os.environ["OCI_NAMESPACE"]
OCI_REGION = os.environ["OCI_REGION"]
WORKER_API_KEY = os.environ["WORKER_API_KEY"]

_JOB_ID_RE = re.compile(r"^[0-9a-f]{24}$", re.IGNORECASE)

# ── OCI clients — module-level singletons ─────────────────────────────────────

_signer = _nosql_handle = _os_client = None


def _get_signer():
    global _signer
    if not _signer:
        import oci.auth.signers

        _signer = oci.auth.signers.get_resource_principals_signer()
    return _signer


def _make_nosql_handle():
    from borneo import NoSQLHandle, NoSQLHandleConfig
    from borneo.iam import SignatureProvider

    provider = SignatureProvider.create_with_resource_principal()
    config = NoSQLHandleConfig(OCI_REGION, provider)
    config.set_logger(logger)
    return NoSQLHandle(config)


def _get_nosql():
    """Return a borneo NoSQLHandle, recreating it if resource principal auth expired."""
    global _nosql_handle
    if not _nosql_handle:
        _nosql_handle = _make_nosql_handle()
    return _nosql_handle


def _get_os():
    global _os_client
    if not _os_client:
        import oci.object_storage

        _os_client = oci.object_storage.ObjectStorageClient(config={}, signer=_get_signer())
    return _os_client


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(data, status: int = 200):
    return json.dumps(data), status, {"Content-Type": "application/json"}


def _err(msg: str, status: int = 400):
    return _json({"error": msg}, status)


# Cognito RSA public keys — embedded to avoid outbound network calls from the
# private subnet. Update if Cognito rotates keys (symptom: all JWTs return 401).
_COGNITO_JWKS = {
    "tyUmWO6W5q+5QxmjvpY08lPB3FcT4d5zHMgFAs4nqQE=": {
        "kty": "RSA",
        "alg": "RS256",
        "n": "xbDfaYpW7dfVZryxFLwrt-GFdeeENXzdvUEV0lXdkjhp62WU6W6V6ojmC8f3bSfPXKSOp9pTviuLiybR96iaQcum4thIDKpO6rxNJdoqsm11-PA3SkTc9U_m9wbmtZP1cuXFOXMANywsztSqVDNd4LI9nbCqIcpiB8LYp138qZ2NjK7tHTIpQwn8H6au3VYJ2K0uWGRzl0RoQKn58qss17o-c5AxbJqwBH7r-NPqbIjlsaru5JMN34ut4O7x8okTEAsf_nR-3qKjK4MeAm7iKwE8kEiw-sNgEwmHIFiqnhZni5DUdAGNUcZN4TS4ZjcAhzVSWPXnhUzRw8e65Uyt_w",
        "e": "AQAB",
    },
    "rNt+Fjj44hzmBN70ZvwvZGyR6HYh9j6HtYYJvBR2+ao=": {
        "kty": "RSA",
        "alg": "RS256",
        "n": "x2eB3Ir7zRN5eDOjnsM5BmBOcu5Tmt-r10zsiMGJk3Q07o6cLySXyG16jsV3nn2YYYp1vQDG0MojmaK21iGaroE2X96mBwtwK84rTdaIt8PxPVimw2dywiXMlvvxlC3QU10tKZ0QuG8uwHUKCjmWQoIkhfQvx6PgbkztHhlW1z7iWlF9RjS8zDlUVS_Y4MrROai_RuNNRRP9C1I5RcsO-2Lnptk8Oq7dnUFKLBBgzV3Im0gDjgBGGB8l_9rqxik4kbbbXTEnSrFRYKDuzL6OAB4GM8P_J08owyzhbZFFEP1OZltGckndSDABrdYUllSqXhD8tCViOK_G_f1I-pHSZQ",
        "e": "AQAB",
    },
}
_COGNITO_PUBLIC_KEYS: dict = {}


def _get_cognito_key(kid: str):
    if kid not in _COGNITO_PUBLIC_KEYS:
        import jwt

        jwk = _COGNITO_JWKS.get(kid)
        if not jwk:
            return None
        _COGNITO_PUBLIC_KEYS[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    return _COGNITO_PUBLIC_KEYS[kid]


def _user_id(headers: dict) -> str | None:
    """Validate Cognito JWT signature and return the sub claim."""
    import jwt as pyjwt

    auth = headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:]
    try:
        header = pyjwt.get_unverified_header(token)
        pub_key = _get_cognito_key(header.get("kid", ""))
        if not pub_key:
            return None
        claims = pyjwt.decode(
            token,
            pub_key,
            algorithms=["RS256"],
            issuer=os.environ["COGNITO_ISSUER"],
            options={"verify_aud": False},
        )
        return claims.get("sub")
    except Exception:
        logger.exception("JWT validation failed")
        return None


def _worker_ok(headers: dict) -> bool:
    return headers.get("x-worker-token") == WORKER_API_KEY


def _nosql_op(fn):
    """Run a borneo operation, refreshing the handle once on auth failure."""
    global _nosql_handle
    try:
        return fn(_get_nosql())
    except Exception as exc:
        if "NotAuthenticated" in str(exc) or "InvalidAuthorization" in str(exc):
            logger.warning("borneo auth expired — refreshing handle")
            _nosql_handle = _make_nosql_handle()
            return fn(_nosql_handle)
        raise


def _query(stmt: str) -> list[dict]:
    from borneo import QueryRequest

    def run(handle):
        req = QueryRequest()
        req.set_statement(stmt)
        req.set_compartment(NOSQL_COMPARTMENT)
        results = []
        while True:
            resp = handle.query(req)
            results.extend(resp.get_results())
            if req.is_done():
                break
        return results

    return _nosql_op(run)


def _upsert(row: dict) -> None:
    from borneo import PutRequest

    def run(handle):
        req = PutRequest()
        req.set_table_name(NOSQL_TABLE)
        req.set_compartment(NOSQL_COMPARTMENT)
        req.set_value(row)
        handle.put(req)

    _nosql_op(run)


def _ocs_get_bytes(object_name: str) -> bytes | None:
    try:
        resp = _get_os().get_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=AUDIOBOOKS_BUCKET,
            object_name=object_name,
        )
        return resp.data.content
    except Exception as exc:
        if (
            getattr(getattr(exc, "status", None), "__eq__", lambda _: False)(404)
            or "404" in str(exc)
            or "ObjectNotFound" in str(exc)
            or "NoSuchKey" in str(exc)
        ):
            return None
        raise


def _ocs_put_bytes(
    object_name: str, data: bytes, content_type: str = "application/octet-stream"
) -> None:
    import io as _io

    _get_os().put_object(
        namespace_name=OCI_NAMESPACE,
        bucket_name=AUDIOBOOKS_BUCKET,
        object_name=object_name,
        put_object_body=_io.BytesIO(data),
        content_type=content_type,
    )


def _ocs_delete(object_name: str) -> None:
    try:
        _get_os().delete_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=AUDIOBOOKS_BUCKET,
            object_name=object_name,
        )
    except Exception:
        pass


def _voice_meta_key(user_id: str) -> str:
    return f"voices/{user_id}/metadata.json"


def _voice_sample_key(user_id: str) -> str:
    return f"voices/{user_id}/sample"


def _read_voice_meta(user_id: str) -> dict | None:
    raw = _ocs_get_bytes(_voice_meta_key(user_id))
    if raw is None:
        return None
    return json.loads(raw)


def _delete(user_id: str, job_id: str) -> None:
    from borneo import DeleteRequest

    def run(handle):
        req = DeleteRequest()
        req.set_table_name(NOSQL_TABLE)
        req.set_compartment(NOSQL_COMPARTMENT)
        req.set_key({"user_id": user_id, "job_id": job_id})
        handle.delete(req)

    _nosql_op(run)


def _current_job(user_id: str) -> dict | None:
    rows = _query(
        f"SELECT * FROM {NOSQL_TABLE} WHERE user_id = '{user_id}'"
        " ORDER BY created_at DESC LIMIT 1"
    )
    return rows[0] if rows else None


def _job_by_id(job_id: str) -> dict | None:
    rows = _query(f"SELECT * FROM {NOSQL_TABLE} WHERE job_id = '{job_id}'")
    return rows[0] if rows else None


# ── Router ─────────────────────────────────────────────────────────────────────

_WORKER_PATH_RE = re.compile(r"^/worker/jobs/([^/]+)/(claim|complete|fail|progress)$")


def _route(method: str, path: str, headers: dict, body: dict):
    if path.startswith("/v1"):
        path = path[3:]

    # POST /jobs — submit text for conversion
    if path == "/jobs" and method == "POST":
        uid = _user_id(headers)
        if not uid:
            return _err("Unauthorized", 401)
        text = (body.get("text") or "").strip()
        if not text:
            return _err("text is required")
        now = _now()
        job = {
            "user_id": uid,
            "job_id": uuid.uuid4().hex[:24],
            "status": "pending",
            "text": text,
            "text_length": len(text),
            "created_at": now,
            "updated_at": now,
            "error": "",
            "audio_path": "",
            "audio_expires_at": "",
        }
        _upsert(job)
        return _json({"job_id": job["job_id"], "status": "pending"}, 201)

    # GET|DELETE /jobs/current — retrieve or cancel the user's latest job
    if path == "/jobs/current":
        uid = _user_id(headers)
        if not uid:
            return _err("Unauthorized", 401)
        job = _current_job(uid)
        if not job:
            return _err("No current job", 404)
        if method == "GET":
            return _json(job)
        if method == "DELETE":
            _delete(uid, job["job_id"])
            return _json({"deleted": True})

    # GET /jobs/current/url — generate a 24-hour pre-signed download URL
    if path == "/jobs/current/url" and method == "GET":
        uid = _user_id(headers)
        if not uid:
            return _err("Unauthorized", 401)
        job = _current_job(uid)
        if not job:
            return _err("No current job", 404)
        if job.get("status") != "complete":
            return _err(f"Job not complete: {job.get('status')}", 409)
        audio_path = job.get("audio_path", "")
        if not audio_path:
            return _err("No audio file", 404)
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        import oci.object_storage.models

        par = _get_os().create_preauthenticated_request(
            namespace_name=OCI_NAMESPACE,
            bucket_name=AUDIOBOOKS_BUCKET,
            create_preauthenticated_request_details=oci.object_storage.models.CreatePreauthenticatedRequestDetails(
                name=f"par-{job['job_id']}-{int(datetime.now(timezone.utc).timestamp())}",
                object_name=audio_path,
                access_type="ObjectRead",
                time_expires=expires,
            ),
        )
        url = f"https://objectstorage.{OCI_REGION}.oraclecloud.com{par.data.access_uri}"
        return _json({"url": url, "expires_at": expires.isoformat()})

    # GET /worker/jobs/pending — return oldest pending job (full text included)
    if path == "/worker/jobs/pending" and method == "GET":
        if not _worker_ok(headers):
            return _err("Unauthorized", 401)
        rows = _query(
            f"SELECT * FROM {NOSQL_TABLE} WHERE status = 'pending'" " ORDER BY created_at LIMIT 1"
        )
        return _json({"job": rows[0] if rows else None})

    # POST /worker/jobs/{id}/(claim|complete|fail)
    m = _WORKER_PATH_RE.fullmatch(path)
    if m and method == "POST":
        if not _worker_ok(headers):
            return _err("Unauthorized", 401)
        job_id, action = m.group(1), m.group(2)
        if not _JOB_ID_RE.match(job_id):
            return _err("Invalid job_id", 400)
        job = _job_by_id(job_id)
        if not job:
            return _err("Job not found", 404)

        if action == "claim":
            if job.get("status") != "pending":
                return _err(f"Job not pending: {job.get('status')}", 409)
            job.update(status="processing", updated_at=_now())
            _upsert(job)
            return _json(job)

        if action == "complete":
            audio_path = (body.get("audio_path") or "").strip()
            if not audio_path:
                return _err("audio_path is required")
            job.update(status="complete", audio_path=audio_path, updated_at=_now())
            _upsert(job)
            return _json({"ok": True})

        if action == "fail":
            job.update(
                status="failed",
                error=body.get("error", "unknown"),
                updated_at=_now(),
            )
            _upsert(job)
            return _json({"ok": True})

        if action == "progress":
            done = body.get("chunks_done")
            total = body.get("chunks_total")
            if done is None or total is None:
                return _err("chunks_done and chunks_total required")
            job.update(chunks_done=int(done), chunks_total=int(total), updated_at=_now())
            _upsert(job)
            return _json({"ok": True})

    # GET /voice — return user's voice registration status
    if path == "/voice" and method == "GET":
        uid = _user_id(headers)
        if not uid:
            return _err("Unauthorized", 401)
        meta = _read_voice_meta(uid)
        if meta is None:
            return _err("No voice registered", 404)
        return _json({"status": meta.get("status"), "registered_at": meta.get("registered_at", "")})

    # POST /voice — save audio sample and queue registration
    if path == "/voice" and method == "POST":
        uid = _user_id(headers)
        if not uid:
            return _err("Unauthorized", 401)
        audio_b64 = (body.get("audio_b64") or "").strip()
        transcript = (body.get("transcript") or "").strip()
        if not audio_b64:
            return _err("audio_b64 is required")
        if not transcript:
            return _err("transcript is required")
        import base64

        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            return _err("audio_b64 is not valid base64")
        if len(audio_bytes) < 1000:
            return _err("Audio too short")
        _ocs_put_bytes(_voice_sample_key(uid), audio_bytes, "audio/webm")
        meta = {"status": "pending", "transcript": transcript, "registered_at": _now()}
        _ocs_put_bytes(_voice_meta_key(uid), json.dumps(meta).encode(), "application/json")
        return _json({"status": "pending"}, 201)

    # DELETE /voice — remove voice registration
    if path == "/voice" and method == "DELETE":
        uid = _user_id(headers)
        if not uid:
            return _err("Unauthorized", 401)
        _ocs_delete(_voice_meta_key(uid))
        _ocs_delete(_voice_sample_key(uid))
        return _json({"deleted": True})

    return _err("Not found", 404)


# ── FDK entrypoint ─────────────────────────────────────────────────────────────


def handler(ctx, data: io.BytesIO = None):
    """OCI Function entrypoint — called by the FDK HTTP server."""
    import fdk.response

    try:
        headers = {k.lower(): v for k, v in ctx.Headers().items()}
        method = (headers.get("fn-http-method") or "GET").upper()
        path = urlparse(headers.get("fn-http-request-url") or "/").path
        body: dict = {}
        if data:
            raw = data.getvalue()
            if raw:
                try:
                    body = json.loads(raw)
                except Exception:
                    pass

        resp_data, status, resp_headers = _route(method, path, headers, body)

    except Exception as _exc:
        import traceback

        logger.exception("unhandled error in handler")
        resp_data = json.dumps(
            {"error": "internal server error", "detail": traceback.format_exc(limit=5)}
        )
        status = 500
        resp_headers = {"Content-Type": "application/json"}

    return fdk.response.Response(
        ctx,
        response_data=resp_data,
        headers=resp_headers,
        status_code=status,
    )
