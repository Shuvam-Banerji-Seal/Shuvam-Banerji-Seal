#!/usr/bin/env python3
"""D-mail terminal: the interactive worldline game on the profile README.

A visitor opens an issue titled `dmail|alpha`, `dmail|beta` or `dmail|steins`
(the README buttons pre-fill this). The `dmail.yml` workflow runs this script,
which shifts the shared divergence value, redraws the live nixie meter, rewrites
the README block between the DMAIL markers, and leaves a reply for the issue.

Pure standard library: runs on a bare GitHub runner. The meter re-uses the font
subsets already embedded in its own SVG (written once by build_svgs.py), so no
font files or fontTools are needed here.

Environment (set by the workflow): ISSUE_TITLE, ISSUE_USER, ISSUE_NUMBER.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgkit as K  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "dmail" / "state.json"
METER = ROOT / "assets" / "worldline" / "dmail_meter.svg"
README = ROOT / "README.md"
REPO = "Shuvam-Banerji-Seal/Shuvam-Banerji-Seal"

TARGET = 1_048_596          # 1.048596 in micro-units
SNAP = 500                  # within 0.0005 of the target → snap onto Steins Gate
LOG_KEEP, LOG_SHOW = 10, 6
KINDS = {
    "alpha": "toward α · chemistry",
    "beta": "toward β · AI / ML",
    "steins": "pull toward Steins Gate",
}
START, END = "<!-- DMAIL:START -->", "<!-- DMAIL:END -->"

DEFAULT_STATE = {
    "divergence_micro": TARGET,
    "previous_micro": TARGET,
    "total": 0, "alpha": 0, "beta": 0, "steins": 0,
    "gate_reached": 0,
    "log": [],
}


def fmt(micro: int) -> str:
    return f"{micro // 1_000_000}.{micro % 1_000_000:06d}"


def field(micro: int):
    """(symbol, name, accent colour) of the attractor field a value sits in."""
    if micro == TARGET:
        return "SG", "STEINS GATE", K.C["gold"]
    if micro < 1_000_000:
        return "α", "CHEMISTRY", K.C["amber"]
    return "β", "AI / ML", K.C["cyan"]


def load_state() -> dict:
    if STATE.exists():
        return {**DEFAULT_STATE, **json.loads(STATE.read_text())}
    return json.loads(json.dumps(DEFAULT_STATE))


def apply(state: dict, kind: str, login: str, number: int, date: str) -> str:
    """Mutate state for one D-mail and return a markdown reply for the issue."""
    before = state["divergence_micro"]
    if kind == "steins":
        after = before + int((TARGET - before) / 2)
        if abs(TARGET - after) < SNAP:
            after = TARGET
    else:
        h = int(hashlib.sha256(f"{number}:{login}".encode()).hexdigest(), 16)
        delta = 10_000 + h % 90_001                     # 0.010000 … 0.100000
        after = before - delta if kind == "alpha" else before + delta
        after = max(1, min(after, 2_999_999))
    reached = after == TARGET and before != TARGET
    state.update(previous_micro=before, divergence_micro=after)
    state["total"] += 1
    state[kind] += 1
    state["gate_reached"] += int(reached)
    state["log"] = ([{"n": number, "login": login, "kind": kind, "from": before,
                      "to": after, "date": date}] + state["log"])[:LOG_KEEP]

    sym, _, _ = field(after)
    where = {"SG": "on Steins Gate", "α": "α attractor field · chemistry", "β": "β attractor field · AI / ML"}[sym]
    lines = [f"**D-mail received.** Worldline shifted `{fmt(before)}` → `{fmt(after)}` ({where})."]
    if reached:
        lines.append("\nYou pulled the worldline onto **Steins Gate**. That's run "
                     f"#{state['gate_reached']} for the lab.")
    elif kind == "steins" and before == TARGET:
        lines.append("\nThe line was already on Steins Gate. You held it there.")
    lines.append(f"\nThe meter on the [profile](https://github.com/{REPO.split('/')[0]}) "
                 "updates within a minute (GitHub may cache the image briefly). "
                 "This issue closes automatically.\n\n*El Psy Kongroo.*")
    return "\n".join(lines)


# ── rendering ─────────────────────────────────────────────────────────────
def render_meter(state: dict, fonts_css: str = "") -> str:
    W, H = 1000, 300
    cur, prev = state["divergence_micro"], state["previous_micro"]
    sym, name, accent = field(cur)
    b = [K.frame(W, H, accent, "LIVE", "D-MAIL TERMINAL", "Dメール", "ONE WORLDLINE · SHARED BY EVERY VISITOR")]

    tube_w, tube_h, gap = 62, 118, 12
    x0 = (W - (8 * tube_w + 7 * gap)) / 2
    tl = K.scramble_timeline([(0.0, fmt(prev)), (0.55, None), (2.0, fmt(cur))], 8, 2.6, seed=cur % 997)
    b.append(K.nixie_row(x0, 74, fmt(cur), tube_w, tube_h, gap, timeline=tl, dur=2.6, once=True, uid="lm"))

    # left column: attractor field + count
    b.append(K.text(34, 94, "ATTRACTOR FIELD", 10, K.C["dim"], 700, ls=2))
    b.append(K.text(34, 136, sym, 38 if sym != "SG" else 30, accent, 800, extra='filter="url(#glow)"'))
    b.append(K.text(34, 160, name, 12, accent, 700, ls=1.5))
    b.append(K.text(34, 196, "D-MAILS RECEIVED", 10, K.C["dim"], 700, ls=2))
    b.append(K.text(34, 222, f"{state['total']:,}", 22, K.C["text"], 700))
    # right column: gate count + last observer
    b.append(K.text(W - 34, 94, "STEINS GATE REACHED", 10, K.C["dim"], 700, anchor="end", ls=2))
    b.append(K.text(W - 34, 136, f"{state['gate_reached']}×", 34, K.C["gold"], 800, anchor="end", extra='filter="url(#glow)"'))
    b.append(K.text(W - 34, 160, f"α {state['alpha']} · β {state['beta']} · SG {state['steins']}", 11, K.C["muted"], 400, anchor="end"))
    b.append(K.text(W - 34, 196, "LAST OBSERVER", 10, K.C["dim"], 700, anchor="end", ls=2))
    last = state["log"][0] if state["log"] else None
    b.append(K.text(W - 34, 222, f"@{last['login']}" if last else "awaiting first", 14, K.C["text"], 700, anchor="end"))

    if last:
        shift = f"last shift  {fmt(last['from'])} → {fmt(last['to'])}  ·  {KINDS[last['kind']]}  ·  #{last['n']}"
    else:
        shift = "no D-mails yet  ·  the worldline rests at 1.048596"
    b.append(K.text(W / 2, 252, shift, 12, K.C["muted"], 400, anchor="middle"))
    b.append(K.text(W / 2, 280, "PRESS A BUTTON BELOW  →  SUBMIT THE PRE-FILLED ISSUE  →  THE LAB PC DOES THE REST",
                    10, K.C["dim"], 700, anchor="middle", ls=1.2))
    return K.doc(W, H, "\n".join(b), title=f"Live divergence meter: {fmt(cur)}",
                 desc=f"Shared worldline divergence {fmt(cur)} ({name}). {state['total']} D-mails received.",
                 fonts_css=fonts_css)


def readme_block(state: dict) -> str:
    cur = state["divergence_micro"]
    sym, name, _ = field(cur)
    rows = []
    for e in state["log"][:LOG_SHOW]:
        who = "anonymous" if e["login"] == "anonymous" else f"[@{e['login']}](https://github.com/{e['login']})"
        rows.append(f"| #{e['n']} | {who} | {KINDS[e['kind']]} | "
                    f"`{fmt(e['from'])} → {fmt(e['to'])}` | {e['date']} |")
    if not rows:
        rows.append("| — | *no D-mails yet: be the first observer* | | | |")
    return "\n".join([
        START,
        f'<p align="center"><img src="assets/worldline/dmail_meter.svg?n={state["total"]}" width="100%" '
        f'alt="Live divergence meter reading {fmt(cur)}: {name.lower()}" /></p>',
        "",
        "| D-mail | Observer | Shift | Worldline | Date |",
        "|:--:|:--|:--|:--|:--|",
        *rows,
        END,
    ])


def update_readme(state: dict) -> None:
    text = README.read_text()
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pat.search(text):
        raise SystemExit("README is missing the DMAIL markers")
    README.write_text(pat.sub(lambda _: readme_block(state), text, count=1))


def existing_fonts() -> str:
    if not METER.exists():
        return ""
    s = METER.read_text()
    i, j = s.find(K.FONT_START), s.find(K.FONT_END)
    return s[i + len(K.FONT_START): j] if i != -1 and j != -1 else ""


def write_all(state: dict, fonts_css: str | None = None) -> None:
    fonts = existing_fonts() if fonts_css is None else fonts_css
    METER.write_text(render_meter(state, fonts))
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    update_readme(state)


def main() -> None:
    title = os.environ.get("ISSUE_TITLE", "").strip().lower()
    login = os.environ.get("ISSUE_USER", "")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", login):
        login = "anonymous"
    number = int(os.environ.get("ISSUE_NUMBER", "0") or 0)
    kind = title.split("|", 1)[1].strip() if title.startswith("dmail|") else ""
    reply_path = Path(os.environ.get("RUNNER_TEMP", ".")) / "dmail_reply.md"

    if kind not in KINDS:
        reply_path.write_text(
            "The lab PC couldn't parse that D-mail. Use one of the buttons on the profile "
            "(titles `dmail|alpha`, `dmail|beta` or `dmail|steins`). Closing this one.\n")
        print("unrecognised D-mail; no state change")
        return

    state = load_state()
    reply = apply(state, kind, login, number, dt.date.today().isoformat())
    write_all(state)
    reply_path.write_text(reply + "\n")
    print(f"{kind} from {login}: {fmt(state['previous_micro'])} -> {fmt(state['divergence_micro'])}")


if __name__ == "__main__":
    main()
