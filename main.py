"""
主入口：支持 MCP 模式和 HTTP 模式
  python main.py          -> HTTP 模式（调试用）
  python main.py --mcp    -> MCP stdio 模式（供 OpenClaw 调用）
"""
import sys
import asyncio
import logging


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "--mcp" in sys.argv:
        # MCP stdio 模式
        from src.mcp_server import run_mcp_server
        asyncio.run(run_mcp_server())
    else:
        # HTTP 模式
        import uvicorn
        from src.api.routes import app
        from src.config import get_settings
        settings = get_settings()
        
        # 支持命令行指定端口
        port = settings.port
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[idx + 1])
                except ValueError:
                    pass
        
        host = settings.host
        if "--host" in sys.argv:
            idx = sys.argv.index("--host")
            if idx + 1 < len(sys.argv):
                host = sys.argv[idx + 1]
        
        # 如果是 0.0.0.0，改为 localhost 以避免端口绑定问题
        if host == "0.0.0.0":
            host = "127.0.0.1"
        
        print(f"\n[INFO] Starting service on {host}:{port}")
        print(f"[INFO] Access at: http://{host}:{port}")
        print(f"[INFO] API docs: http://{host}:{port}/docs")
        print(f"[INFO] Health check: http://{host}:{port}/health\n")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info" if not settings.debug else "debug",
        )


if __name__ == "__main__":
    main()
