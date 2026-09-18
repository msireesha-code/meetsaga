import io
import subprocess

from app.api import meetings as meetings_api


def _no_op_submit(job_id):
    pass


def test_rejects_unsupported_extension(client, monkeypatch):
    monkeypatch.setattr(meetings_api, "submit_job", _no_op_submit)
    resp = client.post(
        "/api/meetings",
        files={"file": ("evil.sh", io.BytesIO(b"malicious"), "text/plain")},
        data={"expected_languages": '["en"]'},
    )
    assert resp.status_code == 400


def test_path_traversal_filename_is_sanitized_not_500(client, monkeypatch, tmp_path):
    monkeypatch.setattr(meetings_api, "submit_job", _no_op_submit)
    wav_path = tmp_path / "sample.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(wav_path)],
        capture_output=True,
        check=True,
    )
    with open(wav_path, "rb") as f:
        resp = client.post(
            "/api/meetings",
            files={"file": ("../../etc/passwd.wav", f, "audio/wav")},
            data={"expected_languages": '["en"]'},
        )
    assert resp.status_code == 200
    meeting_id = resp.json()["meeting_id"]
    meeting = client.get(f"/api/meetings/{meeting_id}").json()
    assert ".." not in meeting["original_filename"]
    assert "/" not in meeting["original_filename"]


def test_rejects_oversized_upload(client, monkeypatch):
    monkeypatch.setattr(meetings_api, "submit_job", _no_op_submit)
    monkeypatch.setattr(meetings_api.settings, "max_upload_size_mb", 1)
    big_content = b"0" * (2 * 1024 * 1024)  # 2MB, exceeds the 1MB limit set above
    resp = client.post(
        "/api/meetings",
        files={"file": ("big.wav", io.BytesIO(big_content), "audio/wav")},
        data={"expected_languages": '["en"]'},
    )
    assert resp.status_code == 413


def test_accepts_valid_audio_upload_and_creates_queued_job(client, monkeypatch, tmp_path):
    monkeypatch.setattr(meetings_api, "submit_job", _no_op_submit)
    wav_path = tmp_path / "sample.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(wav_path)],
        capture_output=True,
        check=True,
    )
    with open(wav_path, "rb") as f:
        resp = client.post(
            "/api/meetings",
            files={"file": ("sample.wav", f, "audio/wav")},
            data={"expected_languages": '["en"]', "name": "API Test Meeting"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "meeting_id" in body and "job_id" in body

    job = client.get(f"/api/jobs/{body['job_id']}").json()
    assert job["status"] == "QUEUED"


def test_get_nonexistent_meeting_returns_404(client):
    resp = client.get("/api/meetings/does-not-exist")
    assert resp.status_code == 404


def test_rejects_empty_expected_languages(client, monkeypatch, tmp_path):
    monkeypatch.setattr(meetings_api, "submit_job", _no_op_submit)
    wav_path = tmp_path / "sample.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(wav_path)],
        capture_output=True,
        check=True,
    )
    with open(wav_path, "rb") as f:
        resp = client.post(
            "/api/meetings",
            files={"file": ("sample.wav", f, "audio/wav")},
            data={"expected_languages": "[]"},
        )
    assert resp.status_code == 400
