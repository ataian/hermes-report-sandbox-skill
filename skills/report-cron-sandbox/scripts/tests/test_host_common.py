import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

BASE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("host_common", BASE / "scripts/host_common.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)




@pytest.mark.parametrize("source,target", [
    ("relative", "/app"), ("/safe,readonly", "/app"),
    ("/safe", "/app,readonly"), ("/safe/../other", "/app"),
    ("/safe\npath", "/app"), ('/safe"path', "/app"),
])
def test_unsafe_mount_rejected(source, target):
    with pytest.raises(ValueError, match="unsafe mount path"):
        helper.mount(source, target)


def test_mount_allows_spaces_and_equals():
    assert helper.mount("/safe/my file=x", "/app/file") == [
        "--mount", "type=bind,src=/safe/my file=x,dst=/app/file,readonly"]


@pytest.mark.parametrize("name", ["--all", "bad/name", "bad,name", "", "a" * 129])
def test_unsafe_container_name_rejected(name, monkeypatch):
    monkeypatch.setattr(helper.subprocess, "run", lambda *a, **k: pytest.fail("transport reached"))
    with pytest.raises(ValueError, match="unsafe container name"):
        helper.docker_run(name, "fixture:1", [], ["true"], 1)


def test_current_uid_gid():
    assert helper.UID == os.getuid()
    assert helper.GID == os.getgid()


def test_mount_and_command_isolation(monkeypatch):
    recorded = []
    def run(args, **kwargs):
        recorded.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(helper.subprocess, "run", run)
    assert helper.docker_run("fixture-job-123", "fixture:1", [
        ("/safe/code", "/app", True), ("/safe/run", "/output", False)],
        ["python", "/app/maker.py"], 42, network=False) == 0
    args, kwargs = recorded[0]
    assert args[:3] == ["docker", "run", "--rm"]
    assert "type=bind,src=/safe/code,dst=/app,readonly" in args
    assert "type=bind,src=/safe/run,dst=/output" in args
    for option, value in (("--network", "none"), ("--cap-drop", "ALL"),
        ("--security-opt", "no-new-privileges"), ("--pids-limit", "64"),
        ("--memory", "384m"), ("--memory-swap", "384m"), ("--cpus", "1")):
        assert args[args.index(option)+1] == value
    assert "--read-only" in args
    assert kwargs["timeout"] == 42
    assert "shell" not in kwargs
    assert args[-3:] == ["fixture:1", "python", "/app/maker.py"]


def test_timeout_only_cleans_named_container(monkeypatch):
    recorded = []
    def run(args, **kwargs):
        recorded.append(args)
        if len(recorded) == 1:
            raise subprocess.TimeoutExpired(args, 1)
        return subprocess.CompletedProcess(args, 0 if len(recorded) == 2 else 1)
    monkeypatch.setattr(helper.subprocess, "run", run)
    assert helper.docker_run("fixture-exact", "fixture:1", [], ["true"], 1) == 124
    assert recorded[1] == ["docker", "rm", "-f", "fixture-exact"]
    assert recorded[2] == ["docker", "inspect", "--type", "container", "fixture-exact"]


def test_timeout_unconfirmed_cleanup_raises(monkeypatch):
    count = 0
    def run(args, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            raise subprocess.TimeoutExpired(args, 1)
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(helper.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="unconfirmed"):
        helper.docker_run("fixture-exact", "fixture:1", [], ["true"], 1)


@pytest.mark.parametrize("path", ["relative/file", "/safe/../file", "/safe//file", "/safe/./file"])
def test_bad_path_rejected(path):
    with pytest.raises(ValueError):
        helper.checked(path, "file", ("/safe",))


def test_outside_root_rejected():
    with pytest.raises(ValueError, match="outside fixed roots"):
        helper.checked("/safe-neighbor/file", "file", ("/safe",))


def test_regular_and_unsafe_files(tmp_path):
    # A normal pytest temp parent may be world-writable. The helper intentionally
    # rejects that ancestor; test with a pre-open path rooted in a private tree.
    # Our documented test invocation sets --basetemp inside the project.
    roots = (str(tmp_path),)
    f = tmp_path / "report.md"
    f.write_text("fixture")
    assert helper.checked(str(f), "file", roots).st_size == 7
    link = tmp_path / "symlink"
    link.symlink_to(f)
    with pytest.raises(OSError):
        helper.checked(str(link), "file", roots)
    hard = tmp_path / "hardlink"
    os.link(f, hard)
    with pytest.raises(ValueError, match="wrong file type"):
        helper.checked(str(hard), "file", roots)


def test_lock_mode(tmp_path):
    path = tmp_path / "lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        helper.checked_lock(fd)
        os.fchmod(fd, 0o666)
        with pytest.raises(ValueError, match="unsafe lock"):
            helper.checked_lock(fd)
    finally:
        os.close(fd)
