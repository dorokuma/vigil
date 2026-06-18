"""
Vigil + Mihomo 扩展模块
为 server-monitor bot 增加 Vigil 数据展示和 Mihomo 增强控制
"""
import json
import logging
import os
import shlex
import asyncio
import time
from datetime import datetime
from mihomo_api import mihomo_api as _mihomo_api
from typing import Optional

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

# ── Vigil 采集端 API ──────────────────────────────────────
VIGIL_API = "http://127.0.0.1:9901"


async def _vigil_get(path: str) -> list | dict:
    """调用 Vigil 采集端 API"""
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(f"{VIGIL_API}{path}")
        resp.raise_for_status()
        return resp.json()





# ── /vigil 命令 ────────────────────────────────────────────

async def cmd_vigil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """展示所有安装了 Agent 的服务器的系统状态"""
    try:
        data = await _vigil_get("/status")
    except Exception as e:
        await update.message.reply_text(f"❌ Vigil API 调用失败: {e}")
        return

    if not data:
        await update.message.reply_text("📭 暂无 Vigil Agent 上报数据")
        return

    lines = ["📊 **Vigil 系统监控**\n"]
    for s in data:
        hostname = s.get("hostname", "?")
        is_offline = s.get("is_offline", False)
        cpu = s.get("cpu_percent", 0)
        mem = s.get("memory_percent", 0)
        uptime_sec = s.get("uptime", 0)
        rtt = s.get("rtt", None)
        load = s.get("load", {})

        if is_offline:
            flag = "🔴"
            detail = "离线"
        else:
            flag = "🟢"
            parts = []
            parts.append(f"CPU {cpu:.1f}%")
            parts.append(f"内存 {mem:.1f}%")
            if rtt is not None and rtt > 0:
                parts.append(f"延迟 {rtt:.0f}ms")
            if uptime_sec > 0:
                days = uptime_sec // 86400
                hours = (uptime_sec % 86400) // 3600
                parts.append(f"运行 {days}d{hours}h")
            detail = " | ".join(parts)

        lines.append(f"{flag} **{hostname}**: {detail}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /mihomo 命令 ──────────────────────────────────────────

def _format_bytes(b: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


async def cmd_mihomo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mihomo 状态和控制"""
    args = context.args
    if not args:
        await _mihomo_show_status(update, context)
        return

    sub = args[0].lower()

    if sub == "rules":
        await _mihomo_show_rules(update, context)
    elif sub == "traffic":
        await _mihomo_show_traffic(update, context)
    elif sub == "connections":
        await _mihomo_show_connections(update, context)
    elif sub == "restart":
        await _mihomo_restart(update, context)
    else:
        await update.message.reply_text(
            "用法:\n"
            "/mihomo — 查看概览\n"
            "/mihomo rules — 查看规则\n"
            "/mihomo traffic — 查看流量\n"
            "/mihomo connections — 查看连接数\n"
            "/mihomo restart — 重启 Mihomo"
        )


async def _mihomo_show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mihomo 概览"""
    try:
        version = await _mihomo_api("GET", "/version")
        proxies = await _mihomo_api("GET", "/proxies")
    except Exception as e:
        await update.message.reply_text(f"❌ Mihomo API 调用失败: {e}")
        return

    ver = version.get("version", "?")
    # 统计代理组和节点数
    groups = {}
    all_proxies = proxies.get("proxies", {})
    for name, info in all_proxies.items():
        t = info.get("type", "")
        if t == "Selector":
            now = info.get("now", "?")
            all_count = info.get("all", [])
            groups[name] = {"now": now, "count": len(all_count)}

    lines = [f"🤖 **Mihomo** v{ver}\n"]
    for gname, ginfo in sorted(groups.items()):
        lines.append(f"  📁 {gname}: **{ginfo['now']}** ({ginfo['count']}个节点)")
    lines.append(f"\n总代理组: {len(groups)}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _mihomo_show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看 Mihomo 规则"""
    try:
        rules = await _mihomo_api("GET", "/rules")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取规则失败: {e}")
        return

    rule_list = rules.get("rules", [])
    if not rule_list:
        await update.message.reply_text("📭 无规则")
        return

    lines = ["📜 **Mihomo 规则**\n"]
    for i, rule in enumerate(rule_list[:30]):  # 最多显示30条
        payload = rule.get("payload", "")
        proxy = rule.get("proxy", "")
        lines.append(f"  {i+1}. {payload} → {proxy}")

    if len(rule_list) > 30:
        lines.append(f"\n... 共 {len(rule_list)} 条规则")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _mihomo_show_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看 Mihomo 流量"""
    try:
        traffic = await _mihomo_api("GET", "/traffic")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取流量失败: {e}")
        return

    up = traffic.get("up", 0)
    down = traffic.get("down", 0)

    await update.message.reply_text(
        "📊 **Mihomo 实时流量**\n\n"
        f"  📤 上传: {_format_bytes(up)}/s\n"
        f"  📥 下载: {_format_bytes(down)}/s",
        parse_mode="Markdown"
    )


async def _mihomo_show_connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看 Mihomo 连接数"""
    try:
        conns = await _mihomo_api("GET", "/connections")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取连接失败: {e}")
        return

    total = len(conns.get("connections", []))
    await update.message.reply_text(f"🔗 **Mihomo 连接数**: {total}", parse_mode="Markdown")


async def _mihomo_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """远程重启 Mihomo"""
    await update.message.reply_text("🔄 正在重启 Mihomo...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=5", "eqi12", "systemctl restart mihomo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode == 0:
            await update.message.reply_text("✅ Mihomo 已重启")
        else:
            await update.message.reply_text(f"❌ 重启失败: {stderr.decode().strip()}")
    except Exception as e:
        await update.message.reply_text(f"❌ 重启失败: {e}")


# ── 注册函数（由 bot.py 调用）────────────────────────────

def register_handlers(app):
    """注册所有扩展命令到 bot Application"""
    app.add_handler(CommandHandler("vigil", cmd_vigil))
    app.add_handler(CommandHandler("mihomo", cmd_mihomo))
    logger.info("Vigil + Mihomo 扩展模块已加载")
