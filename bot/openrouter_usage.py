import os
import httpx


async def query() -> dict:
    """Query OpenRouter credits API and return parsed response."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {"ok": False, "error": "OPENROUTER_API_KEY environment variable is not set"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=5.0)) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/credits",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def format_report(data: dict) -> str:
    """Format OpenRouter credits data into a readable text report with emoji."""
    if not data.get("ok", True):
        return f"❌ 查询失败: {data.get('error', 'Unknown error')}"

    if "data" not in data:
        return "❌ 无数据返回"

    credits_data = data.get("data", {})
    if not credits_data:
        return "❌ 无法获取余额数据"

    total_credits = credits_data.get("total_credits", 0)
    total_usage = credits_data.get("total_usage", 0)
    remaining = total_credits - total_usage
    pct = (total_usage / total_credits * 100) if total_credits > 0 else 0

    bar_width = 7
    filled = round(pct / 100 * bar_width)
    if filled == 0 and pct > 0:
        filled = 1
    bar = "▓" * filled + "░" * (bar_width - filled)

    if pct < 50:
        status = "🟢"
    elif pct < 80:
        status = "🟡"
    else:
        status = "🔴"

    lines = [
        "━━━━━━━━━━",
        "  📊 OpenRouter 账户余额",
        "━━━━━━━━━━",
        f"  💰 总额   ${total_credits:.2f}",
        f"  📤 已用   ${total_usage:.4f}",
        "  ────────",
        f"  {status} 剩余   ${remaining:.2f}",
        f"  📈 使用率 {bar} {pct:.1f}%",
        "━━━━━━━━━━",
    ]
    return "\n".join(lines)
