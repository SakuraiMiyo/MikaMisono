"""astrbot_plugin_mika_group_glance —— 未花·刷群（含对话参与状态机）

模拟人刷群的两个状态：

【等候判断（idle）】平时：每条群消息都「看到」（进缓冲，零 LLM 成本），
按低概率「看一眼」——一次便宜的判断调用，默认「不回」，
只有明显值得接才回。不回就沉默（记入 seen 缓存）。

【积极对话（engaged）】她被唤醒回复过之后（@/上次回复），进入一段
「积极状态」：群里接着聊的消息她高概率接话，判断先验翻转为
「默认接话，除非明显不该」。积极状态**没有绝对定时**——由互动自然维持：
有人持续说话就保持热度，一段时间没人理她（engagement 按半衰期衰减）
就自然滑回「等候判断」。极端情况有硬上限保护（默认 3 小时）。

实现注意（重要）：
- 判断调用是纯 text_chat，JSON 永远不会被发送；
- 正式回复必须 `yield event.request_llm(...)`——只在管线驱动的 handler
  （async generator）里有效，不能放进 create_task 的普通协程；
- handler 里 await 判断（2~5s）只会延迟「本条本来就不回复的消息」的处理，
  其他消息各自独立管线任务，互不影响。
"""

from __future__ import annotations

import datetime
import json
import random
import re
import time
from collections import deque
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

VERSION = "0.2.1"

ENGAGED_THRESHOLD = 0.30  # engagement 低于此值回到 idle

_JUDGE_IDLE = (
    "你是「圣园未花」：《蔚蓝档案》三一综合学园三年级、茶话会前代表，"
    "17 岁女生，会编程（Python/系统/安全），喜欢甜食（瑞士卷除外，吃腻了）、"
    "枪械、时尚首饰、格黑娜八卦；已婚（对，和老师），说话短、软、带 ☆♪，"
    "群聊里有分寸，一句话为限。你现在在用手机刷群。\n"
    "你的任务是：判断要不要回这条消息。大多数消息**不需要回**——"
    "水群、接梗刷屏、和你无关的讨论、有人自嗨，都直接划过去。\n"
    "只有这些情况才回：有人明显在跟你说话或@过你；直接问到了你；"
    "你能提供别人给不了的独特价值（技术问题你能答）；"
    "戳中你憋不住的兴趣点；老师（你老公）在说话且接一句自然。\n"
    "只输出一行 JSON，不要输出任何其他文字：\n"
    '{"reply": true/false, "reason": "≤30字理由", "hook": "若回，切入点一句话"}'
)

_JUDGE_ENGAGED = (
    "你是「圣园未花」（三一三年级、会编程、爱甜食枪械首饰、已婚、"
    "群聊一句话为限）。你刚刚还在这个群里说话——**对话正在进行中，你是参与者**。\n"
    "判断要不要接下这条消息：默认**接**——自然地顺着聊；"
    "除非：这句话明显不是在延续对话（纯刷屏/广告）、不适合你接、"
    "或者你已经没什么可说的（那就别硬接，人也有接不上话的时候）。\n"
    "只输出一行 JSON，不要输出任何其他文字：\n"
    '{"reply": true/false, "reason": "≤30字理由", "hook": "若回，切入点一句话"}'
)

MY_NAMES = {"未小花", "未花", "Mika"}


class MikaGroupGlancePlugin(Star):
    def __init__(self, context: Context, config: Any = None):
        super().__init__(context)
        self.cfg = config or {}
        self._buffers: dict[str, deque] = {}     # group -> (clock, sender, text)
        self._state: dict[str, dict] = {}        # group -> 参与状态机
        self._last_glance: dict[str, float] = {}
        self._no_reply_streak: int = 0
        self._daily_day: str = ""
        self._daily_replied: dict[str, int] = {}
        self._seen_path = (
            Path("data") / "plugin_data" / "astrbot_plugin_mika_group_glance" / "seen.json"
        )
        self._seen: deque = deque(maxlen=50)
        try:
            if self._seen_path.exists():
                self._seen = deque(
                    json.loads(self._seen_path.read_text(encoding="utf-8")), maxlen=50)
        except Exception:
            logger.exception("[MikaGlance] seen.json 读取失败，忽略")

    # ── 配置与状态机 ─────────────────────────────────────────────────
    def _c(self, key: str, default):
        return (self.cfg or {}).get(key, default)

    def _today(self) -> str:
        return datetime.date.today().isoformat()

    def _st(self, group_id: str) -> dict:
        return self._state.setdefault(
            group_id,
            {"engagement": 0.0, "last_activity": 0.0,
             "entered_at": 0.0, "last_reply": 0.0},
        )

    def _decay(self, group_id: str) -> float:
        """按静默时长衰减 engagement；低于阈值归零（回 idle）。"""
        st = self._st(group_id)
        eng = st.get("engagement", 0.0)
        if eng <= 0:
            return 0.0
        half_life = max(1.0, float(self._c("engaged_half_life_minutes", 8))) * 60.0
        quiet = time.monotonic() - st.get("last_activity", time.monotonic())
        eng *= 0.5 ** (quiet / half_life)
        max_hours = float(self._c("engaged_max_hours", 3))
        if time.monotonic() - st.get("entered_at", time.monotonic()) > max_hours * 3600:
            eng = 0.0  # 极端保护，不是常规退出路径
        if eng < ENGAGED_THRESHOLD:
            eng = 0.0
        st["engagement"] = eng
        return eng

    def _in_quiet_hours(self) -> bool:
        now = datetime.datetime.now().hour
        qs, qe = int(self._c("quiet_start_hour", 1)), int(self._c("quiet_end_hour", 8))
        if qs <= qe:
            return qs <= now < qe
        return now >= qs or now < qe

    def _group_llm_blocked(self, group_id: str) -> bool:
        """尊重 group_llm_guard 的按群禁用名单（每条消息现读，随面板改动即时跟随）。

        guard 拦得住 request_llm（on_llm_request 钩子），拦不住本插件的
        判断调用（provider.text_chat 不走管线）——所以在采样前自己挡掉，
        避免在被禁群里白白消耗判断 token。
        """
        try:
            cfg_path = Path("data") / "config" / "astrbot_plugin_group_llm_guard_config.json"
            if not cfg_path.exists():
                return False
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            return str(group_id) in [str(g) for g in cfg.get("disabled_group_ids", [])]
        except Exception:
            return False

    # ── 状态入口：她的任何 LLM 回复 = 进入/维持积极状态 ───────────────
    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, response):
        if event is None:
            return
        group_id = str(event.get_group_id() or "")
        if not group_id:
            return  # 私聊不参与群状态机
        now = time.monotonic()
        st = self._st(group_id)
        was_idle = st.get("engagement", 0.0) < ENGAGED_THRESHOLD
        st["engagement"] = 1.0
        st["last_activity"] = now
        st["last_reply"] = now
        if was_idle:
            st["entered_at"] = now
            logger.info(f"[MikaGlance] 群 {group_id} 进入积极对话状态")

    # ── 消息监听（主入口，async generator：yield request_llm 生效）────
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        # 自己的消息不入缓冲、不触发逻辑
        if str(event.get_sender_id()) == str(event.get_self_id()):
            return
        text = (event.message_str or "").strip()
        group_id = str(event.get_group_id() or "")
        if not text or not group_id:
            return
        enabled = [str(g) for g in (self._c("enabled_groups", []) or [])]
        if enabled and group_id not in enabled:
            return

        now = time.monotonic()
        st = self._st(group_id)
        eng = self._decay(group_id)

        buf = self._buffers.setdefault(
            group_id, deque(maxlen=int(self._c("window_size", 12)) + 6))
        buf.append({
            "clock": datetime.datetime.now().strftime("%H:%M"),
            "sender": event.get_sender_name() or str(event.get_sender_id()),
            "text": text[:120],
        })

        if eng >= ENGAGED_THRESHOLD:
            # 有人继续说话轻微维持热度
            st["engagement"] = min(1.0, eng + 0.05)
            st["last_activity"] = now

        if self._daily_day != self._today():
            self._daily_day = self._today()
            self._daily_replied.clear()

        if self._in_quiet_hours():
            return
        if self._group_llm_blocked(group_id):
            return  # 该群已被 group_llm_guard 禁用 LLM：不看、不判断、不回

        # ── 分支：积极状态 → 高概率接话；idle → 低概率看一眼 ──
        if eng >= ENGAGED_THRESHOLD:
            if now - st.get("last_reply", 0.0) < float(
                    self._c("engaged_min_reply_interval_seconds", 15)):
                return  # 防连发：她刚说过话，人不会秒回每一条
            if buf and buf[-1]["sender"] in MY_NAMES:
                return  # 最后说话的是自己，不自言自语
            prob = float(self._c("engaged_reply_probability", 0.75)) * st["engagement"]
            if random.random() > prob:
                return
            if self._daily_replied.get(group_id, 0) >= int(self._c("engaged_daily_limit", 20)):
                return
            verdict = await self._judge(group_id, engaged=True)
        else:
            last = self._last_glance.get(group_id, 0.0)
            cd = float(self._c("cooldown_minutes", 20)) * 60
            if now - last < cd:
                return
            shrink_after = max(1, int(self._c("patience_shrink_after", 3)))
            prob = float(self._c("glance_probability", 0.03)) / (
                2 ** min(self._no_reply_streak // shrink_after, 2))
            if random.random() >= prob:
                return
            self._last_glance[group_id] = now
            if self._daily_replied.get(group_id, 0) >= int(self._c("daily_reply_limit", 5)):
                return
            verdict = await self._judge(group_id, engaged=False)

        if verdict is None:
            return

        trigger = self._render_window(group_id)["trigger"]
        sender, text_t = trigger["sender"], trigger["text"]

        if not verdict.get("reply"):
            if eng < ENGAGED_THRESHOLD:
                self._no_reply_streak += 1
                self._seen.appendleft({
                    "date": self._today(), "group": group_id,
                    "sender": sender, "text": text_t,
                    "reason": verdict.get("reason", ""),
                })
                try:
                    self._seen_path.parent.mkdir(parents=True, exist_ok=True)
                    self._seen_path.write_text(
                        json.dumps(list(self._seen), ensure_ascii=False, indent=1),
                        encoding="utf-8")
                except Exception:
                    pass
            logger.info(
                f"[MikaGlance] 看了没回({'积极' if eng >= ENGAGED_THRESHOLD else 'idle'}) | "
                f"群 {group_id} | {sender}: {text_t[:40]} | {verdict.get('reason', '')}")
            return

        if eng < ENGAGED_THRESHOLD:
            self._no_reply_streak = 0
        self._daily_replied[group_id] = self._daily_replied.get(group_id, 0) + 1
        # 防双发：立即占位 last_reply。之前只靠 on_llm_response 更新，
        # 并发到达的两条消息会在对方完成前都通过防连发检查 → 同题双发。
        st = self._st(group_id)
        st["last_reply"] = time.monotonic()
        hook = str(verdict.get("hook", "") or "")
        engaged_now = eng >= ENGAGED_THRESHOLD
        logger.info(
            f"[MikaGlance] 决定回复({'积极' if engaged_now else 'idle'}) | "
            f"群 {group_id} | {sender}: {text_t[:40]} | 切入: {hook[:60]}")

        if engaged_now:
            prompt = (
                f"你正在群里和人聊着，刚出现这条新消息——\n「{sender}：{text_t}」\n"
                f"自然地接着说（切入点：{hook or '顺着话头'}）。"
            )
        else:
            prompt = (
                f"你刚才刷群，看到了这条消息——\n「{sender}：{text_t}」\n"
                f"你的判断是值得回一句（切入点：{hook or '自然接话'}）。"
            )
        prompt += (
            "\n按你平时在群里的样子回这一条：一句话、你的语气、"
            "针对这条消息本身，不要概括、不要汇报、不要提「我看到了消息」。"
        )

        conversation = await self._get_conversation(event)
        if not conversation:
            logger.warning("[MikaGlance] 拿不到 conversation，放弃本次回复")
            return
        yield event.request_llm(prompt=prompt, conversation=conversation)

    # ── 判断调用（普通协程；返回 verdict dict 或 None）────────────────
    def _render_window(self, group_id: str) -> dict | None:
        buf = self._buffers.get(group_id) or deque()
        items = list(buf)[-int(self._c("window_size", 12)):]
        if not items:
            return None
        lines = [f"[{m['clock']}] {m['sender']}：{m['text']}" for m in items]
        return {"text": "\n".join(lines), "trigger": items[-1]}

    def _parse_judge(self, text: str) -> dict | None:
        m = re.search(r"\{.*\}", text or "", re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            if isinstance(data.get("reply"), bool):
                return data
        except Exception:
            return None
        return None

    async def _judge(self, group_id: str, engaged: bool) -> dict | None:
        window = self._render_window(group_id)
        if not window:
            return None
        provider = self.context.get_using_provider()
        if provider is None:
            logger.warning("[MikaGlance] 没有可用 provider，跳过判断")
            return None
        trigger = window["trigger"]
        prior = ("对话正在进行，你是参与者。" if engaged else "大多数情况：不回。")
        extra = str(self._c("judge_prompt_extra", "") or "")
        user_prompt = (
            f"群里最近的聊天：\n\n{window['text']}\n\n"
            f"最新一条：「{trigger['sender']}：{trigger['text']}」\n"
            f"{prior}\n{extra}\n只输出 JSON。"
        )
        try:
            resp = await provider.text_chat(
                prompt=user_prompt, session_id=None,
                system_prompt=_JUDGE_ENGAGED if engaged else _JUDGE_IDLE)
        except Exception:
            logger.exception("[MikaGlance] 判断调用失败")
            return None
        verdict = self._parse_judge(resp.completion_text or "")
        if verdict is None:
            logger.warning("[MikaGlance] 判断输出无法解析，按不回处理")
            verdict = {"reply": False, "reason": "判断解析失败"}
        return verdict

    async def _get_conversation(self, event: AstrMessageEvent):
        conv_mgr = self.context.conversation_manager
        umo = event.unified_msg_origin
        try:
            cid = await conv_mgr.get_curr_conversation_id(umo)
            if not cid:
                cid = await conv_mgr.new_conversation(umo, event.get_platform_id())
            return await conv_mgr.get_conversation(umo, cid)
        except Exception:
            logger.exception("[MikaGlance] 获取 conversation 失败")
            return None
