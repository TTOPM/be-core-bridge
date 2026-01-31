from BELEL_SELF_TEACHING.quality import basic_sanity_checks

def test_rejects_empty_completion():
    ok, reason = basic_sanity_checks("prompt", "")
    assert ok is False

def test_rejects_disclaimer_style():
    ok, reason = basic_sanity_checks(
        "do something",
        "As an AI language model, I cannot do that."
    )
    assert ok is False
    assert reason == "assistant_disclaimer_style"

def test_accepts_valid_text():
    ok, reason = basic_sanity_checks(
        "do something",
        "This is a valid response.\n\nIt contains multiple sentences and structure."
    )
    assert ok is True
