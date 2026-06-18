"""
Shared Mihomo API client for server-monitor-bot
通过 SSH 调用家里 eqi12 的 Mihomo API
"""
import asyncio
import json
import logging
import os
import shlex

logger = logging.getLogger(__name__)


async def mihomo_api(method: str, path: str, payload: dict = None) -> dict:
    """通过 SSH 调用家里 eqi12 的 Mihomo API（3次重试，指数退避）
    注意：curl 命令通过 SSH stdin 传递，避免 token 出现在 ps 命令行中
    """
    token = os.environ.get("MIHOMO_API_TOKEN", "")
    curl_parts = [
        "curl", "-s", "-X", method,
        f"http://127.0.0.1:19090{path}",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
    ]
    if payload is not None:
        curl_parts += ["-d", json.dumps(payload)]
    curl_cmd = shlex.join(curl_parts)

    delays = [1, 2, 4]
    for attempt in range(3):
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "ConnectTimeout=5", "eqi12", "sh",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=curl_cmd.encode()), timeout=15
            )
            if proc.returncode != 0:
                err_msg = stderr.decode().strip() or "unknown"
                if attempt < 2:
                    await asyncio.sleep(delays[attempt])
                    continue
                raise RuntimeError(f"mihomo api error: {err_msg}")
            text = stdout.decode().strip()
            if not text:
                return {}
            return json.loads(text)
        except (asyncio.TimeoutError, OSError) as e:
            if attempt < 2:
                await asyncio.sleep(delays[attempt])
                continue
            raise RuntimeError(f"mihomo api error (timeout): {e}")
    raise RuntimeError("mihomo api error: max retries exceeded")
