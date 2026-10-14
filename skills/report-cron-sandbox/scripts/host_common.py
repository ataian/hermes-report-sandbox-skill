"""Host-only preflight and bounded Docker invocation for fixed report jobs."""
import os
import re
import stat
import subprocess

UID = os.getuid()
GID = os.getgid()


def checked(path, kind, roots):
    if kind not in ("dir", "file") or not path.startswith("/") or any(part in ("", ".", "..") for part in path[1:].split("/")):
        raise ValueError(f"invalid path or kind: {path}")
    if not any(path == root or path.startswith(root + "/") for root in roots):
        raise ValueError(f"path outside fixed roots: {path}")
    current = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        parts = path.strip("/").split("/")
        for index, part in enumerate(parts):
            following = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_DIRECTORY if index < len(parts) - 1 or kind == "dir" else 0), dir_fd=current)
            os.close(current)
            current = following
            info = os.fstat(current)
            if info.st_uid not in (0, UID) or info.st_mode & stat.S_IWOTH:
                raise ValueError(f"unsafe owner/mode: {path}")
        info = os.fstat(current)
        if (kind == "dir" and not stat.S_ISDIR(info.st_mode)) or (kind == "file" and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)):
            raise ValueError(f"wrong file type: {path}")
        if info.st_uid not in (0, UID) or info.st_mode & stat.S_IWOTH:
            raise ValueError(f"unsafe owner/mode: {path}")
        return info
    finally:
        os.close(current)


def checked_lock(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != UID or info.st_mode & 0o077:
        raise ValueError("unsafe lock")


def mount(source, target, readonly=True):
    # Docker parses --mount as CSV even when subprocess uses an argument list.
    # Ownership/type/allowed-root checks remain the trusted starter's responsibility.
    for path in (source, target):
        if (not isinstance(path, str) or not path.startswith("/")
                or any(char in path for char in ',"\r\n\x00')
                or any(part in ("", ".", "..") for part in path[1:].split("/"))):
            raise ValueError("unsafe mount path")
    if not isinstance(readonly, bool):
        raise ValueError("readonly must be boolean")
    return ["--mount", f"type=bind,src={source},dst={target}" + (",readonly" if readonly else "")]


def docker_run(name, image, mounts, command, timeout, network=True):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
        raise ValueError("unsafe container name")
    args = ["docker", "run", "--rm", "--name", name, "--user", f"{UID}:{GID}",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--read-only",
            "--memory", "384m", "--memory-swap", "384m", "--pids-limit", "64",
            "--cpus", "1", "--tmpfs", f"/tmp:rw,noexec,nosuid,size=32m,uid={UID},gid={GID}"]
    if not network:
        args += ["--network", "none"]
    for source, target, readonly in mounts:
        args += mount(source, target, readonly)
    args += [image, *command]
    try:
        result = subprocess.run(args, timeout=timeout, check=False)
        return result.returncode
    except subprocess.TimeoutExpired:
        # docker CLI may die before its container; remove by fixed generated name.
        removed = subprocess.run(["docker", "rm", "-f", name], timeout=30, check=False)
        probe = subprocess.run(["docker", "inspect", "--type", "container", name], timeout=30, check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if removed.returncode != 0 or probe.returncode == 0:
            raise RuntimeError("timed-out container cleanup unconfirmed")
        return 124
