"""Quorum — AI Investment Committee · replay terminal.

A read-only, institutional-grade replay of real committee meetings coordinated
through Band. Reads committed transcripts (transcripts/*.json), makes ZERO API
calls, needs no keys — so it can never burn credits or crash a live demo.

Run:  streamlit run app.py     (or:  uv run streamlit run app.py)
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from replay_data import build_view, role_meta

TRANSCRIPTS = Path(__file__).parent / "transcripts"
ORDER = ["nvda", "ea", "aapl"]

st.set_page_config(page_title="Quorum — AI Investment Committee", page_icon="◆", layout="wide")

# --------------------------------------------------------------------------- CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

html, body, [class*="css"], .stMarkdown { font-family: 'Inter', system-ui, sans-serif; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px; }
#MainMenu, footer, .stDeployButton { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
:root { --ink:#1A2433; --muted:#5A6B82; --line:#E4E9F0; --gold:#B08D57; --navy:#102A43; }

/* ---- top brand band ---- */
.brandbar { background: linear-gradient(180deg,#0E2440 0%,#10294A 100%); color:#fff;
  border-radius:12px; padding:20px 26px; margin-bottom:18px; border:1px solid #0A1C33;
  box-shadow:0 6px 22px rgba(13,32,58,.18); display:flex; justify-content:space-between; align-items:center; }
.brandbar .mark { font-family:'Newsreader',serif; font-size:30px; font-weight:600; letter-spacing:.5px; }
.brandbar .mark b { color:var(--gold); font-weight:600; }
.brandbar .sub { font-size:12.5px; color:#A9BCD6; letter-spacing:2.5px; text-transform:uppercase; margin-top:2px; }
.brandbar .fund { text-align:right; font-size:12.5px; color:#C7D5E8; line-height:1.5; }
.brandbar .fund b { color:#fff; font-size:13.5px; }

/* ---- decision hero ---- */
.hero { background:#fff; border:1px solid var(--line); border-radius:12px; padding:22px 26px;
  box-shadow:0 2px 10px rgba(16,42,67,.05); margin-bottom:16px; }
.hero-top { display:flex; justify-content:space-between; align-items:flex-start; gap:20px; flex-wrap:wrap; }
.hero .tkr { font-family:'Newsreader',serif; font-size:34px; font-weight:600; color:var(--navy); line-height:1; }
.hero .co { color:var(--muted); font-size:14px; margin-top:5px; }
.hero .sub2 { color:var(--muted); font-size:12px; margin-top:9px; letter-spacing:.3px; }
.rec { display:inline-flex; align-items:center; gap:10px; }
.rec .verdict { font-size:13px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
  padding:9px 18px; border-radius:8px; }
.v-buy{ background:#E7F4ED; color:#1B7A4B; border:1px solid #BfE3CF;}
.v-hold{ background:#FBF1DE; color:#9A6A12; border:1px solid #EAD5A8;}
.v-sell{ background:#FBE9E7; color:#B42318; border:1px solid #F0C4Bd;}
.hero-metaline { display:flex; gap:26px; margin-top:16px; padding-top:15px; border-top:1px solid var(--line); flex-wrap:wrap;}
.hm { font-size:12px; color:var(--muted); }
.hm b { display:block; font-size:18px; color:var(--ink); font-weight:600; margin-top:2px; }
.badge { display:inline-block; font-size:11px; font-weight:700; letter-spacing:.8px; text-transform:uppercase;
  padding:4px 10px; border-radius:6px; }
.b-pass{ background:#E7F4ED; color:#1B7A4B;} .b-qual{ background:#FBF1DE; color:#9A6A12;}
.b-fail{ background:#FBE9E7; color:#B42318;} .b-none{ background:#EEF1F5; color:#5A6B82;}

/* ---- metric strip ---- */
.metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:8px; }
.metric { background:#fff; border:1px solid var(--line); border-radius:10px; padding:13px 15px; }
.metric .l { font-size:10.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.9px; }
.metric .v { font-size:21px; font-weight:600; color:var(--navy); margin-top:3px; font-variant-numeric:tabular-nums;}
.metric .v small { font-size:13px; color:var(--muted); font-weight:500; }
.pos{ color:#1B7A4B!important;}

/* ---- section label ---- */
.seclabel { font-size:12px; letter-spacing:2.5px; text-transform:uppercase; color:var(--muted);
  margin:26px 0 4px; font-weight:600;}
.seclabel + .hint { font-size:12.5px; color:var(--muted); margin-bottom:14px;}

/* ---- timeline ---- */
.turn { display:flex; gap:14px; align-items:stretch; }
.rail { position:relative; width:44px; flex:none; }
.rail::before { content:""; position:absolute; left:21px; top:0; bottom:-14px; width:2px; background:var(--line); }
.turn.last .rail::before { bottom:auto; height:22px; }  /* line ends at the last node, not the card */
.node { position:relative; z-index:1; width:44px; height:44px; border-radius:50%; color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:9.5px; font-weight:700; letter-spacing:.3px;
  box-shadow:0 0 0 4px #F4F6F9; }
.card { flex:1; background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px 17px;
  margin-bottom:14px; box-shadow:0 1px 4px rgba(16,42,67,.04); }
.card.gov { border-left:3px solid var(--gold); }
.card.human { border-left:3px solid var(--navy); background:#FAFBFD; }
.chead { display:flex; align-items:center; gap:9px; flex-wrap:wrap; margin-bottom:9px; }
.chead .who { font-weight:600; color:var(--ink); font-size:14.5px; }
.chip { font-size:10.5px; color:var(--muted); background:#F1F4F8; border:1px solid var(--line);
  padding:2px 8px; border-radius:5px; letter-spacing:.2px;}
.chead .to { font-size:12px; color:var(--muted); }
.chead .to b { color:var(--ink); }
.chead .t { margin-left:auto; font-size:11.5px; color:#9AA8BC; font-variant-numeric:tabular-nums; }
.cbody { font-size:13.3px; color:#33425A; line-height:1.55; }
.cbody ul { margin:4px 0 6px; padding-left:18px; } .cbody li { margin-bottom:5px; }
.subh { font-size:10.5px; text-transform:uppercase; letter-spacing:.8px; color:var(--muted); margin:9px 0 3px; font-weight:600;}
.mand { font-size:14px; color:var(--ink); }

/* chips / dots */
.sev { font-size:10px; font-weight:700; letter-spacing:.5px; text-transform:uppercase; padding:2px 7px; border-radius:4px; margin-right:7px; }
.s-high{ background:#FBE9E7; color:#B42318;} .s-med{ background:#FBF1DE; color:#9A6A12;} .s-low{ background:#EEF1F5; color:#51607A;}
.flag { margin:5px 0; padding-left:2px; }
.dots { display:inline-flex; gap:3px; vertical-align:middle; }
.dot { width:9px; height:9px; border-radius:50%; background:#D7DEE8; } .dot.on{ background:var(--navy);}
.kv { color:var(--muted); } .kv b { color:var(--ink); font-weight:600;}

/* memo */
.memo { font-family:'Newsreader',serif; }
.memo h3 { font-size:19px; color:var(--navy); margin:0 0 2px; font-weight:600;}
.memo .num { font-family:'Inter'; font-size:13px; color:#33425A; line-height:1.6; margin:8px 0;}
.memo .num b { color:var(--navy); }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------- small helpers
def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def money_bn(x) -> str:
    if not isinstance(x, (int, float)):
        return "—"
    return f"${x/1000:.2f}T" if abs(x) >= 1000 else f"${x:,.0f}bn"


def pct(x, plus=False) -> str:
    if not isinstance(x, (int, float)):
        return "—"
    return f"{'+' if plus and x > 0 else ''}{x:.1f}%"


def dots(n) -> str:
    try:
        n = int(n)
    except Exception:
        n = 0
    return '<span class="dots">' + "".join(
        f'<span class="dot {"on" if i < n else ""}"></span>' for i in range(5)) + "</span>"


def sev_chip(s) -> str:
    s = str(s).lower()
    cls = "s-high" if "high" in s else "s-med" if ("med" in s or "mod" in s) else "s-low"
    return f'<span class="sev {cls}">{esc(s)}</span>'


def badge(status) -> str:
    s = (status or "").lower()
    cls = {"pass": "b-pass", "qualified": "b-qual", "fail": "b-fail"}.get(s, "b-none")
    return f'<span class="badge {cls}">{esc(status or "—")}</span>'


def bullets(items) -> str:
    items = items if isinstance(items, list) else [items]
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items if x) + "</ul>"


# --------------------------------------------------------- structured reply body
def reply_body(name: str, d: dict) -> str:
    # Auditor
    if "attestation" in d:
        h = f'<div class="subh">Attestation</div>{badge(d.get("attestation"))}'
        if d.get("findings"):
            h += f'<div class="subh">Checks</div>{bullets(d["findings"])}'
        if d.get("one_line"):
            h += f'<div style="margin-top:7px" class="kv">{esc(d["one_line"])}</div>'
        return h
    # Risk Officer
    if "compliance_status" in d:
        h = (f'<span class="kv"><b>Compliance:</b></span> {badge(d.get("compliance_status"))} '
             f'<span class="kv" style="margin-left:14px"><b>Max position:</b> {esc(d.get("max_position_pct_allowed","—"))}%</span>')
        flags = d.get("risk_flags", [])
        if flags:
            h += '<div class="subh">Risk flags</div>'
            for f in flags:
                issue = f.get("issue") or f.get("flag") or f.get("note", "")
                h += f'<div class="flag">{sev_chip(f.get("severity",""))}{esc(issue)}</div>'
        if d.get("required_conditions"):
            h += f'<div class="subh">Conditions</div>{bullets(d["required_conditions"])}'
        return h
    # Chief Risk Officer (tie-break)
    if "independent_call" in d:
        side = d.get("stronger_side", "")
        h = (f'<span class="kv"><b>Independent call:</b></span> '
             f'<span class="sev s-med">{esc(d["independent_call"]).upper()}</span>'
             f'<span class="kv" style="margin-left:14px"><b>Stronger side:</b> {esc(side)}</span>')
        factor = d.get("single_most_decisive_factor") or d.get("why", "")
        if factor:
            h += f'<div class="subh">Decisive factor</div><div class="kv">{esc(factor)}</div>'
        return h
    # Bull / Bear
    if "conviction" in d:
        h = ""
        if d.get("thesis"):
            h += f'<div class="subh">Thesis</div>{bullets(d["thesis"])}'
        if d.get("catalysts"):
            h += f'<div class="subh">Catalysts</div>{bullets(d["catalysts"])}'
        if d.get("red_flags"):
            h += f'<div class="subh">Red flags</div>{bullets(d["red_flags"])}'
        reb = d.get("rebuttal_of_bear") or d.get("rebuttal_of_bull")
        if reb:
            h += f'<div class="subh">Rebuttal</div><div class="kv">{esc(reb)}</div>'
        h += f'<div style="margin-top:9px" class="kv"><b>Conviction</b> &nbsp; {dots(d["conviction"])} &nbsp; {esc(d["conviction"])}/5</div>'
        return h
    # Specialist (export / valuation / forensic)
    if "domain" in d or "severity_after_review" in d or "valuation_risk_level" in d:
        h = ""
        if d.get("domain"):
            h += f'<div class="kv"><b>Domain:</b> {esc(d["domain"])}</div>'
        sev = d.get("severity_after_review") or d.get("valuation_risk_level")
        if sev:
            h += f'<div style="margin-top:6px">{sev_chip(sev)}<span class="kv">severity after review</span></div>'
        if d.get("fair_value_bias"):
            h += f'<div class="kv" style="margin-top:6px"><b>Fair-value bias:</b> {esc(d["fair_value_bias"])}</div>'
        if d.get("assessment"):
            h += f'<div class="subh">Assessment</div><div class="kv">{esc(d["assessment"])}</div>'
        if d.get("mitigations"):
            h += f'<div class="subh">Mitigations</div>{bullets(d["mitigations"])}'
        impact = d.get("position_impact") or (f'ceiling {d["sizing_ceiling_pct"]}%' if d.get("sizing_ceiling_pct") else "")
        if impact:
            h += f'<div style="margin-top:7px" class="kv"><b>Position impact:</b> {esc(impact)}</div>'
        return h
    # Research brief
    if "snapshot" in d:
        devs = d.get("recent_developments", [])
        h = '<div class="subh">Material developments &amp; risks</div><ul>'
        for x in devs:
            head = x.get("headline", "") if isinstance(x, dict) else str(x)
            h += f"<li>{esc(head)}</li>"
        return h + "</ul>"
    # fallback
    return f'<div class="kv">{esc(json.dumps(d, indent=2))}</div>'


def memo_body(content: str) -> str:
    lines = [l for l in content.splitlines() if l.strip()]
    out = ['<div class="memo">']
    for l in lines:
        ls = l.strip()
        if ls.startswith("INVESTMENT MEMO"):
            out.append(f"<h3>{esc(ls)}</h3>")
        elif ls.startswith(("Recommendation", "Committee", "Independent Audit")):
            out.append(f'<div class="num"><b>{esc(ls)}</b></div>')
        else:
            out.append(f'<div class="num">{esc(ls)}</div>')
    return "".join(out) + "</div>"


GOV_ROLES = {"Risk Officer", "Chief Risk Officer", "Independent Auditor"}


def render_turn(t: dict, is_last: bool = False):
    meta = role_meta(t["name"]) if not t["is_user"] else role_meta("__user__")
    color = meta.get("color", "#0B1F3A")
    short = "YOU" if t["is_user"] else meta.get("short", "")
    cls = "card"
    if t["kind"] in ("memo",) or t["name"] in GOV_ROLES:
        cls += " gov"
    if t["is_user"]:
        cls += " human"

    # header bits
    who = "Portfolio Manager" if (t["is_user"] and t["kind"] != "mandate") else t["display_name"]
    chips = ""
    if not t["is_user"] and meta.get("model"):
        chips = f'<span class="chip">{esc(meta["model"])} · {esc(meta["vendor"])}</span>'
    to = ""
    if t["recipients"]:
        to = '<span class="to">→ <b>' + esc(", ".join(t["recipients"])) + "</b></span>"

    # body
    if t["kind"] == "mandate":
        body = f'<div class="mand">📋 <b>Mandate.</b> {esc(t["prose"])}</div>'
        who = "Human — Portfolio (mandate)"
    elif t["kind"] == "approve":
        body = '<div class="mand">✅ <b>Human approval.</b> The committee\'s recommendation is authorised.</div>'
        who = "Human — Portfolio"
    elif t["kind"] == "memo":
        body = memo_body(t["full"])
    elif t["kind"] == "draft":
        body = f'<div class="cbody">{esc(t["prose"]).replace(chr(10), "<br>")}</div>'
    elif t["kind"] == "route":
        body = f'<div class="kv">{esc(t["route_intent"])}.</div>'
    elif t["kind"] == "thought":
        body = f'<div class="kv" style="font-style:italic">⚙︎ {esc(t["prose"])}</div>'
    elif t["data"] is not None:
        body = f'<div class="cbody">{reply_body(t["name"], t["data"])}</div>'
    else:
        body = f'<div class="cbody">{esc(t["prose"])}</div>'

    st.markdown(f"""
<div class="turn{' last' if is_last else ''}"><div class="rail"><div class="node" style="background:{color}">{esc(short)}</div></div>
<div class="{cls}"><div class="chead"><span class="who">{esc(who)}</span>{chips}{to}
<span class="t">{esc(t["time"])}</span></div>{body}</div></div>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- app
def metric(label, value, pos=False):
    return f'<div class="metric"><div class="l">{esc(label)}</div><div class="v {"pos" if pos else ""}">{value}</div></div>'


@st.cache_data
def load(stem: str) -> dict:
    return build_view(json.loads((TRANSCRIPTS / f"{stem}.json").read_text(encoding="utf-8")))


def _sidebar() -> None:
    with st.sidebar:
        st.markdown('<div style="font-family:Newsreader,serif;font-size:24px;font-weight:600;color:#102A43">Quorum<span style="color:#B08D57">.</span></div>'
                    '<div style="font-size:11px;letter-spacing:2px;color:#5A6B82;text-transform:uppercase;margin-bottom:14px">AI Investment Committee</div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="subh" style="margin-top:0">Model fleet</div>', unsafe_allow_html=True)
        fleet = [("Portfolio Manager", "GPT-5.2 · OpenAI"), ("Research", "Qwen2.5-72B · Featherless"),
                 ("Bull", "DeepSeek-V4"), ("Bear", "Grok-4 · xAI"), ("Risk Officer", "o3 · OpenAI"),
                 ("Chief Risk Officer", "Gemini-2.5 · Google"), ("Specialists", "Grok / DeepSeek / Gemini"),
                 ("Independent Auditor", "Gemini-2.5 · Google")]
        st.markdown("".join(f'<div style="font-size:12px;color:#33425A;margin:3px 0"><b>{esc(a)}</b> · <span style="color:#5A6B82">{esc(b)}</span></div>' for a, b in fleet), unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="subh" style="margin-top:0">How it works</div>'
                    '<div style="font-size:12px;color:#33425A;line-height:1.6">A committee that <b>rewrites its own membership</b> from its risk findings, <b>governs</b> the decision with an enforceable gate + human sign-off, and <b>audits</b> itself — coordinated agent-to-agent through <b>Band</b>.</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10.5px;color:#9AA8BC;margin-top:16px;line-height:1.5">Illustrative only — not investment advice.</div>', unsafe_allow_html=True)


def render_case(v: dict):
    m = v["memo"] or {}
    rec = (m.get("recommendation") or "—")
    vcls = {"BUY": "v-buy", "HOLD": "v-hold", "SELL": "v-sell"}.get(rec, "v-hold")
    audit_html = badge(m.get("audit_status")) if m.get("audit_status") else '<span class="badge b-none">—</span>'
    st.markdown(f"""
<div class="hero"><div class="hero-top">
  <div><div class="tkr">{esc(v["ticker"])}</div><div class="co">{esc(v["company"])} · {esc((v["brief"] or {}).get("snapshot",{}).get("sub_industry","—"))}</div>
  <div class="sub2">Committee: {esc(m.get("committee","—"))}</div></div>
  <div class="rec"><span class="verdict {vcls}">{esc(rec)}</span></div>
</div>
<div class="hero-metaline">
  <div class="hm">Position size<b>{esc(m.get("size","—"))}</b></div>
  <div class="hm">Risk ceiling<b>{esc(m.get("risk_max","—"))}</b></div>
  <div class="hm">Independent audit<b style="font-size:13px;margin-top:5px">{audit_html}</b></div>
  <div class="hm">Seats convened<b>{len(v["participated"])}</b></div>
  <div class="hm">Meeting time<b>{esc(v["duration"])}</b></div>
</div></div>
""", unsafe_allow_html=True)

    b = v["brief"] or {}
    snap, kf = b.get("snapshot", {}), b.get("key_financials", {})
    if snap or kf:
        cards = [
            metric("Market cap", money_bn(snap.get("market_cap_usd_bn"))),
            metric("Forward P/E", f'{snap.get("fwd_pe","—")}<small>x</small>'),
            metric("Revenue (TTM)", money_bn(kf.get("revenue_ttm_usd_bn"))),
            metric("Revenue growth", pct(kf.get("revenue_growth_yoy_pct"), plus=True), pos=True),
            metric("Gross margin", pct(kf.get("gross_margin_pct"))),
            metric("Operating margin", pct(kf.get("operating_margin_pct"))),
            metric("Free cash flow", money_bn(kf.get("fcf_ttm_usd_bn"))),
            metric("EV / EBITDA", f'{kf.get("ev_ebitda","—")}<small>x</small>'),
        ]
        st.markdown('<div class="metrics">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    st.markdown('<div class="seclabel">Committee proceedings</div>'
                '<div class="hint">Every handoff is a real agent-to-agent message routed through Band — gather → debate → risk gate → self-assembled specialists → escalation → independent audit → human sign-off.</div>', unsafe_allow_html=True)
    for idx, t in enumerate(v["turns"]):
        render_turn(t, is_last=(idx == len(v["turns"]) - 1))


def main():
    _sidebar()
    st.markdown('<div class="brandbar"><div><div class="mark">Quorum<b>.</b></div>'
                '<div class="sub">AI Investment Committee</div></div>'
                '<div class="fund"><b>Northwind Tech Growth Fund</b><br>Long-only · GARP · 5–10% target<br>Max position 10% · sub-industry 35%</div></div>', unsafe_allow_html=True)
    available = [s for s in ORDER if (TRANSCRIPTS / f"{s}.json").exists()]
    choice = st.radio("Case", available, format_func=lambda s: s.upper(), horizontal=True, label_visibility="collapsed")
    render_case(load(choice))


if __name__ == "__main__":
    main()
