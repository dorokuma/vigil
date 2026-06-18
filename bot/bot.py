#!/usr/bin/env python3
from __future__ import annotations
import asyncio
import json
import logging
import os
import shlex

import time
from datetime import datetime
from pathlib import Path

import httpx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import psutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import *
from mihomo_api import mihomo_api as _mihomo_api
from vigil_ext import register_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---- 持久化路径 ----
BOT_DIR = Path(__file__).parent
DATA_DIR = BOT_DIR.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ALERT_HISTORY_FILE = DATA_DIR / "alert_history.json"
RECOVERY_FILE = DATA_DIR / "recovery_history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

def load_json(path: Path, default=dict):
    if not path.exists():
        return default()
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default()

def save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_settings():
    return load_json(SETTINGS_FILE)

def save_settings(settings: dict):
    save_json(SETTINGS_FILE, settings)

# ---- Alert History ----
def load_alert_history():
    return load_json(ALERT_HISTORY_FILE, default=list)

def save_alert_record(server: str, reason: str, rtt: float = 0, loss: float = 0):
    history = load_alert_history()
    history.append({
        "time": datetime.now().isoformat(),
        "server": server,
        "reason": reason,
        "rtt": rtt,
        "loss": loss,
    })
    # 保留最近 500 条
    if len(history) > 500:
        history = history[-500:]
    save_json(ALERT_HISTORY_FILE, history)

def load_recovery_history():
    return load_json(RECOVERY_FILE, default=list)

def save_recovery_record(server: str, down_time: str, recovered_at: str):
    history = load_recovery_history()
    history.append({
        "server": server,
        "down_since": down_time,
        "recovered_at": recovered_at,
    })
    if len(history) > 200:
        history = history[-200:]
    save_json(RECOVERY_FILE, history)

# ---- Mihomo API (via SSH) ----


# ---- API 客户端 ----
async def api_get(path: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}{path}", timeout=httpx.Timeout(5.0, connect=5.0))
        resp.raise_for_status()
        return resp.json()

# ---- 工具函数 ----
def fmt_rtt(rtt: float) -> str:
    if rtt <= 0:
        return "❌ 超时"
    color = "🟢" if rtt < 150 else ("🟡" if rtt < 300 else "🔴")
    return f"{color} {rtt:.0f}ms"

def fmt_loss(pct: float) -> str:
    if pct <= 0:
        return "0%"
    return f"{'🔴' if pct >= ALERT_LOSS_THRESHOLD else '🟡'} {pct:.1f}%"

def flag(name: str) -> str:
    return SERVER_FLAGS.get(name, "🌐")

# ---- Handlers ----
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_get("/api/servers")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取状态失败: {e}")
        return
    lines = [f"📊 服务器状态 · {datetime.now().strftime('%H:%M:%S')}", ""]
    for s in data:
        name = s['hostname']
        ok = s.get('online', True)
        rtt = s.get('rtt')
        if rtt and rtt > 0:
            rtt_str = fmt_rtt(rtt)
        elif s.get('ping_status'):
            rtt_str = f"ℹ️ {s['ping_status']}"
        else:
            rtt_str = "❕ 超时"
        lines.append(f"{flag(name)} {'✅' if ok else '⚠️'} {name}")
        lines.append(f"   延迟: {rtt_str}  |  丢包: {fmt_loss(s.get('loss_pct') or 0)}")
    text = "\n".join(lines)
    if not text.strip():
        text = "⚠️ 状态数据异常，请重试"
    await update.message.reply_text(text)

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        try:
            data = await api_get("/api/servers")
        except Exception as e:
            await update.message.reply_text(f"❌ 获取状态失败: {e}")
            return
        lines = [f"🏓 实时延迟 · {datetime.now().strftime('%H:%M:%S')}", ""]
        for s in data:
            rtt = s.get("rtt")
            if rtt and rtt > 0:
                rtt_str = fmt_rtt(rtt)
            elif s.get("ping_status"):
                rtt_str = f"ℹ️ {s['ping_status']}"
            else:
                rtt_str = "❕ 超时"
            lines.append(f"{flag(s['hostname'])} {s['hostname']}: {rtt_str}")
        text = "\n".join(lines)
        if not text.strip():
            text = "⚠️ 延迟数据异常，请重试"
        await update.message.reply_text(text)
        return

    server = args[0]
    time_range = args[1] if len(args) > 1 else "60"
    # Validate time_range: must be positive integer
    if not time_range.isdigit() or int(time_range) <= 0:
        await update.message.reply_text(f"❌ time_range 必须为正整数，当前: {time_range}")
        return
    try:
        data = await api_get(f"/api/ping/{server}?n={time_range}")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取失败: {e}")
        return
    entries = data.get("data",[])
    if not entries:
        await update.message.reply_text(f"📭 {flag(server)} {server}: 暂无数据")
        return
    total = len(entries)
    if total == 0:
        await update.message.reply_text("❌ 无可用服务器数据")
        return
    ok_count = sum(1 for e in entries if e["ok"])
    loss_pct = (total-ok_count)/total*100
    rtts = [e["rtt"] for e in entries if e["ok"] and e["rtt"]>0]
    if rtts:
        summary = f"均值: {sum(rtts)/len(rtts):.0f}ms | 最小: {min(rtts):.0f}ms | 最大: {max(rtts):.0f}ms | 丢包: {loss_pct:.1f}%"
    else:
        summary = f"全部超时，丢包率: {loss_pct:.1f}%"
    await update.message.reply_text(f"{flag(server)} {server} · 最近 {len(entries)} 次探测\n{summary}")

# ---- /proxy test <节点> ----
async def cmd_proxy_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """测试某个节点的延迟（curl google.com）"""
    args = context.args
    if not args:
        await update.message.reply_text("用法: /proxy test <节点名>\n例: /proxy test 🇭🇰 HongKong-01")
        return

    node_name = " ".join(args)
    await update.message.reply_text(f"⏳ 正在测试节点: {node_name} ...")

    try:
        proxies_data = await _mihomo_api("GET", "/proxies")
        all_nodes = set()
        for info in proxies_data.get("proxies", {}).values():
            all_nodes.update(info.get("all", []))

        matched = [n for n in all_nodes if node_name.lower() in n.lower()]
        if not matched:
            await update.message.reply_text(f"❌ 未找到节点: {node_name}")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ 获取节点列表失败: {e}")
        return

    # 测试延迟（直接 curl，从当前已选出口出去）
    test_url = "https://www.google.com/generate_204"
    results = []
    for node in matched[:5]:  # 最多测5个匹配节点
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "ConnectTimeout=5", "eqi12",
                "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}|%{time_total}",
                "--max-time", "10", test_url,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode().strip()
            if "|" in output:
                code, t = output.split("|")
                rtt_ms = float(t) * 1000
                results.append((node, int(code), rtt_ms))
        except Exception:
            pass

    if not results:
        await update.message.reply_text(f"❌ 测试失败（可能当前出口节点不可达）")
        return

    lines = [f"📡 节点测速结果 ({test_url})", ""]
    for node, code, rtt in sorted(results, key=lambda x: x[2]):
        icon = "✅" if code == 204 else ("🟡" if code else "❌")
        lines.append(f"{icon} {node}: {rtt:.0f}ms (HTTP {code})")
    await update.message.reply_text("\n".join(lines))

# ---- /rank ----
async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """延迟排名"""
    try:
        data = await api_get("/api/servers")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取状态失败: {e}")
        return

    valid = []
    for s in data:
        rtt = s.get("rtt")
        if not rtt or rtt <= 0:
            continue
        if not s.get("online", False):
            continue
        valid.append((s["hostname"], rtt, s.get("loss_pct") or 0))

    if not valid:
        await update.message.reply_text("⚠️ 暂无有效数据")
        return

    valid.sort(key=lambda x: x[1])
    lines = [f"🏆 延迟排名 · {datetime.now().strftime('%H:%M:%S')}", ""]
    for i, (name, rtt, loss) in enumerate(valid, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        lines.append(f"{medal} {flag(name)} {name}: {rtt:.0f}ms  丢包: {fmt_loss(loss)}")
    await update.message.reply_text("\n".join(lines))

# ---- /chart <服务器> [n] ----
async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """生成延迟趋势图"""
    args = context.args
    if not args:
        await update.message.reply_text("用法: /chart <服务器> [探测次数]\n例: /chart hongkong 60")
        return

    server = args[0]
    n = int(args[1]) if len(args) > 1 else 60
    n = min(n, 300)

    await update.message.reply_text(f"📈 正在生成 {server} 延迟趋势图 ...")

    try:
        data = await api_get(f"/api/ping/{server}?n={n}")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取数据失败: {e}")
        return

    entries = data.get("data", [])
    if not entries:
        await update.message.reply_text(f"📭 {flag(server)} {server}: 暂无数据")
        return

    ok_entries = [e for e in entries if e.get("ok") and e.get("rtt", 0) > 0]
    if not ok_entries:
        await update.message.reply_text(f"📭 {flag(server)} {server}: 无有效探测数据")
        return

    rtts = [e["rtt"] for e in ok_entries]
    times = [datetime.fromtimestamp(e["ts"] / 1000) for e in ok_entries]

    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "sans-serif"]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, rtts, color="#4FC3F7", linewidth=1.5, alpha=0.9)
    ax.fill_between(times, rtts, alpha=0.2, color="#4FC3F7")
    avg_rtt = sum(rtts) / len(rtts)
    ax.axhline(y=avg_rtt, color="#FF9800", linestyle="--", linewidth=1, label=f"Avg: {avg_rtt:.0f}ms")
    ax.set_title(f"{flag(server)} {server} — Latency Trend ({len(ok_entries)} probes)", fontsize=13)
    ax.set_ylabel("RTT (ms)")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()

    chart_path = DATA_DIR / f"chart_{server}.png"
    if chart_path.exists():
        chart_path.unlink()  # 清理旧图表
    fig.savefig(chart_path, dpi=80)
    plt.close(fig)

    with open(chart_path, "rb") as f:
        await update.message.reply_photo(photo=f,
            caption=f"📈 {flag(server)} {server} 延迟趋势 (最近 {len(ok_entries)} 次)")

# ---- /alert history ----
async def cmd_alert_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """告警历史记录"""
    history = load_alert_history()
    if not history:
        await update.message.reply_text("📭 暂无告警历史记录")
        return

    recent = history[-20:][::-1]
    lines = [f"🚨 告警历史 (最近 {len(recent)} 条)", ""]
    for rec in recent:
        dt = datetime.fromisoformat(rec["time"]).strftime("%m-%d %H:%M")
        rtt_info = f", rtt={rec['rtt']:.0f}ms" if rec.get("rtt") else ""
        loss_info = f", loss={rec['loss']:.1f}%" if rec.get("loss") else ""
        lines.append(f"{dt} {flag(rec['server'])} {rec['server']}: {rec['reason']}{rtt_info}{loss_info}")
    await update.message.reply_text("\n".join(lines))

# ---- /recovery ----
async def cmd_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """恢复通知历史"""
    history = load_recovery_history()
    if not history:
        await update.message.reply_text("📭 暂无恢复记录")
        return

    recent = history[-15:][::-1]
    lines = [f"✅ 恢复历史 (最近 {len(recent)} 条)", ""]
    for rec in recent:
        lines.append(f"{flag(rec['server'])} {rec['server']}: 离线 {rec['down_since']} → 恢复于 {rec['recovered_at']}")
    await update.message.reply_text("\n".join(lines))

# ---- /sys ----
async def cmd_sys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """本机系统状态（CPU/内存/磁盘）"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        lines = [
            f"🖥️ 北京服务器系统状态 · {datetime.now().strftime('%H:%M:%S')}",
            "",
            f"CPU:    {cpu:.1f}%",
            f"内存:   {mem.percent:.1f}%  ({mem.used/1024**3:.1f}GB / {mem.total/1024**3:.1f}GB)",
            f"磁盘:   {disk.percent:.1f}%  ({disk.used/1024**3:.1f}GB / {disk.total/1024**3:.1f}GB)",
        ]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"❌ 获取系统状态失败: {e}")

# ---- /alert ----
async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or args[0] == "list":
        # 检查哪些服务器在冷却中
        cooldown_lines = []
        last_alerts = context.bot_data.get("last_alert", {})
        now = time.time()
        for srv, last_time in last_alerts.items():
            remaining = ALERT_COOLDOWN - (now - last_time)
            if remaining > 0:
                cooldown_lines.append(f"  🔒 {srv}: 冷却中 ({remaining:.0f}s)")
        cooldown_info = ""
        if cooldown_lines:
            cooldown_info = "\n🔒 冷却中服务器:\n" + "\n".join(cooldown_lines)

        await update.message.reply_text(
            f"🔔 当前告警配置\n"
            f"延迟阈值: {context.bot_data.get('rtt_threshold', ALERT_RTT_THRESHOLD):.0f}ms\n"
            f"丢包阈值: {context.bot_data.get('loss_threshold', ALERT_LOSS_THRESHOLD):.0f}%\n"
            f"巡检间隔: {CHECK_INTERVAL}s\n冷却时间: {ALERT_COOLDOWN}s\n\n"
            f"命令:\n"
            f"/alert threshold 300 — 设置延迟阈值 (ms)\n"
            f"/alert loss 20 — 设置丢包阈值 (%)\n"
            f"/alert silence hongkong 2h — 静音某台服务器\n"
            f"/alert history — 告警历史\n"
            f"/recovery — 恢复通知历史"
            + cooldown_info)
        return

    if args[0] == "history":
        await cmd_alert_history(update, context)
        return

    if args[0] == "threshold" and len(args) >= 2:
        try:
            val = float(args[1])
            context.bot_data["rtt_threshold"] = val
            save_settings({**load_settings(), "rtt_threshold": val})
            await update.message.reply_text(f"✅ 延迟阈值已设为 {val:.0f}ms")
        except ValueError:
            await update.message.reply_text("❌ 参数错误")
        return

    if args[0] == "loss" and len(args) >= 2:
        try:
            val = float(args[1])
            context.bot_data["loss_threshold"] = val
            save_settings({**load_settings(), "loss_threshold": val})
            await update.message.reply_text(f"✅ 丢包阈值已设为 {val:.0f}%")
        except ValueError:
            await update.message.reply_text("❌ 参数错误")
        return

    if args[0] == "silence" and len(args) >= 3:
        server = args[1]
        duration = args[2]
        seconds = int(duration[:-1])*3600 if duration.endswith("h") else (
                  int(duration[:-1])*60 if duration.endswith("m") else 3600)
        context.bot_data[f"silenced_{server}"] = time.time() + seconds
        await update.message.reply_text(f"🔇 {server} 已静音 {duration}")
        return

    await update.message.reply_text("❌ 未知命令，请用 /alert list 查看")

async def cmd_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_get("/api/servers")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取监控目标失败: {e}")
        return
    lines = [f"🎯 监控目标 · {datetime.now().strftime('%H:%M:%S')}", ""]
    for s in data:
        lines.append(f"{flag(s['hostname'])} {'✅' if s.get('online') else '⚠️'} {s['hostname']}")
    lines.append(""); lines.append(f"共 {len(data)} 台服务器")
    await update.message.reply_text("\n".join(lines))

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Server Monitor Bot\n\n"
        "/status — 所有服务器实时状态一览\n"
        "/ping [服务器] [时间] — 延迟详情\n"
        "/rank — 服务器延迟排名\n"
        "/chart <服务器> [n] — 延迟趋势图 (默认60个点)\n"
        "/alert list — 告警配置\n"
        "/alert history — 告警历史\n"
        "/alert threshold 300 — 设置延迟阈值\n"
        "/alert silence hongkong 2h — 静音\n"
        "/recovery — 恢复通知历史\n"
        "/minimax — MiniMax 用量查询\n"
        "/openrouter — OpenRouter 用量查询\n"
        "/sys — 北京服务器系统状态\n"
        "/proxy — 切换 Mihomo 节点\n"
        "/proxy test <节点> — 测试节点延迟\n"
        "/targets — 列出所有监控目标\n"
        "/help — 本帮助")

# ---- 后台巡检（增强：告警历史+恢复通知+系统监控） ----
async def check_servers(app: Application):
    app.bot_data.setdefault("last_alert", {})
    app.bot_data.setdefault("down_since", {})   # 服务器离线开始时间
    app.bot_data.setdefault("last_sys_alert", 0)  # 系统告警冷却
    app.bot_data.setdefault("consecutive_loss_count", {})  # 连续丢包计数
    app.bot_data.setdefault("consecutive_rtt_count", {})  # 连续延迟超阈值计数

    sys_cpu_threshold = 90.0
    sys_mem_threshold = 90.0
    sys_disk_threshold = 90.0

    while True:
        threshold = app.bot_data.get("rtt_threshold", ALERT_RTT_THRESHOLD)
        loss_threshold = app.bot_data.get("loss_threshold", ALERT_LOSS_THRESHOLD)

        try:
            data = await api_get("/api/servers")
        except Exception as e:
            logger.warning(f"check_servers: /api/servers API failed ({e}), skipping this round")
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        for s in data:
            server = s["hostname"]
            last_ok = s.get("online", True)
            loss_pct = s.get("loss_pct") or 0
            last_rtt = s.get("rtt") or 0

            # 静音检查（同时清理已过期的 key）
            silenced_key = f"silenced_{server}"
            silenced_until = app.bot_data.get(silenced_key, 0)
            if time.time() < silenced_until:
                continue
            elif silenced_key in app.bot_data and time.time() >= silenced_until:
                del app.bot_data[silenced_key]

            # 冷却检查
            if time.time() - app.bot_data["last_alert"].get(server, 0) < ALERT_COOLDOWN:
                continue

            reason = None
            if not last_ok:
                reason = "已失联"
            elif loss_pct >= loss_threshold:
                consecutive_count = app.bot_data["consecutive_loss_count"].get(server, 0) + 1
                app.bot_data["consecutive_loss_count"][server] = consecutive_count
                if consecutive_count >= 3:
                    reason = f"丢包率 {loss_pct:.1f}% 超过阈值 {loss_threshold:.0f}%（连续3次）"
                    app.bot_data["consecutive_loss_count"][server] = 0
                else:
                    reason = None
            elif last_rtt > 0 and last_rtt >= threshold:
                consecutive_rtt = app.bot_data["consecutive_rtt_count"].get(server, 0) + 1
                app.bot_data["consecutive_rtt_count"][server] = consecutive_rtt
                if consecutive_rtt >= 3:
                    reason = f"延迟 {last_rtt:.0f}ms 超过阈值 {threshold:.0f}ms（连续3次）"
                    app.bot_data["consecutive_rtt_count"][server] = 0
                else:
                    reason = None
            else:
                app.bot_data["consecutive_loss_count"][server] = 0
                app.bot_data["consecutive_rtt_count"][server] = 0
                reason = None

            if reason:
                app.bot_data["last_alert"][server] = time.time()
                save_alert_record(server, reason, rtt=last_rtt, loss=loss_pct)

                # 记录离线开始时间
                if last_ok is False and server not in app.bot_data["down_since"]:
                    app.bot_data["down_since"][server] = datetime.now().strftime("%m-%d %H:%M")

                try:
                    for chat_id in app.bot_data.get("chat_ids", set()):
                        await app.bot.send_message(chat_id=chat_id,
                            text=f"🚨 {flag(server)} {server} 告警\n{reason}")
                except Exception as e:
                    logger.error(f"alert send failed: {e}")
            else:
                # 恢复通知：之前离线，现在恢复了
                if server in app.bot_data["down_since"]:
                    down_since = app.bot_data["down_since"].pop(server)
                    recovered_at = datetime.now().strftime("%m-%d %H:%M")
                    save_recovery_record(server, down_since, recovered_at)
                    try:
                        for chat_id in app.bot_data.get("chat_ids", set()):
                            await app.bot.send_message(chat_id=chat_id,
                                text=f"✅ {flag(server)} {server} 已恢复\n离线: {down_since} → 恢复: {recovered_at}")
                    except Exception as e:
                        logger.error(f"recovery send failed: {e}")

        # 系统资源告警（CPU/内存/磁盘）
        now = time.time()
        if now - app.bot_data.get("last_sys_alert", 0) >= ALERT_COOLDOWN:
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                alerts = []
                if cpu >= sys_cpu_threshold:
                    alerts.append(f"CPU {cpu:.1f}%")
                if mem.percent >= sys_mem_threshold:
                    alerts.append(f"内存 {mem.percent:.1f}%")
                if disk.percent >= sys_disk_threshold:
                    alerts.append(f"磁盘 {disk.percent:.1f}%")

                if alerts:
                    app.bot_data["last_sys_alert"] = now
                    try:
                        for chat_id in app.bot_data.get("chat_ids", set()):
                            await app.bot.send_message(chat_id=chat_id,
                                text=f"🖥️ 北京服务器资源告警\n" + "\n".join(alerts))
                    except Exception as e:
                        logger.error(f"sys alert send failed: {e}")
            except Exception:
                logger.warning("sys resource check failed", exc_info=True)

        await asyncio.sleep(CHECK_INTERVAL)

async def post_init(app: Application):
    app.bot_data.setdefault("chat_ids", set())
    settings = load_settings()
    if "rtt_threshold" in settings:
        app.bot_data["rtt_threshold"] = settings["rtt_threshold"]
    if "loss_threshold" in settings:
        app.bot_data["loss_threshold"] = settings["loss_threshold"]
    app.bot_data["check_task"] = asyncio.create_task(check_servers(app))

    # 注册斜杠命令到 Telegram
    commands = [
        ("status", "所有服务器实时状态"),
        ("ping", "延迟详情"),
        ("rank", "服务器延迟排名"),
        ("chart", "延迟趋势图"),
        ("alert", "告警配置与历史"),
        ("recovery", "恢复通知历史"),
        ("sys", "本机系统状态"),
        ("proxy", "切换 Mihomo 节点"),
        ("targets", "监控目标列表"),
        ("minimax", "MiniMax 用量"),
        ("openrouter", "OpenRouter 用量"),
        ("help", "帮助"),
    ]
    await app.bot.set_my_commands(commands)

async def post_stop(app: Application):
    task = app.bot_data.get("check_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def track_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.application.bot_data["chat_ids"].add(chat_id)

# ---- /proxy ----
async def cmd_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show proxy groups as inline keyboard buttons"""
    try:
        data = await _mihomo_api("GET", "/proxies")
    except Exception as e:
        await update.message.reply_text(f"❌ 获取代理列表失败: {e}")
        return
    proxies = data.get("proxies", {})
    groups = {k: v for k, v in proxies.items() if v.get("type") == "Selector"}
    groups_sorted = sorted(groups.items(), key=lambda x: x[0])
    keyboard = []
    for name, info in groups_sorted:
        now = info.get("now", "?")
        keyboard.append([InlineKeyboardButton(f"{name} [{now}]", callback_data=f"pg:{name}")])
    await update.message.reply_text("🌐 选择代理组:", reply_markup=InlineKeyboardMarkup(keyboard))

async def proxy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("pg:"):
        group = data[3:]
        try:
            info = await _mihomo_api("GET", f"/proxies/{group}")
        except Exception as e:
            await query.edit_message_text(f"❌ 获取节点失败: {e}")
            return
        now = info.get("now", "")
        nodes = info.get("all", [])
        keyboard = []
        for node in nodes:
            mark = "✅ " if node == now else ""
            cb = f"pn:{group}:{node}"
            keyboard.append([InlineKeyboardButton(f"{mark}{node}", callback_data=cb)])
        keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="pb")])
        await query.edit_message_text(f"📁 {group} — 选择节点:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("pn:"):
        rest = data[3:]
        sep = rest.find(":")
        if sep == -1:
            await query.edit_message_text("❌ 数据错误")
            return
        group = rest[:sep]
        node = rest[sep+1:]
        try:
            await _mihomo_api("PUT", f"/proxies/{group}", {"name": node})
            await query.edit_message_text(f"✅ {group} → {node}")
        except Exception as e:
            await query.edit_message_text(f"❌ 切换失败: {e}")
    elif data == "pb":
        try:
            pd = await _mihomo_api("GET", "/proxies")
        except Exception as e:
            await query.edit_message_text(f"❌ 获取代理列表失败: {e}")
            return
        proxies = pd.get("proxies", {})
        groups = {k: v for k, v in proxies.items() if v.get("type") == "Selector"}
        groups_sorted = sorted(groups.items(), key=lambda x: x[0])
        kb = []
        for name, info in groups_sorted:
            now = info.get("now", "?")
            kb.append([InlineKeyboardButton(f"{name} [{now}]", callback_data=f"pg:{name}")])
        await query.edit_message_text("🌐 选择代理组:", reply_markup=InlineKeyboardMarkup(kb))

async def cmd_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from minimax_usage import query as mm_query, format_report as mm_format
        data = await mm_query()
        report = mm_format(data)
        await update.message.reply_text(report, parse_mode=None)
    except Exception as e:
        await update.message.reply_text("❌ MiniMax 查询失败: " + str(e))


async def cmd_openrouter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from openrouter_usage import query as or_query, format_report as or_format
        data = await or_query()
        report = or_format(data)
        await update.message.reply_text(report, parse_mode=None)
    except Exception as e:
        await update.message.reply_text("❌ OpenRouter 查询失败: " + str(e))

def main():
    app = (Application.builder()
        .token(BOT_TOKEN)
        .base_url(WORKER_URL)
        .post_init(post_init)
        .post_stop(post_stop)
        .build())

    cmd_map = {
        "status": cmd_status, "ping": cmd_ping, "alert": cmd_alert,
        "proxy": cmd_proxy, "help": cmd_help, "targets": cmd_targets,
        "start": cmd_help, "h": cmd_help, "minimax": cmd_usage,
        "rank": cmd_rank, "chart": cmd_chart, "recovery": cmd_recovery,
        "sys": cmd_sys, "openrouter": cmd_openrouter,
    }
    for cmd, handler in cmd_map.items():
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(CallbackQueryHandler(proxy_callback, pattern="^p"))
    register_handlers(app)
    for cmd in ["status", "ping", "alert"]:
        app.add_handler(CommandHandler(cmd, track_chat), group=1)

    logger.info("bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
