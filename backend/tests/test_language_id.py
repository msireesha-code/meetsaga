from app.services.transcription.language_id import detect_segment_language


def test_detects_english():
    assert detect_segment_language("We need to complete this by Friday.", ["en", "hi", "te"]) == "en"


def test_detects_hindi():
    assert detect_segment_language("इसके बाद हम deployment करेंगे.", ["en", "hi", "te"]) == "hi"


def test_detects_telugu():
    assert detect_segment_language("ఈ పని పూర్తయ్యాక testing start చేద్దాం.", ["en", "hi", "te"]) == "te"


def test_falls_back_to_first_expected_language_when_no_script_detected():
    # digits/punctuation only: no Latin/Devanagari/Telugu letters at all
    assert detect_segment_language("12345 !!!", ["hi", "te"]) == "hi"


def test_falls_back_to_english_when_expected_and_no_script_detected():
    assert detect_segment_language("12345", ["en", "hi"]) == "en"
