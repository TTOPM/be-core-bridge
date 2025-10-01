from grok.grok_integrity_beacon import QuorumVerifier

def test_quorum_empty():
    q = QuorumVerifier([], 0.66)
    res = q.verify()
    assert res["agree"] == 0

# For full tests, stub _fetch_witness to return known JSONs and assert quorum True/False.
