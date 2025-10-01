from privacy.redactor import redact
def test_redactor_basic():
    s = "Contact me at alice@example.com or +1 (415) 555-1234"
    out = redact(s)
    assert "<email:" in out and "<phone:" in out
