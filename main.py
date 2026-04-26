"""本地开发启动入口。

生产环境请直接使用 Uvicorn/Gunicorn 启动 `app.main:app`，
不要依赖这个脚本管理前端进程。
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from shlex import split
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings

WINDOWS_NEW_PROCESS_GROUP = 0x00000200 if os.name == "nt" else 0


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

    popen_kwargs: dict[str, object] = {
        "cwd": frontend_dir,
        "env": env,
        "text": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = WINDOWS_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    if args:
        executable = shutil.which(args[0])
        if executable:
            args[0] = executable
            process = subprocess.Popen(args, **popen_kwargs)
        elif os.name == "nt":
            # Windows 下 npm/pnpm/yarn 常以 .cmd 形式存在，直接 Popen(list) 可能找不到入口。
            process = subprocess.Popen(command, shell=True, **popen_kwargs)
        else:
            process = subprocess.Popen(args, **popen_kwargs)
    else:
        process = subprocess.Popen(command, shell=True, **popen_kwargs)

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


def _can_bind(host: str, port: int) -> bool:
    """在真正启动服务前先做端口探测，避免把失败留到 Uvicorn 才暴露。"""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _normalize_bind_host(host: str) -> str:
    """0.0.0.0 / :: 无法直接作为本地探测地址，开发阶段统一回落到 127.0.0.1。"""

    if host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _ensure_backend_port_available() -> None:
    settings = get_settings()
    probe_host = _normalize_bind_host(settings.APP_HOST)
    if _can_bind(probe_host, settings.APP_PORT):
        return

    raise SystemExit(
        (
            f"[launcher] 无法启动后端：{probe_host}:{settings.APP_PORT} 已被占用。\n"
            "请先关闭占用该端口的进程，或在 .env 中调整 APP_PORT / FRONTEND_DEV_ORIGIN / VITE_API_PROXY_TARGET。"
        )
    )


def _print_boot_banner() -> None:
    settings = get_settings()
    backend_origin = f"http://{_normalize_bind_host(settings.APP_HOST)}:{settings.APP_PORT}"
    print("[launcher] 本地联调启动中")
    print(f"[launcher] backend -> {backend_origin}")
    if settings.START_FRONTEND_WITH_BACKEND and settings.is_development:
        print(f"[launcher] frontend -> {settings.FRONTEND_DEV_ORIGIN}")


def _stop_process_tree(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            process.wait(timeout=8)
            return

        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    from app.main import app

    settings = get_settings()
    _ensure_backend_port_available()
    _print_boot_banner()
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
            app,
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=False,
        )
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        frontend_thread.join(timeout=1.0)
        _stop_process_tree(frontend_process_holder.get("process"))
        sys.stdout.flush()
