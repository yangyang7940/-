"""本地网页应用入口：python app.py"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from matcher import rank_resumes, score_resume
from repository import PROJECT_ROOT, load_jobs, load_resumes


STATIC_DIR = PROJECT_ROOT / "static"
MAX_BODY_SIZE = 2 * 1024 * 1024


class ResumeMatchHandler(BaseHTTPRequestHandler):
    server_version = "ResumeMatch/1.0"

    @property
    def jobs(self) -> list[dict[str, str]]:
        return self.server.jobs  # type: ignore[attr-defined]

    @property
    def resumes(self) -> list[dict[str, str]]:
        return self.server.resumes  # type: ignore[attr-defined]

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[访问] {self.address_string()} - {format_string % args}")

    def _json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"ok": False, "error": message}, status)

    def _read_json(self) -> dict[str, object]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("请求长度无效") from exc
        if content_length <= 0 or content_length > MAX_BODY_SIZE:
            raise ValueError("请求内容为空或超过 2 MB 限制")
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求内容不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("请求内容格式错误")
        return payload

    def _find_job(self, job_id: object) -> dict[str, str]:
        for job in self.jobs:
            if job["job_id"] == str(job_id):
                return job
        raise ValueError("未找到所选岗位")

    def _serve_static(self, relative_path: str) -> None:
        path = (STATIC_DIR / relative_path).resolve()
        if STATIC_DIR.resolve() not in path.parents and path != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = path.read_bytes()
        # Windows 注册表可能把 .css 识别为 application/octet-stream，浏览器会因此拒绝应用样式。
        mime_type = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }.get(path.suffix.lower(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if mime_type.startswith("text/") else mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/api/bootstrap":
            self._json(
                {
                    "ok": True,
                    "jobs": self.jobs,
                    "resumes": [
                        {
                            "resume_id": item["resume_id"],
                            "name": item["name"],
                            "target_role": item["target_role"],
                            "full_text": item["full_text"],
                        }
                        for item in self.resumes
                    ],
                    "stats": {"job_count": len(self.jobs), "resume_count": len(self.resumes)},
                }
            )
        elif route in ("/", "/index.html"):
            self._serve_static("index.html")
        elif route.startswith("/static/"):
            self._serve_static(route.removeprefix("/static/"))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        try:
            payload = self._read_json()
            job = self._find_job(payload.get("job_id"))
            if route == "/api/match":
                resume_text = str(payload.get("resume_text", "")).strip()
                self._json({"ok": True, "job": job, "result": score_resume(resume_text, job)})
            elif route == "/api/rank":
                self._json({"ok": True, "job": job, "results": rank_resumes(self.resumes, job)})
            else:
                self._error("接口不存在", HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._error(str(exc))
        except Exception as exc:  # 保证演示时返回可读错误，不暴露调用栈
            print(f"[错误] {exc!r}")
            self._error("系统处理失败，请检查输入后重试", HTTPStatus.INTERNAL_SERVER_ERROR)


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ResumeMatchHandler)
    server.jobs = load_jobs()  # type: ignore[attr-defined]
    server.resumes = load_resumes()  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="智能简历筛选与岗位匹配系统")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="监听端口，默认 8765")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    url = f"http://{args.host}:{args.port}"
    print("=" * 56)
    print("智能简历筛选与岗位匹配系统已启动")
    print(f"访问地址：{url}")
    print("按 Ctrl+C 停止系统")
    print("=" * 56)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n系统已安全停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
