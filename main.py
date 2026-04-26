"""
项目根启动入口：
- 推荐开发启动命令: python main.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.main import app
from app.core.config import get_settings


def _list_listening_pids_windows(port: int) -> set[int]:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return set()

    target = f":{port}"
    pids: set[int] = set()
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if "LISTENING" not in line:
            continue
        if target not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            continue
    return pids


def _kill_process_tree_windows(pid: int) -> bool:
    if pid <= 0:
        return False
    proc = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _cleanup_stale_ports() -> None:
    settings = get_settings()
    ports = {settings.APP_PORT}

    frontend_port = urlparse(settings.FRONTEND_DEV_ORIGIN).port
    if frontend_port:
        ports.add(frontend_port)

    if os.name != "nt":
        return

    current_pid = os.getpid()
    for port in sorted(ports):
        stale_pids = _list_listening_pids_windows(port)
        for stale_pid in sorted(stale_pids):
            if stale_pid == current_pid:
                continue
            if _kill_process_tree_windows(stale_pid):
                print(f"[launcher] 已清理端口 {port} 的旧进程 PID={stale_pid}")


def _start_frontend_dev_server() -> subprocess.Popen[str] | None:
    settings = get_settings()
    if not settings.START_FRONTEND_WITH_BACKEND:
        return None

    frontend_dir = Path(settings.FRONTEND_DIR).resolve()
    if not frontend_dir.exists():
        print(f"[launcher] 前端目录不存在，跳过启动：{frontend_dir}")
        return None

    command = settings.FRONTEND_DEV_COMMAND.strip()
    if not command:
        print("[launcher] FRONTEND_DEV_COMMAND 为空，跳过前端启动")
        return None

    # 开发模式下将前端地址写入环境，便于 Vite 或脚本读取
    env = os.environ.copy()
    parsed = urlparse(settings.FRONTEND_DEV_ORIGIN)
    if parsed.hostname:
        env["VITE_DEV_HOST"] = parsed.hostname
    if parsed.port:
        env["VITE_DEV_PORT"] = str(parsed.port)

    # 兼容 Windows/macOS/Linux：统一使用 shell 执行用户配置命令
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(command, cwd=frontend_dir, env=env, shell=True, creationflags=creationflags)
    print(f"[launcher] 已启动前端开发服务: {command} (cwd={frontend_dir})")
    return proc


def _wait_backend_healthy_and_start_frontend(
    stop_event: threading.Event,
    proc_holder: dict[str, subprocess.Popen[str] | None],
) -> None:
    settings = get_settings()
    if not settings.START_FRONTEND_WITH_BACKEND:
        return

    host = settings.APP_HOST
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    health_url = f"http://{host}:{settings.APP_PORT}/"

    while not stop_event.is_set():
        try:
            req = Request(health_url, method="GET")
            with urlopen(req, timeout=1.2):
                pass
            if stop_event.is_set():
                return
            proc_holder["proc"] = _start_frontend_dev_server()
            return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.4)


def _stop_process(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        _kill_process_tree_windows(proc.pid)
        return
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    _cleanup_stale_ports()
    settings = get_settings()
    frontend_holder: dict[str, subprocess.Popen[str] | None] = {"proc": None}
    stop_event = threading.Event()
    frontend_starter = threading.Thread(
        target=_wait_backend_healthy_and_start_frontend,
        args=(stop_event, frontend_holder),
        daemon=True,
    )
    frontend_starter.start()
    try:
        uvicorn.run(
            "main:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=settings.ENVIRONMENT == "development",
        )
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        frontend_starter.join(timeout=1.0)
        _stop_process(frontend_holder.get("proc"))
        # 避免某些平台下子进程退出后父进程挂起
        sys.stdout.flush()
