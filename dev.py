#!/usr/bin/env python3
"""Cross-platform dev launcher: spins up backend (FastAPI) and frontend (SvelteKit)."""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

IS_WINDOWS = sys.platform == "win32"


def venv_python() -> str:
    if IS_WINDOWS:
        candidate = BACKEND / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = BACKEND / ".venv" / "bin" / "python"
    if not candidate.exists():
        print(f"Virtual env not found at {candidate}")
        print("Run: cd backend && python -m venv .venv")
        sys.exit(1)
    return str(candidate)


def start(name: str, cwd: Path, cmd: list[str]):
    print(f"Starting {name}...")
    kwargs = dict(cwd=str(cwd))
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(cmd, **kwargs)
    return proc


def main():
    os.chdir(ROOT)

    python = venv_python()
    backend = start("backend", BACKEND, [
        python, "-m", "uvicorn", "app.main:app",
        "--reload", "--port", "8000",
        "--reload-exclude", "build/**",
    ])
    frontend = start("frontend", FRONTEND, [
        "npm.cmd" if IS_WINDOWS else "npm", "run", "dev",
    ])

    print()
    print("=" * 48)
    print("Backend:  http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("Docs:     http://localhost:8000/docs")
    print("=" * 48)
    print()
    print("Press Ctrl+C to stop all services.")

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print("Backend exited unexpectedly.")
                break
            if frontend.poll() is not None:
                print("Frontend exited unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nShutting down...")

    for proc, name in [(backend, "backend"), (frontend, "frontend")]:
        if proc.poll() is not None:
            continue
        if IS_WINDOWS:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)

    # Windows: kill the whole group so uvicorn reload children die too
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(backend.pid)],
                       capture_output=True)
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend.pid)],
                       capture_output=True)


if __name__ == "__main__":
    main()
