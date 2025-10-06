from cloud.api.policy_pipeline import PolicyGraph, Disclosure, Harm, Bias, Jurisdiction, Provenance, AuditLog, PolicyContext
def test_pipeline_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_DB", str(tmp_path/"audit.sqlite"))
    g = PolicyGraph([Disclosure(), Harm(), Bias(), Jurisdiction(), Provenance(), AuditLog()])
    ctx = PolicyContext(user_text="please search", model_text="you are an idiot", session_disclosed=False, locale="EU")
    out = g.run(ctx)
    assert "person" in out.model_text  # bias mitigated
