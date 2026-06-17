"""A LangGraph adapter that guarantees a reply is actually delivered.

Band's stock LangGraphAdapter posts a message to the room ONLY when the model
calls the band_send_message tool. Intermittently a model ends its turn by
*writing* the answer as plain text WITHOUT calling the tool — and then nothing
is sent, no error is raised, the inbound message is acked as "processed", and
Band never redelivers it. The committee hangs forever. That is the root cause of
every "stuck-at-204" stall we saw (PM after the Bull; Bear after the PM).

ReliableLangGraphAdapter closes the gap: it watches each turn, and if the model
finished WITHOUT calling band_send_message, it sends the model's final answer
itself — to whoever the answer @mentions, or failing that, back to the sender of
the message it was answering. One trigger always yields one delivered reply.

Coupling note: this overrides two LangGraphAdapter internals (on_message and
_handle_stream_event). If you bump band-sdk and replies stop flowing, re-check
those two methods against the new version.
"""

from __future__ import annotations

import logging
from typing import Any

from band.adapters import LangGraphAdapter

logger = logging.getLogger("quorum")

_SEND_TOOL = "band_send_message"

# Injected on a retry so the input differs from the silent attempt — a deterministic
# empty turn (model freezing on a hard step) would otherwise repeat identically.
_RETRY_NUDGE = (
    "Your previous attempt produced no message and was discarded. Do NOT stay "
    "silent. Take the next protocol step NOW by calling the appropriate Band tool "
    "(band_lookup_peers, then band_add_participant, then band_send_message — or "
    "band_send_message directly if you are simply replying). Act this turn."
)


class ReliableLangGraphAdapter(LangGraphAdapter):
    """LangGraphAdapter + a fallback that delivers the reply if the model
    forgot to call band_send_message."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # Per-room state for the turn currently being processed. The runtime
        # processes one message per room at a time, so keying by room_id is safe.
        self._turn: dict[str, dict[str, Any]] = {}
        # An empty/no-op turn (nothing sent, no final text to rescue) is re-run
        # up to this many times total — the cure for the intermittent stalls
        # where a model ends its turn without producing its reply or tool calls.
        self._max_attempts = 3

    async def on_message(  # type: ignore[override]
        self,
        msg,
        tools,
        history,
        participants_msg,
        contacts_msg,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        try:
            for attempt in range(1, self._max_attempts + 1):
                self._turn[room_id] = {"sent": False, "final_text": None}
                # On a retry, append a nudge so the input differs from the silent
                # attempt and the model is pushed to act instead of re-freezing.
                turn_contacts = contacts_msg
                if attempt > 1:
                    turn_contacts = (
                        f"{contacts_msg}\n\n{_RETRY_NUDGE}"
                        if contacts_msg
                        else _RETRY_NUDGE
                    )
                await super().on_message(
                    msg,
                    tools,
                    history,
                    participants_msg,
                    turn_contacts,
                    is_session_bootstrap=is_session_bootstrap,
                    room_id=room_id,
                )
                state = self._turn.get(room_id, {})
                if state.get("sent"):
                    return  # delivered normally via band_send_message
                if state.get("final_text"):
                    # Model answered in plain text without calling the tool —
                    # deliver that answer ourselves.
                    await self._deliver_fallback(
                        state["final_text"], tools, msg, room_id
                    )
                    return
                # Nothing delivered: an empty/no-op turn. Re-run so the model gets
                # another shot at its reply (or its recruitment tool calls).
                # band_add_participant is idempotent, so partial-then-retry is safe.
                if attempt < self._max_attempts:
                    logger.warning(
                        "Room %s: turn produced no reply (attempt %d/%d) — retrying.",
                        room_id,
                        attempt,
                        self._max_attempts,
                    )
            logger.warning(
                "Room %s: no reply after %d attempts — giving up (may be an "
                "intentional no-op, e.g. ignoring a duplicate).",
                room_id,
                self._max_attempts,
            )
        finally:
            self._turn.pop(room_id, None)

    async def _handle_stream_event(self, event: Any, room_id: str, tools) -> None:  # type: ignore[override]
        # Preserve the base behaviour (tool_call/tool_result event reporting),
        # then track whether a send happened and capture the final answer text.
        await super()._handle_stream_event(event, room_id, tools)
        if not isinstance(event, dict):
            return
        state = self._turn.get(room_id)
        if state is None:
            return
        etype = event.get("event")
        if etype == "on_tool_start" and event.get("name") == _SEND_TOOL:
            state["sent"] = True
        elif etype == "on_chat_model_end":
            text = self._final_text(event)
            if text:
                state["final_text"] = text

    @staticmethod
    def _final_text(event: dict) -> str | None:
        """Assistant text from an on_chat_model_end event, but only when the
        model did NOT call a tool on that step. A step that calls a tool is
        mid-ReAct, not a final plain-text answer; the genuine final answer is
        the last no-tool model output."""
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        output = data.get("output")
        ai_msg = output
        if not hasattr(ai_msg, "content"):
            gens = getattr(output, "generations", None)
            if gens:
                try:
                    ai_msg = gens[0][0].message
                except Exception:
                    return None
            else:
                return None
        if getattr(ai_msg, "tool_calls", None):
            return None  # this step called a tool — not a final answer
        content = getattr(ai_msg, "content", None)
        if isinstance(content, str):
            return content.strip() or None
        if isinstance(content, list):  # some models return content blocks
            parts = [
                c.get("text", "") if isinstance(c, dict) else str(c) for c in content
            ]
            return "".join(parts).strip() or None
        return None

    async def _deliver_fallback(self, text: str, tools, msg, room_id: str) -> None:
        mentions = self._fallback_mentions(text, tools, msg)
        if not mentions:
            logger.warning(
                "Room %s: model answered without calling %s and no recipient "
                "could be resolved; reply dropped.",
                room_id,
                _SEND_TOOL,
            )
            return
        logger.warning(
            "Room %s: model answered in plain text without calling %s — "
            "auto-delivering its reply to %s.",
            room_id,
            _SEND_TOOL,
            mentions,
        )
        try:
            await tools.send_message(content=text, mentions=mentions)
        except Exception:
            logger.exception("Room %s: fallback send_message failed", room_id)

    @staticmethod
    def _fallback_mentions(text: str, tools, msg) -> list[str]:
        """Who should receive the rescued reply: everyone the text @mentions
        (matched against real participants), else the sender we were answering."""
        participants = list(getattr(tools, "participants", []) or [])
        low = text.lower()
        mentions: list[str] = []
        for p in participants:
            name = p.get("name")
            if name and ("@" + name.lower()) in low:
                mentions.append(p.get("handle") or name)
        if mentions:
            return mentions
        sender_id = getattr(msg, "sender_id", None)
        for p in participants:
            if p.get("id") == sender_id:
                return [p.get("handle") or p.get("name")]
        sender_name = getattr(msg, "sender_name", None)
        return [sender_name] if sender_name else []
