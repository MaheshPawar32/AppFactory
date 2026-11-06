"""Controlled command execution: allowlisted executables, argument arrays, timeouts."""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .redact import redact

ALLOWED_EXECUTABLES = {
    "flutter", "dart", "adb", "aapt", "aapt2", "apksigner", "bundletool", "java",
    "osv-scanner", "trivy", "sqlite3", "git", "gradlew", "emulator", "avdmanager",
    "sdkmanager",
}


class CommandRejected(PermissionError):
    pass


@dataclass
class CommandResult:
    command: list
    cwd: str
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False
    cancelled: bool = False
    not_found: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not (self.timed_out or self.cancelled or self.not_found)

    @property
    def status(self) -> str:
        if self.not_found:
            return "NOT RUN"
        return "PASS" if self.ok else "FAIL"

    def to_dict(self, tail_lines=40) -> dict:
        return {"command": self.command, "cwd": self.cwd, "returncode": self.returncode,
                "status": self.status, "duration_seconds": self.duration_seconds,
                "timed_out": self.timed_out, "cancelled": self.cancelled, "not_found": self.not_found,
                "stdout_tail": self.stdout.splitlines()[-tail_lines:],
                "stderr_tail": self.stderr.splitlines()[-tail_lines:]}


def _executable_name(command) -> str:
    return Path(str(command[0])).name


def which(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name in {"adb", "emulator", "aapt", "aapt2", "apksigner"}:
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") \
            or str(Path.home() / "Library" / "Android" / "sdk")
        sdk_path = Path(sdk)
        candidates = [sdk_path / "platform-tools" / name, sdk_path / "emulator" / name]
        build_tools = sorted((sdk_path / "build-tools").glob("*"), reverse=True)
        candidates += [bt / name for bt in build_tools]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def run_binary(command, cwd, timeout=300, stdin_bytes: bytes | None = None, allowed=ALLOWED_EXECUTABLES):
    """Allowlisted command with raw-bytes stdin/stdout (device archives). Returns (code, stdout, stderr)."""
    if isinstance(command, str) or not command:
        raise CommandRejected("Commands must be a non-empty argument list")
    command = [str(part) for part in command]
    name = _executable_name(command)
    if name not in allowed:
        raise CommandRejected(f"Executable not allowlisted: {name}")
    if not Path(cwd).is_dir():
        raise CommandRejected(f"Working directory does not exist: {cwd}")
    resolved = which(name)
    if not resolved:
        return None, b"", f"{name} not found"
    try:
        proc = subprocess.run([resolved, *command[1:]], cwd=str(cwd), input=stdin_bytes,
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, b"", "timed out"
    return proc.returncode, proc.stdout, redact(proc.stderr.decode("utf-8", "replace"))


def run(command, cwd, timeout=600, env_extra=None, secret_values=(), cancel_event: threading.Event | None = None,
        log_path: Path | None = None, allowed=ALLOWED_EXECUTABLES) -> CommandResult:
    """Run an allowlisted command. Strings are rejected to rule out shell parsing."""
    if isinstance(command, str) or not command:
        raise CommandRejected("Commands must be a non-empty argument list")
    command = [str(part) for part in command]
    name = _executable_name(command)
    if name not in allowed:
        raise CommandRejected(f"Executable not allowlisted: {name}")
    if not Path(cwd).is_dir():
        raise CommandRejected(f"Working directory does not exist: {cwd}")
    resolved = command[0] if os.path.isabs(command[0]) or "/" in command[0] else which(name)
    if not resolved or not Path(resolved).exists():
        return CommandResult(command, str(cwd), None, "", f"{name} not found", not_found=True)
    env = dict(os.environ)
    env.update(env_extra or {})
    started = time.time()
    result = CommandResult(command, str(cwd), None)
    try:
        process = subprocess.Popen([resolved, *command[1:]], cwd=str(cwd), env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        return CommandResult(command, str(cwd), None, "", str(exc), not_found=True)
    try:
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if cancel_event is not None and cancel_event.is_set():
                    process.kill()
                    stdout, stderr = process.communicate()
                    result.cancelled = True
                    break
                if time.time() - started > timeout:
                    process.kill()
                    stdout, stderr = process.communicate()
                    result.timed_out = True
                    break
    finally:
        if process.poll() is None:
            process.kill()
    secrets = list(secret_values) + list((env_extra or {}).values())
    result.returncode = process.returncode
    result.stdout = redact(stdout or "", secrets)
    result.stderr = redact(stderr or "", secrets)
    result.duration_seconds = round(time.time() - started, 2)
    if log_path:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(command)}\n\n[stdout]\n{result.stdout}\n[stderr]\n{result.stderr}\n",
                            encoding="utf-8")
    return result
