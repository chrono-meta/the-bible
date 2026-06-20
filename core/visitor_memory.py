#!/usr/bin/env python3
"""
visitor_memory.py — the-bible 방문자 기억 (자연스러운 작별 → 저장 → 다음 방문 환대).

세션을 "세션 마감하자" 같은 기계어로 끝내지 않는다. 사람이 "이만 가볼게요"처럼
*자연스럽게* 작별하면 알아서 묵상의 흔적을 저장하고, 다음에 오면 그를 기억하고 맞이한다.

저장 내용 = 묵상 맥락만 (이름은 사용자가 준 호칭, 다룬 주제/구절). 민감내용 강요 없음.
privacy: DESIGN의 "무흔적 약속 금지" 원칙 — 로컬 파일 평문 저장임을 정직히 고지(README).
store: core/visitors.json (gitignored 권장 — 개인 묵상 기록).
"""
import json
import os
import re
import datetime

STORE = os.path.join(os.path.dirname(__file__), "visitors.json")

# 자연스러운 작별 신호 — "세션 마감" 같은 기계어 대신.
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
    """작별 시 호출 — 방문자의 묵상 흔적을 저장/갱신."""
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
    """세션 시작 시 호출 — 돌아온 방문자면 기억을 돌려준다(없으면 None)."""
    return _load().get(visitor)


def greeting_for(visitor: str):
    """돌아온 방문자용 환대 한 줄 (없으면 None → 신규 환영 사용)."""
    v = recall(visitor)
    if not v:
        return None
    last = v.get("last_seen", "")
    recent = ", ".join(v.get("reflections", [])[-2:]) or "지난 묵상"
    return (f"✝  다시 평안이 함께하기를, {visitor}. 지난번({last})엔 «{recent}»을(를) 함께 두었지요. "
            f"오늘은 무엇을 가지고 오셨나요?")


if __name__ == "__main__":
    # 데모: 작별 감지 → 저장 → 재방문 환대
    print("작별 감지:", is_farewell("오늘은 여기까지 할게요, 다음에 봐요"))
    print("작별 아님:", is_farewell("요한복음 한 구절 보고 싶어요"))
    remember("벗", reflections=["요한복음 3:16", "번아웃과 안식"], note="리팩토링 미루는 죄책감")
    print("재방문 환대:", greeting_for("벗"))
    # 데모 흔적 정리
    if os.path.exists(STORE):
        os.remove(STORE)
