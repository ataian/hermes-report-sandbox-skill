"""Offline synthetic smoke test inside the real selector dependency image.

Mount scripts/select.py readonly at /app/select.py and this file at
/app/container_smoke.py. Writable /state, /config-output and /warning-run
must be NEW private fixture directories. No real keys or network needed.
"""
import importlib.util
import json
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location("report_selector", "/app/select.py")
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)

assert os.getuid() != 0
assert not Path("/var/run/docker.sock").exists()
assert not Path("/run/secrets/nous_api_key").exists()
try:
    Path("/rootfs-write-probe").write_text("must not work")
except OSError:
    pass
else:
    raise AssertionError("root filesystem accepted a write")

free = {"id": "fixture/free:free", "name": "Fixture Free", "context_length": 131072,
        "pricing": {"prompt": "0", "completion": "0"}, "reasoning": {"mandatory": False}}
paid = {"id": selection.FALLBACK, "pricing": {"prompt": "1", "completion": "1"}}
selection.catalog = lambda: {free["id"]: free, paid["id"]: paid}
selection.secret = lambda _: "synthetic-not-a-real-key"

def fixture_http(url, payload=None, key=None, **kwargs):
    assert url == selection.BASE + "/chat/completions"
    assert payload["model"] == free["id"]
    return {"model": free["id"], "choices": [{"message": {"content": "FREE_REPORT_OK"}}],
            "usage": {"cost": 0}}

selection.http_json = fixture_http
selection.portal_candidates = lambda _: (_ for _ in ()).throw(AssertionError("unexpected rank search"))
db = selection.database()
db.execute("INSERT INTO meta VALUES('route',?)", (json.dumps({
    "provider": "custom:nous-api-key", "model": free["id"], "free_confirmed": True}),))
db.commit()
db.close()
assert selection.main("2026-01-01") == 0
config = json.loads(Path("/config-output/llm-config.json").read_text())
assert config == {"provider": "custom:nous-api-key", "model": free["id"]}
assert list(Path("/warning-run").iterdir()) == []
print("PASS: synthetic selector output, nonroot, rootfs write denied, no keys/socket")
