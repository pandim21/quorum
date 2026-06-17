"""Turn an exported Band room JSON into a structured, render-ready committee view.

Pure functions, no Streamlit — so the parsing can be unit-tested headless and the
UI layer (app.py) stays thin. One public entry point: build_view(raw) -> dict.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

# --- Static metadata about each committee seat (model fleet + presentation) -----
# Keyed by Band display name. Models/vendors mirror prompts.ROLES; duplicated here
# (not imported) so the demo has ZERO dependency on the live agent stack.
ROLE_META: dict[str, dict] = {
    "Portfolio Manager":           {"short": "PM",    "model": "GPT-5.2",        "vendor": "OpenAI",      "color": "#102A43", "seat": "Chair"},
    "Research Analyst":            {"short": "RES",   "model": "Qwen2.5-72B",    "vendor": "Featherless", "color": "#48566B", "seat": "Research"},
    "Bull Analyst":                {"short": "BULL",  "model": "DeepSeek-V4",    "vendor": "DeepSeek",    "color": "#1B7A4B", "seat": "Debate"},
    "Bear Analyst":                {"short": "BEAR",  "model": "Grok-4",         "vendor": "xAI",         "color": "#B42318", "seat": "Debate"},
    "Risk Officer":                {"short": "RISK",  "model": "o3",             "vendor": "OpenAI",      "color": "#B7791F", "seat": "Gate"},
    "Chief Risk Officer":          {"short": "CRO",   "model": "Gemini-2.5-Pro", "vendor": "Google",      "color": "#6941C6", "seat": "Escalation"},
    "Export Controls Analyst":     {"short": "GEO",   "model": "Grok-4",         "vendor": "xAI",         "color": "#0E7490", "seat": "Specialist"},
    "Valuation Specialist":        {"short": "VAL",   "model": "DeepSeek-V4",    "vendor": "DeepSeek",    "color": "#0E7490", "seat": "Specialist"},
    "Forensic Accounting Analyst": {"short": "FOR",   "model": "Gemini-2.5-Pro", "vendor": "Google",      "color": "#0E7490", "seat": "Specialist"},
    "Independent Auditor":         {"short": "AUDIT", "model": "Gemini-2.5-Pro", "vendor": "Google",      "color": "#0B5563", "seat": "Control"},
}
USER_META = {"short": "PM/HUMAN", "model": "", "vendor": "", "color": "#0B1F3A", "seat": "Human"}

COMPANY_NAMES = {
    "NVDA": "NVIDIA Corporation",
    "EA": "Electronic Arts Inc.",
    "AAPL": "Apple Inc.",
}

_MENTION_RE = re.compile(r"@\[\[([0-9a-fA-F\-]+)\]\]")
_HANDLE_RE = re.compile(r"@[A-Za-z0-9._/\-]+")
# PM internal polling/reminder thoughts from a messy endgame — pure noise to a viewer.
_NOISE_THOUGHT = re.compile(r"\b(await|awaiting|waiting|still|ignor|reminder|pending|no further action)\b", re.I)


def _clean_text(s: str) -> str:
    """Strip @[[uuid]] tokens and literal handles (@user/agent, @user.name) from
    display text, while keeping plain @Name mentions. Preserves newlines."""
    s = _MENTION_RE.sub("", s)
    s = _HANDLE_RE.sub(lambda m: "" if ("/" in m.group() or "." in m.group()) else m.group(), s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def _fmt_time(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
    except Exception:
        return ""


def _duration(first: str, last: str) -> str:
    try:
        a = datetime.fromisoformat(first.replace("Z", "+00:00"))
        b = datetime.fromisoformat(last.replace("Z", "+00:00"))
        secs = int((b - a).total_seconds())
        return f"{secs // 60}m {secs % 60}s"
    except Exception:
        return ""


def _strip_and_extract(content: str):
    """Remove @[[id]] tokens; pull a trailing JSON object out if the body is one.

    Returns (pre_text, data, prose) where exactly one of data / prose is the
    meaningful payload. Agent replies are '@mention {json}'; the PM's routing
    messages and the memo are prose.
    """
    text = _clean_text(content)
    # Drop a leading literal "@Portfolio Manager" the specialists prepend.
    text = re.sub(r"^@[\w ./-]{0,40}?(?=\{|[A-Z])", "", text, count=1).strip() if text.startswith("@") else text
    start = text.find("{")
    if start != -1:
        end = text.rfind("}")
        if end > start:
            try:
                # strict=False: models sometimes emit raw newlines inside JSON
                # string values, which the default parser rejects.
                data = json.loads(text[start:end + 1], strict=False)
                if isinstance(data, dict):
                    return text[:start].strip(), data, None
            except Exception:
                pass
    return "", None, text


# Intent of a PM routing message, keyed by WHO it is addressed to. Recipient-driven
# (not keyword-driven) because the PM embeds the full case file — which mentions
# "deadlock", "Chief Risk Officer", etc. — inside every routing message.
ROUTE_INTENTS = {
    "Research Analyst": "Commissions the research brief",
    "Bear Analyst": "Hands over the brief + bull case — requests the bear case",
    "Risk Officer": "Sends the debate to the risk gate",
    "Chief Risk Officer": "Escalates the deadlock to the Chief Risk Officer",
    "Export Controls Analyst": "Recruits the Export Controls Analyst for a flagged risk",
    "Valuation Specialist": "Recruits the Valuation Specialist for a flagged risk",
    "Forensic Accounting Analyst": "Recruits the Forensic Accounting Analyst for a flagged risk",
    "Independent Auditor": "Submits the decision for independent audit",
}


def _route_intent(recipients: list[str], bull_seen: bool) -> str:
    r = recipients[0] if recipients else ""
    if r == "Bull Analyst":
        return "Requests the bull's final counter-rebuttal" if bull_seen else "Hands over the brief — requests the bull case"
    return ROUTE_INTENTS.get(r, "Routes the case file")


def _classify(name: str, mtype: str, content: str, is_user: bool):
    if is_user:
        c = content.lower()
        if "approve" in c and len(content) < 120:
            return "approve"
        return "mandate"
    if name == "Portfolio Manager":
        if "INVESTMENT MEMO" in content:
            return "memo"
        if "DRAFT DECISION" in content:
            return "draft"
        if mtype == "thought":
            return "thought"
        return "route"
    if mtype == "thought":
        return "thought"
    return "reply"


def _recipients(msg, name_map) -> list[str]:
    out = []
    for m in (msg.get("metadata") or {}).get("mentions", []) or []:
        nm = m.get("username") or name_map.get(m.get("id"))
        if nm and nm != "p.dimitrelis":
            out.append(nm)
    # de-dup, drop self
    sender = (msg.get("sender") or {}).get("name")
    return [n for i, n in enumerate(out) if n != sender and n not in out[:i]]


def _parse_memo(text: str) -> dict:
    def find(pat, default=""):
        m = re.search(pat, text)
        return m.group(1).strip() if m else default
    audit = re.search(r"Independent Audit:\s*(\w+)\s*[—-]\s*(.+)", text)
    return {
        "recommendation": find(r"Recommendation:\s*([A-Za-z/]+)").upper(),
        "size": find(r"Size:\s*([0-9.]+%)"),
        "risk_max": find(r"risk max\s*([0-9.]+%)"),
        "committee": find(r"Committee:\s*(.+)"),
        "audit_status": (audit.group(1).strip().lower() if audit else ""),
        "audit_note": (audit.group(2).strip() if audit else ""),
        "trail": find(r"Decision trail:\s*(.+)"),
        "date": find(r"INVESTMENT MEMO\s*[—-]\s*\w+\s*[—-]\s*([\d-]+)"),
    }


def build_view(raw: dict) -> dict:
    messages = raw.get("messages", [])
    name_map = {}
    for m in messages:
        s = m.get("sender") or {}
        if s.get("id"):
            name_map[s["id"]] = s.get("name")
        for mention in (m.get("metadata") or {}).get("mentions", []) or []:
            if mention.get("id"):
                name_map.setdefault(mention["id"], mention.get("username"))

    turns: list[dict] = []
    brief: dict | None = None
    memo: dict | None = None
    participated: list[str] = []
    seen: set = set()
    replied: set = set()  # agents who have already given a reply (one per case; Bull twice)

    for i, m in enumerate(messages):
        sender = m.get("sender") or {}
        name = sender.get("name") or "Unknown"
        is_user = sender.get("type") == "User"
        mtype = m.get("message_type", "text")
        content = m.get("content", "") or ""
        kind = _classify(name, mtype, content, is_user)
        # Drop the PM's internal polling/reminder thoughts (endgame noise); keep
        # substantive ones like "Deadlock detected — initiating tie-breaker".
        if kind == "thought" and _NOISE_THOUGHT.search(content):
            continue
        pre, data, prose = _strip_and_extract(content)
        recips = _recipients(m, name_map)
        r_intent = _route_intent(recips, "Bull Analyst" in replied) if kind == "route" else ""

        # Drop PM<->human status chatter: routing messages addressed to no
        # committee agent ("We are at the final approval...", etc.).
        if kind == "route" and not recips:
            continue

        # One reply per agent per case — only the Bull speaks twice (thesis then
        # counter-rebuttal). This collapses Band's at-least-once redelivery dups,
        # the PM's re-asks, AND stray prose notes like "I already reviewed this".
        if kind not in ("memo", "draft", "mandate", "approve"):
            if kind == "reply" and name != "Bull Analyst" and name in replied:
                continue
            if data is not None:
                sig = ("reply", name, json.dumps(data, sort_keys=True))
            elif kind == "route":
                sig = ("route", tuple(recips), r_intent)
            else:
                sig = ("txt", name, (prose or "")[:120])
            if sig in seen:
                continue
            seen.add(sig)
            if kind == "reply":
                replied.add(name)

        if data and name == "Research Analyst" and brief is None:
            brief = data
        if kind == "memo":
            memo = _parse_memo(content)

        display_name = "Human (PM mandate)" if is_user else name
        if not is_user and name in ROLE_META and name not in participated:
            participated.append(name)

        turns.append({
            "i": i,
            "name": name,
            "display_name": display_name,
            "is_user": is_user,
            "kind": kind,
            "time": _fmt_time(m.get("inserted_at", "")),
            "recipients": recips,
            "data": data,
            "prose": prose,
            "route_intent": r_intent,
            "full": _clean_text(content),
        })

    ticker = (brief or {}).get("ticker", raw.get("room", {}).get("title", "—"))
    times = [m.get("inserted_at", "") for m in messages if m.get("inserted_at")]
    return {
        "ticker": ticker,
        "company": COMPANY_NAMES.get(ticker, ticker),
        "brief": brief,
        "memo": memo,
        "turns": turns,
        "participated": participated,
        "duration": _duration(times[0], times[-1]) if len(times) >= 2 else "",
        "msg_count": len(messages),
    }


def role_meta(name: str) -> dict:
    return ROLE_META.get(name, USER_META)


if __name__ == "__main__":  # quick headless sanity check
    import sys
    from pathlib import Path

    for p in sorted((Path(__file__).parent / "transcripts").glob("*.json")):
        view = build_view(json.loads(p.read_text(encoding="utf-8")))
        d = view["memo"] or {}
        print(f"{p.stem.upper():5} | {view['ticker']:5} | turns={len(view['turns']):2} "
              f"| {d.get('recommendation','?')} {d.get('size','?')} "
              f"| audit={d.get('audit_status','?')} | seats={len(view['participated'])} "
              f"| {view['duration']}")
