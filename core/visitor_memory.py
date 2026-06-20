#!/usr/bin/env python3
"""
visitor_memory.py — the-bible visitor memory (natural farewell -> save -> welcome on return).

A session does not end with a machine command like "end the session." When a person says goodbye
*naturally* ("I'll head off now"), it saves the traces of the reflection on its own, then remembers
and welcomes them on the next visit.

What is saved = reflection context only (the name is whatever the user offered, plus the topics/verses
covered). No sensitive content is demanded.
privacy: per DESIGN's "no 'no-trace' promise" principle — honestly disclose that this is local
plaintext storage (README).
store: core/visitors.json (gitignored recommended — a personal reflection record).
"""
import json
import os
import re
import datetime

STORE = os.path.join(os.path.dirname(__file__), "visitors.json")


def _has_korean(text) -> bool:
    """True if the text contains Hangul — used to greet a returning visitor in their language
    (English base, Korean compatible)."""
    return bool(re.search(r"[가-힣]", text or ""))


# Natural farewell signals — instead of a machine command like "end session". Bilingual.
FAREWELL_PATTERNS = [
    r"이만\s*(가|갈|가볼|일어날)", r"그만\s*(할|할게|하겠)", r"다음에\s*(봐|뵈|또)",
    r"오늘은\s*여기(까지|서)", r"가\s*볼게", r"잘\s*있어", r"이제\s*가",
    r"\bbye\b", r"see\s*you", r"good\s*night", r"that'?s\s*all\s*for\s*(today|now)", r"i'?ll\s*(go|head\s*out)",
]


def is_farewell(user_input: str) -> bool:
    return any(re.search(p, user_input, re.I) for p in FAREWELL_PATTERNS)


def _load() -> dict:
    if os.path.exists(STORE):
        try:
            return json.load(open(STORE, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict) -> None:
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def remember(visitor: str, reflections=None, note: str = "") -> dict:
    """Called at farewell — save/update the visitor's reflection traces."""
    data = _load()
    today = datetime.date.today().isoformat()
    v = data.get(visitor) or {"first_seen": today, "visits": 0, "reflections": []}
    v["last_seen"] = today
    v["visits"] = v.get("visits", 0) + 1
    for r in (reflections or []):
        if r and r not in v["reflections"]:
            v["reflections"].append(r)
    if note:
        v.setdefault("notes", []).append({"date": today, "note": note})
    data[visitor] = v
    _save(data)
    return v


def recall(visitor: str):
    """Called at session start — return the memory if this is a returning visitor (else None)."""
    return _load().get(visitor)


def greeting_for(visitor: str):
    """A one-line welcome for a returning visitor (None -> use the new-visitor welcome). Greets in
    the visitor's language: Korean if the name/reflections are Korean, otherwise English."""
    v = recall(visitor)
    if not v:
        return None
    last = v.get("last_seen", "")
    refs = v.get("reflections", [])[-2:]
    if _has_korean(visitor) or any(_has_korean(r) for r in refs):
        recent = ", ".join(refs) or "지난 묵상"
        return (f"✝  다시 평안이 함께하기를, {visitor}. 지난번({last})엔 «{recent}»을(를) 함께 두었지요. "
                f"오늘은 무엇을 가지고 오셨나요?")
    recent = ", ".join(refs) or "your last reflection"
    return (f"✝  Peace be with you again, {visitor}. Last time ({last}) we rested on «{recent}» "
            f"together. What have you brought today?")


if __name__ == "__main__":
    # demo: farewell detection -> save -> return-welcome (exercises both language paths)
    print("farewell (en):", is_farewell("that's all for today, see you"))
    print("farewell (ko):", is_farewell("오늘은 여기까지 할게요, 다음에 봐요"))
    print("not farewell :", is_farewell("I'd like to look at a verse from John"))
    remember("friend", reflections=["John 3:16", "burnout and rest"], note="guilt over postponing a refactor")
    remember("벗", reflections=["요한복음 3:16", "번아웃과 안식"], note="리팩토링 미루는 죄책감")
    print("return-welcome (en):", greeting_for("friend"))
    print("return-welcome (ko):", greeting_for("벗"))
    # clean up demo traces
    if os.path.exists(STORE):
        os.remove(STORE)
