from app.models.entities import Meeting, Speaker, Transcript, TranscriptSegment


def test_remote_provider_token_is_never_returned(client):
    resp = client.post(
        "/api/settings/remote-providers",
        json={"name": "TestProvider", "base_url": "https://whisper.example.internal", "api_token": "supersecrettoken1234"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "supersecrettoken1234" not in str(body)
    assert body["api_token_masked"] != "supersecrettoken1234"

    listing = client.get("/api/settings/remote-providers").json()
    assert all("supersecrettoken1234" not in str(p) for p in listing)


def test_duplicate_remote_provider_name_rejected(client):
    payload = {"name": "DupProvider", "base_url": "https://a.internal", "api_token": "x"}
    first = client.post("/api/settings/remote-providers", json=payload)
    assert first.status_code == 200
    second = client.post("/api/settings/remote-providers", json=payload)
    assert second.status_code == 400


def test_settings_general_round_trip(client):
    resp = client.put("/api/settings/general", json={"app_name": "MeetSage Test"})
    assert resp.status_code == 200
    all_settings = client.get("/api/settings").json()
    assert all_settings["general"]["app_name"] == "MeetSage Test"


def _make_meeting_with_transcript(db):
    meeting = Meeting(name="Export/Search Test", original_filename="f.wav", media_type="audio", expected_languages=["en"])
    db.add(meeting)
    db.flush()
    transcript = Transcript(meeting_id=meeting.id, version=1, provider="local", model="tiny", languages_detected=["en"])
    db.add(transcript)
    db.flush()
    db.add(TranscriptSegment(transcript_id=transcript.id, seq=0, start=0.0, end=1.0, text="Hello there team.", language="en"))
    db.commit()
    return meeting


def test_export_transcript_txt(client, db_session):
    meeting = _make_meeting_with_transcript(db_session)
    resp = client.get(f"/api/meetings/{meeting.id}/export/transcript?format=txt")
    assert resp.status_code == 200
    assert "Hello there team." in resp.text


def test_export_transcript_uses_renamed_speaker_not_raw_label(client, db_session):
    meeting = Meeting(name="Rename Export Test", original_filename="f.wav", media_type="audio", expected_languages=["en"])
    db_session.add(meeting)
    db_session.flush()
    transcript = Transcript(meeting_id=meeting.id, version=1, provider="local", model="tiny", languages_detected=["en"])
    db_session.add(transcript)
    db_session.flush()
    db_session.add(
        TranscriptSegment(
            transcript_id=transcript.id, seq=0, start=0.0, end=1.0, text="We should ship Friday.",
            language="en", speaker_label="SPEAKER_00",
        )
    )
    speaker = Speaker(meeting_id=meeting.id, label="SPEAKER_00")
    db_session.add(speaker)
    db_session.commit()

    rename_resp = client.patch(f"/api/meetings/{meeting.id}/speakers/{speaker.id}", json={"display_name": "Ravi"})
    assert rename_resp.status_code == 200

    for fmt in ("txt", "srt", "vtt", "md"):
        resp = client.get(f"/api/meetings/{meeting.id}/export/transcript?format={fmt}")
        assert resp.status_code == 200
        assert "Ravi" in resp.text, f"format={fmt} still shows raw speaker label instead of renamed display name"
        assert "SPEAKER_00" not in resp.text, f"format={fmt} leaked the raw speaker label after rename"


def test_export_transcript_rejects_unsupported_format(client, db_session):
    meeting = _make_meeting_with_transcript(db_session)
    resp = client.get(f"/api/meetings/{meeting.id}/export/transcript?format=exe")
    assert resp.status_code == 400


def test_export_analysis_404_when_no_analysis(client, db_session):
    meeting = _make_meeting_with_transcript(db_session)
    resp = client.get(f"/api/meetings/{meeting.id}/export/analysis?format=json")
    assert resp.status_code == 404


def test_search_finds_meeting_by_name(client, db_session):
    _make_meeting_with_transcript(db_session)
    resp = client.get("/api/search", params={"q": "Export/Search Test"})
    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()["meetings"]]
    assert "Export/Search Test" in names


def test_search_finds_transcript_text(client, db_session):
    _make_meeting_with_transcript(db_session)
    resp = client.get("/api/search", params={"q": "Hello there team"})
    assert resp.status_code == 200
    texts = [s["text"] for s in resp.json()["transcript_segments"]]
    assert any("Hello there team" in t for t in texts)
