from grok.grok_link_fetcher import LinkFetcher
def test_file_json(tmp_path):
    p = tmp_path / "w.json"
    p.write_text('{"ok":true}')
    r = LinkFetcher().fetch_json(str(p))
    assert r.ok and r.json_data["ok"] is True
