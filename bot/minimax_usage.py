import os
import httpx
from datetime import timedelta

MINIMAX_API_URL = "https://www.minimaxi.com/v1/token_plan/remains"


async def query() -> dict:
    api_key = os.environ.get("MINIMAX_CN_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "未找到 MiniMax API Key"}

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0)) as client:
            resp = await client.get(MINIMAX_API_URL, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    data = resp.json()

    model_remains = data.get("model_remains", [])
    if not model_remains:
        return {"ok": False, "error": "接口返回无 model_remains 数据"}

    groups = []
    for m in model_remains:
        groups.append({
            "name": m.get("model_name", "unknown"),
            "5h_pct": m.get("current_interval_remaining_percent", 0),
            "5h_remains": m.get("remains_time", 0),
        })

    return {"ok": True, "groups": groups}


def _format_hours_only(seconds: int) -> str:
    if seconds <= 0:
        return "已用完"
    hours = seconds // 3600
    return f"{hours}小时"


def make_bar(pct: float, width: int = 6) -> str:
    filled = max(1, round(pct / 100 * width)) if pct > 0 else 0
    return "█" * filled + "░" * (width - filled)


def get_status_emoji(pct: float) -> str:
    # 基于用量百分比（低用量=🟢，高用量=🔴）
    # API 返回的是剩余百分比，显示时用 100 - remaining 作为用量
    if pct < 50:
        return "🟢"
    elif pct < 80:
        return "🟡"
    else:
        return "🔴"


def format_report(data: dict) -> str:
    if not data.get("ok"):
        return f"❌ 查询失败: {data.get('error', 'Unknown error')}"

    groups = data.get("groups", [])
    if not groups:
        return "📊 MiniMax 用量\n\n⚠️ 暂无数据"

    g = groups[0]

    # 5h 窗口：用量用于颜色/条/百分比，剩余小时用 pct 算（5小时总窗口配额）
    rem_5h_pct = g["5h_pct"]
    used_5h_pct = 100 - rem_5h_pct
    five_h_rem_hours = int(rem_5h_pct / 100 * 5)

    line = f"{get_status_emoji(used_5h_pct)} {make_bar(used_5h_pct)} {int(used_5h_pct)}%  {five_h_rem_hours}小时"

    lines = [
        "📊 MiniMax 用量",
        "",
        "用量",
        line,
    ]
    return "\n".join(lines).strip()

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(query())
    print(format_report(result))
