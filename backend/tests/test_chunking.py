from app.services.analysis.chunking import chunk_segments


def test_single_chunk_for_short_transcript():
    segments = [{"text": "hello"} for _ in range(3)]
    chunks = chunk_segments(segments, max_chars=1000)
    assert len(chunks) == 1
    assert len(chunks[0]) == 3


def test_splits_into_multiple_chunks_when_exceeding_budget():
    segments = [{"text": "x" * 100} for _ in range(10)]
    chunks = chunk_segments(segments, max_chars=250)
    assert len(chunks) > 1


def test_every_segment_preserved_across_chunks():
    segments = [{"text": "x" * 100, "id": i} for i in range(10)]
    chunks = chunk_segments(segments, max_chars=250)
    flattened_ids = [s["id"] for chunk in chunks for s in chunk]
    assert flattened_ids == list(range(10))  # nothing lost, nothing duplicated, order preserved


def test_empty_segments_returns_one_empty_chunk():
    assert chunk_segments([]) == [[]]
