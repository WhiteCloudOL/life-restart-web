"""本地开发启动入口。

生产环境请直接使用 Uvicorn/Gunicorn 启动 `app.main:app`，
不要依赖这个脚本管理前端进程。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from shlex import split
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


def _start_frontend_dev_server() -> subprocess.Popen[str] | None:
    settings = get_settings()
    if not settings.is_development or not settings.START_FRONTEND_WITH_BACKEND:
        return None

    frontend_dir = settings.FRONTEND_DIR
    if not frontend_dir.exists():
        print(f"[launcher] 前端目录不存在，跳过启动：{frontend_dir}")
        return None

    command = settings.FRONTEND_DEV_COMMAND.strip()
    if not command:
        print("[launcher] FRONTEND_DEV_COMMAND 为空，跳过前端启动")
        return None

    env = os.environ.copy()
    try:
        args = split(command, posix=os.name != "nt")
    except ValueError:
        # 若用户填入了复杂 shell 命令，保底交给 shell 处理，但仅限本地开发脚本。
        args = []

    if args:
        process = subprocess.Popen(args, cwd=frontend_dir, env=env, text=True)
    else:
        process = subprocess.Popen(command, cwd=frontend_dir, env=env, text=True, shell=True)

    print(f"[launcher] 已启动前端开发服务: {command} (cwd={frontend_dir})")
    return process


def _wait_backend_ready(stop_event: threading.Event, backend_url: str) -> None:
    while not stop_event.is_set():
        try:
            request = Request(backend_url, method="GET")
            with urlopen(request, timeout=1.2):
                return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.4)


def _stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return

    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    backend_url = f"http://127.0.0.1:{settings.APP_PORT}/healthz"
    stop_event = threading.Event()
    frontend_process_holder: dict[str, subprocess.Popen[str] | None] = {"process": None}

    def boot_frontend_after_backend_ready() -> None:
        _wait_backend_ready(stop_event, backend_url)
        if stop_event.is_set():
            return
        frontend_process_holder["process"] = _start_frontend_dev_server()

    frontend_thread = threading.Thread(target=boot_frontend_after_backend_ready, daemon=True)
    frontend_thread.start()

    try:
        uvicorn.run(
            "app.main:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=settings.is_development,
        )
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        frontend_thread.join(timeout=1.0)
        _stop_process(frontend_process_holder.get("process"))
        sys.stdout.flush()
