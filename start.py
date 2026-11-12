"""
执行顺序：
    1. 向系统申请一个空闲端口；
    2. 在后台守护线程中启动 uvicorn（使用 Server 实例，便于外部控制停止）；
    3. 轮询端口，确认服务已可接受连接；+
    4. 主线程交给 pywebview 创建窗口；
    5. 窗口关闭后主动通知服务退出，并结束进程。

关于进程退出的问题：
    webview.start() 返回只代表窗口已关闭，并不意味着进程会退出。守护线程（daemon=True）只在python正常结束时才被清理，而 uvicorn 的事件循环仍会在后台空转；此外 pythonnet 承载的.NET侧可能残留非后台线程，导致在finalize阶段被卡住——表现出来就是"窗口关了、python.exe 还在任务管理器里"。
    所以我就把退出流程设计了下：
        a) 通过 server.should_exit 通知 uvicorn 优雅停止；
        b) 等待后调用 os._exit(0) 强制结束进程，确保不留残余。
    数据在每次事务提交时即已落盘，强制退出不会造成数据丢失。
"""

import os
import socket
import threading
import time

import uvicorn
import webview

from app.api import app
from app.config import APP_TITLE, WINDOW_HEIGHT, WINDOW_WIDTH


def find_free_port() -> int:
    """向操作系统申请一个尚未占用的端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until_ready(port: int, timeout: float = 10.0) -> bool:
    """轮询目标端口，直到能建立连接或超时"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> None:
    port = find_free_port()

    # feat：使用 Server 实例而非 uvicorn.run()，使webview线程停止后，可通知后端服务自行停止。
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not wait_until_ready(port):
        server.should_exit = True
        raise RuntimeError(f"后端服务未能在 {port} 端口启动")

    webview.create_window(
        APP_TITLE,
        f"http://127.0.0.1:{port}",
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(900, 600),
    )

    # 阻塞，直到所有窗口关闭
    webview.start()

    # ----前端webview关闭后，关闭后端线程----
    server.should_exit = True

    # 最多等待3秒，让uvicorn完成关闭流程
    thread.join(timeout=3)
    os._exit(0)


if __name__ == "__main__":
    main()
