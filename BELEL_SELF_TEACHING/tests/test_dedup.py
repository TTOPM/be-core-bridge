from BELEL_SELF_TEACHING.dedup import Deduper

def test_exact_dedup():
    d = Deduper(set())
    text = "hello world"
    assert d.is_exact_dup(text) is False
    d.add_exact(text)
    assert d.is_exact_dup(text) is True

def test_fuzzy_dedup():
    d = Deduper(set(), fuzzy_threshold=0.9)
    a = "This is a sentence used for testing."
    b = "This is a sentence used for tests."
    d.remember(a)
    assert d.is_fuzzy_dup(b) is True
