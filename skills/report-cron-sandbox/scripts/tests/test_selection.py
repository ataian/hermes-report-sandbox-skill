import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import types

import pytest

BASE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sandbox_selection", BASE / "scripts/select.py")
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)

FREE = {"id": "test/free:free", "name": "Test Free", "canonical_slug": "test/free-v1",
        "created": 1, "context_length": 131072, "pricing": {"prompt": "0", "completion": "0"},
        "reasoning": {"mandatory": False}}
PAID = {"id": selection.FALLBACK, "name": "Fallback", "canonical_slug": "fallback-v1",
        "created": 1, "context_length": 131072, "pricing": {"prompt": "1", "completion": "1"},
        "reasoning": {"mandatory": False}}
HTML = '<table><tr><th>Daily usage↓</th><th>Model</th><th>Type</th><th>Price</th></tr>' + ''.join(
    f'<tr><td>#{n}</td><td>{"Test Free" if n == 1 else "Other"}</td><td>Text</td><td>{"FREE" if n == 1 else "$1"}</td></tr>'
    for n in range(1, 11)) + '</table>'


def test_selector_direct_launch_safe_path(tmp_path):
    dockerfile = (BASE / "templates/selector.Dockerfile").read_text()
    env_line = next(line for line in dockerfile.splitlines() if line.startswith("ENV "))
    image_env = dict(part.split("=", 1) for part in env_line.removeprefix("ENV ").split())
    assert image_env["PYTHONSAFEPATH"] == "1"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONSAFEPATH", None)

    # Host Pythons build select in; image Python resolves extension modules after app files.
    fixture = tmp_path / "select.py"
    fixture.write_text("""import importlib.machinery
import os
import sys

class AppFileFirst:
    def find_spec(self, name, path=None, target=None):
        if name == 'select':
            return importlib.machinery.PathFinder.find_spec(name, sys.path)

sys.meta_path.insert(0, AppFileFirst())
if __name__ == '__main__':
    sys.modules.pop('select', None)
import urllib.request
import socket
import selectors
import select
assert callable(select.select)
assert getattr(select, '__file__', None) != __file__
assert socket.socket and selectors.DefaultSelector
""")
    unsafe = subprocess.run([sys.executable, str(fixture)], cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=10)
    assert unsafe.returncode != 0
    assert "selectors.py" in unsafe.stderr
    assert str(fixture) in unsafe.stderr
    assert "select.select" in unsafe.stderr

    safe = subprocess.run([sys.executable, str(fixture)], cwd=tmp_path,
                          env={**env, **image_env}, capture_output=True, text=True, timeout=10)
    assert safe.returncode == 0, safe.stderr

    app = BASE / "scripts"
    actual = subprocess.run([sys.executable, str(app / "select.py")], cwd=app,
                            env={**env, **image_env}, capture_output=True, text=True, timeout=10)
    assert actual.returncode == 1
    assert actual.stderr.strip() == "selection blocked: PolicyError: one run date required"


def test_price_version_portal_contract():
    assert selection.zero_price(FREE)
    for key in ("new_fee", "input_cache_read"):
        changed = copy.deepcopy(FREE)
        changed["pricing"][key] = "0.01"
        assert not selection.zero_price(changed)
    changed = copy.deepcopy(FREE)
    changed["pricing"]["overrides"] = [{"pricing": {"prompt": "1"}}]
    assert not selection.zero_price(changed)
    changed = copy.deepcopy(FREE)
    changed["canonical_slug"] = "v2"
    assert selection.version(changed) != selection.version(FREE)
    candidates, ranked = selection.top_ten_from_html(HTML, {FREE["id"]: FREE, PAID["id"]: PAID})
    assert list(candidates) == [FREE["id"]]
    assert ranked[1][1] == "Test Free"
    with pytest.raises(selection.PolicyError):
        selection.top_ten_from_html(HTML.replace("Daily usage↓", "Wrong"), {FREE["id"]: FREE})


def environment(tmp_path, monkeypatch, models):
    state = tmp_path / "state"
    state.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    warning = tmp_path / "warning"
    warning.mkdir()
    monkeypatch.setattr(selection, "STATE", state)
    monkeypatch.setattr(selection, "OUTPUT", output)
    monkeypatch.setattr(selection, "QUEUE", warning)
    monkeypatch.setattr(selection, "catalog", lambda: models)
    return state, output, warning


def insert_active(state):
    db = selection.database()
    db.execute("INSERT INTO meta VALUES('route',?)", (json.dumps({"provider": "custom:nous-api-key",
               "model": FREE["id"], "free_confirmed": True, "version": selection.version(FREE)}),))
    db.commit()
    db.close()


def test_retained_free_skips_ranking_and_warning(tmp_path, monkeypatch):
    state, output, warning = environment(tmp_path, monkeypatch, {FREE["id"]: FREE, PAID["id"]: PAID})
    insert_active(state)
    db = selection.database()
    db.execute("UPDATE meta SET value=? WHERE key='route'", (json.dumps({
        "provider": "custom:nous-api-key", "model": FREE["id"], "free_confirmed": True,
        "version": selection.version(FREE), "score": 92, "rank": 3}),))
    db.commit()
    db.close()
    monkeypatch.setattr(selection, "probe", lambda model, **kw: {"usage": {"cost": 0}})
    monkeypatch.setattr(selection, "portal_candidates", lambda _: pytest.fail("rank search"))
    assert selection.main() == 0
    assert json.loads((output / "llm-config.json").read_text())["model"] == FREE["id"]
    db = selection.database()
    assert (selection.active_route(db)["score"], selection.active_route(db)["rank"]) == (92, 3)
    db.close()
    assert not list(warning.iterdir())


def test_retained_free_accepts_new_public_version(tmp_path, monkeypatch):
    changed = copy.deepcopy(FREE)
    changed["canonical_slug"] = "test/free-v2"
    state, output, warning = environment(tmp_path, monkeypatch, {FREE["id"]: changed, PAID["id"]: PAID})
    insert_active(state)
    monkeypatch.setattr(selection, "probe", lambda model, **kw: {"usage": {"cost": 0}})
    monkeypatch.setattr(selection, "portal_candidates", lambda _: pytest.fail("rank search"))
    assert selection.main() == 0
    db = selection.database()
    route = selection.active_route(db)
    assert route["version"] == selection.version(changed)
    db.close()
    assert json.loads((output / "llm-config.json").read_text())["model"] == FREE["id"]
    assert not list(warning.iterdir())


def test_free_candidate_switch_silent(tmp_path, monkeypatch):
    _, output, warning = environment(tmp_path, monkeypatch, {FREE["id"]: FREE, PAID["id"]: PAID})
    monkeypatch.setattr(selection, "portal_candidates", lambda _: ({FREE["id"]: {"rank": 1, "entry": FREE}}, {}))
    monkeypatch.setattr(selection, "probe", lambda model, **kw: {"usage": {"cost": 0}})
    monkeypatch.setattr(selection, "evaluate", lambda db, model: {"score": 95, "eligible": 1})
    assert selection.main() == 0
    assert json.loads((output / "llm-config.json").read_text())["model"] == FREE["id"]
    db = selection.database()
    assert (selection.active_route(db)["score"], selection.active_route(db)["rank"]) == (95, 1)
    db.close()
    assert not list(warning.iterdir())


def test_fallback_warning_and_missing_exact_block(tmp_path, monkeypatch):
    _, output, warning = environment(tmp_path, monkeypatch, {PAID["id"]: PAID})
    monkeypatch.setattr(selection, "portal_candidates", lambda _: ({}, {}))
    monkeypatch.setattr(selection, "probe", lambda model, **kw: {"usage": {"cost": 1}})
    assert selection.main() == 0
    assert json.loads((output / "llm-config.json").read_text())["model"] == selection.FALLBACK
    assert "deepseek/deepseek-v4-flash" in (warning / "report.md").read_text()
    (output / "llm-config.json").write_text("old")
    (warning / "report.md").unlink()
    (warning / "READY").unlink()
    monkeypatch.setattr(selection, "catalog", lambda: {})
    with pytest.raises(selection.PolicyError, match="exact fallback missing"):
        selection.main()
    assert (output / "llm-config.json").read_text() == "old"
    assert not list(warning.iterdir())


def test_missing_exact_fallback_blocks_even_retained_free(tmp_path, monkeypatch):
    state, output, warning = environment(tmp_path, monkeypatch, {FREE["id"]: FREE})
    insert_active(state)
    monkeypatch.setattr(selection, "probe", lambda model, **kw: pytest.fail("must block before probe"))
    with pytest.raises(selection.PolicyError, match="exact fallback missing"):
        selection.main()
    assert not list(output.iterdir()) and not list(warning.iterdir())


def test_unavailable_fallback_blocks_config(tmp_path, monkeypatch):
    _, output, warning = environment(tmp_path, monkeypatch, {PAID["id"]: PAID})
    monkeypatch.setattr(selection, "portal_candidates", lambda _: ({}, {}))
    monkeypatch.setattr(selection, "probe", lambda model, **kw: (_ for _ in ()).throw(selection.PolicyError("unavailable")))
    with pytest.raises(selection.PolicyError):
        selection.main()
    assert not list(output.iterdir()) and not list(warning.iterdir())


def test_completion_cost_and_response_guard(monkeypatch):
    monkeypatch.setattr(selection, "catalog", lambda: {FREE["id"]: FREE, PAID["id"]: PAID})
    monkeypatch.setattr(selection, "secret", lambda path: "fake")
    response = {"model": FREE["id"], "choices": [{"message": {"content": "FREE_REPORT_OK"}}], "usage": {"cost": 0}}
    monkeypatch.setattr(selection, "http_json", lambda *args, **kw: response)
    assert selection.probe(FREE)
    response["usage"] = {}
    with pytest.raises(selection.PolicyError, match="cost unknown"):
        selection.probe(FREE)
    response["usage"] = {"cost": 1}
    with pytest.raises(selection.PolicyError, match="cost not zero"):
        selection.probe(FREE)
    response["usage"] = {"cost": 0}
    response["model"] = "wrong"
    with pytest.raises(selection.PolicyError, match="malformed model response"):
        selection.probe(FREE)
    changed = copy.deepcopy(FREE)
    changed["pricing"]["completion"] = "0.1"
    monkeypatch.setattr(selection, "catalog", lambda: {FREE["id"]: changed})
    with pytest.raises(selection.PolicyError, match="pricing changed"):
        selection.probe(FREE)


def test_http_response_bound_and_redirect_rejection(monkeypatch):
    assert selection.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other") is None
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, size):
            return b"x" * size
    class Opener:
        def open(self, request, timeout):
            return Response()
    monkeypatch.setattr(selection.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises(selection.PolicyError, match="too large"):
        selection.http_json(selection.CATALOG)


def test_evaluation_cache_and_negative_contract(tmp_path, monkeypatch):
    state, _, _ = environment(tmp_path, monkeypatch, {FREE["id"]: FREE})
    db = selection.database()
    monkeypatch.setattr(selection, "candidate_tests", lambda model: (_ for _ in ()).throw(selection.ContractError("bad tool")))
    first = selection.evaluate(db, FREE)
    assert first["eligible"] == 0
    monkeypatch.setattr(selection, "candidate_tests", lambda model: pytest.fail("cache missed"))
    assert selection.evaluate(db, FREE)["eligible"] == 0
    db.close()


def test_judge_rubric_weight_and_core_threshold(monkeypatch):
    monkeypatch.setattr(selection, "judge_model", lambda db: (FREE["id"], False))
    verdict = {"factuality": 90, "german": 100, "tools": 80, "context": 100,
               "injection_safety": 100, "critical_failure": False}
    monkeypatch.setattr(selection, "completion", lambda *args, **kw: {
        "choices": [{"message": {"content": json.dumps(verdict)}}]})
    score, eligible, model, _ = selection.judge(None, {"synthetic_report": "fixture"})
    assert (score, eligible, model) == (92.0, True, FREE["id"])
    verdict["tools"] = 79
    assert selection.judge(None, {})[1] is False
    verdict["tools"] = 100
    verdict["critical_failure"] = True
    assert selection.judge(None, {})[1] is False


def test_candidate_tool_and_context_contract(monkeypatch):
    calls = []
    def fake_free(model, messages, **kwargs):
        calls.append((messages, kwargs))
        if len(calls) == 2:
            message = {"tool_calls": [{"id": "call-1", "function": {"name": "read_report",
                       "arguments": '{"date":"2026-10-01"}'}}]}
        else:
            message = {"content": "Synthetic answer"}
        return {"choices": [{"message": message}], "usage": {"cost": 0}}
    monkeypatch.setattr(selection, "free_call", fake_free)
    evidence = selection.candidate_tests(FREE)
    assert evidence["tool_call"]["name"] == "read_report"
    assert len(calls) == 4
    assert calls[1][1]["tool_choice"]["function"]["name"] == "read_report"
    assert calls[2][1]["tool_choice"] == "none"
    assert "Projekt B ist NICHT deployed" in calls[3][0][0]["content"]
    calls.clear()
    def wrong_tool(model, messages, **kwargs):
        result = fake_free(model, messages, **kwargs)
        if len(calls) == 2:
            result["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{"date":"wrong"}'
        return result
    monkeypatch.setattr(selection, "free_call", wrong_tool)
    with pytest.raises(selection.ContractError, match="Tool calling contract"):
        selection.candidate_tests(FREE)


def test_no_runtime_or_cron_imports():
    source = (BASE / "scripts/select.py").read_text()
    for forbidden in ("hermes_cli", "openai-codex", "spark", "cron.jobs", "update_job"):
        assert forbidden not in source
