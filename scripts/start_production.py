"""Production container entrypoint for free single-service hosting.

Runs migrations, optionally seeds the verified demo user, starts the MCP
server on localhost, then starts Uvicorn on the platform-provided port.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def _run_step(args: list[str], *, name: str) -> None:
    print(f"[startup] {name}...", flush=True)
    subprocess.check_call(args)


def _start_process(args: list[str], *, name: str, env: dict[str, str]) -> subprocess.Popen:
    print(f"[startup] starting {name}: {' '.join(args)}", flush=True)
    return subprocess.Popen(args, env=env)


def _terminate(processes: list[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 10
    for proc in processes:
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if proc.poll() is None:
            proc.kill()


def main() -> int:
    env = os.environ.copy()
    env.setdefault("MCP_HOST", "127.0.0.1")
    env.setdefault("MCP_PORT", "8765")
    env.setdefault("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*,[::1]:*")
    env.setdefault("MCP_SERVER_URL", "http://127.0.0.1:8765/mcp")

    _run_step([sys.executable, "-m", "alembic", "upgrade", "head"], name="migrations")
    _run_step([sys.executable, "-m", "scripts.seed_demo_user"], name="demo user seed")

    port = env.get("PORT", "8000")
    processes = [
        _start_process(
            [sys.executable, "-m", "app.mcp_server"],
            name="mcp server",
            env=env,
        ),
        _start_process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                port,
                "--proxy-headers",
                "--forwarded-allow-ips",
                "*",
            ],
            name="fastapi",
            env=env,
        ),
    ]

    def _handle_signal(signum: int, _frame: object) -> None:
        print(f"[startup] received signal {signum}, shutting down", flush=True)
        _terminate(processes)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    while True:
        for proc in processes:
            code = proc.poll()
            if code is not None:
                print(f"[startup] child exited with code {code}", flush=True)
                _terminate(processes)
                return code
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
