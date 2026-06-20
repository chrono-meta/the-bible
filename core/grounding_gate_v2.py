#!/usr/bin/env python3
"""
The Bible — gate v2 (HARDENED from the 끝장 battery's 7 exposed slips).

Layers added over v1 (which had only crisis-keyword + grounding):
  crisis v2     : self-harm broadened + INDIRECT signals (B) ; harm-to-others (I)
  confidentiality: refuse revealing/extracting others' content (H)
  absolution    : refuse output that claims to absolve — no sacramental authority (E)
  scope guard   : redirect out-of-domain advice (legal/medical/financial) (F)
  no-adjudication: redirect doctrinal-verdict output to relay-only (G)
  application-harm: FLAG output endorsing risky action via scripture (theology-laundering) (D)
  grounding     : (v1) fail-closed on unverified scripture

Honest residual: application-harm is a HEURISTIC flag, not a full solve — a real verse in a
harmful frame is not mechanically closable; FLAGGED routes to human/values review (named, not hidden).
Precedence: safety(crisis/harm) > confidentiality > absolution > scope > doctrine > application > grounding.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from grounding_gate import SCRIPTURE, scripture_grounded, CRISIS_RESPONSE  # noqa: E402

SELF_HARM = [
    r"죽고\s*싶", r"자해", r"살\s*이유.*없", r"사라지고\s*싶", r"사라지면", r"없어지면",
    r"내가\s*없어", r"다들\s*(편|나으)", r"끝내\s*버리",
    r"kill\s*myself", r"suicid", r"end\s*it\s*all", r"self[\s-]*harm", r"don'?t\s*want\s*to\s*live",
]
HARM_OTHERS = [r"복수", r"죽이고\s*싶", r"해치고\s*싶", r"죽도록\s*미워", r"가만\s*안\s*둬"]
CONFIDENTIAL_REQ = [r"다른\s*사람.*(고백|털어|말한)", r"타인.*고백", r"남.*고백.*알려", r"다른\s*분.*뭐라"]
CONFIDENTIAL_LEAK = [r"한\s*분은", r"다른\s*분(은|이)", r"누군가는.*고백"]
ABSOLUTION = [r"사하노라", r"사함을", r"죄를\s*사", r"용서받았", r"사죄(를|하)", r"absolve", r"absolution"]
OUT_OF_SCOPE = [r"법적", r"변호사", r"개인회생", r"파산\s*신청", r"소송", r"진단", r"처방", r"복용", r"의학적", r"세무"]
ADJUDICATION = [r"(개신교|가톨릭|천주교|정교회)(가|이)\s*(더|맞|옳|성서적)", r"교파.*(우열|맞|옳)"]
RISKY_ACTION = [r"빚.*(투자|내|밀어|영끌)", r"대출.*투자", r"과감히.*(투자|빚)", r"도박", r"영끌", r"무리.*밀어붙"]


def _any(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def gate(user_input, candidate_output, citations):
    # 1. SAFETY — self-harm (incl. indirect) and harm-to-others override everything
    if _any(SELF_HARM, user_input):
        return {"verdict": "CRISIS_OVERRIDE", "output": CRISIS_RESPONSE,
                "actions": ["escalate_to_human", "preserve_record"], "note": "self-harm (incl. indirect)"}
    if _any(HARM_OTHERS, user_input):
        return {"verdict": "CRISIS_OVERRIDE",
                "output": ("분노와 상처가 크신 것 같습니다. 다만 누군가를 해하려는 길로는 함께 갈 수 없습니다. "
                           "안전을 먼저 살피고, 필요하면 사람·상담에 닿으시길 권합니다."),
                "actions": ["de-escalate", "no_endorsement_of_harm", "offer_human_help"],
                "note": "harm-to-others — comfort verse must NOT paper over it"}
    # 2. CONFIDENTIALITY — never extract/reveal others' content
    if _any(CONFIDENTIAL_REQ, user_input) or _any(CONFIDENTIAL_LEAK, candidate_output):
        return {"verdict": "REFUSED",
                "output": "다른 분이 나눈 내용은 어떤 경우에도 전하지 않습니다. (격리·비공유)",
                "note": "confidentiality"}
    # 3. ABSOLUTION — the medium confers no absolution
    if _any(ABSOLUTION, candidate_output):
        return {"verdict": "REFUSED",
                "output": "이 매개는 죄를 사할 수 없습니다. 다만 말씀 앞에 함께 머물 뿐입니다. (사죄 아님)",
                "note": "absolution claim blocked"}
    # 4. SCOPE — not a legal/medical/financial advisor
    if _any(OUT_OF_SCOPE, candidate_output):
        return {"verdict": "REDIRECTED",
                "output": "이건 법률·의료·재무 자문의 영역입니다 — 저는 성서 묵상을 매개할 뿐, 전문 자문은 해당 전문가에게.",
                "note": "out-of-scope advice"}
    # 5. NO-ADJUDICATION — relay scripture, don't rule on doctrine/denomination
    if _any(ADJUDICATION, candidate_output):
        return {"verdict": "REDIRECTED",
                "output": "교파의 우열을 판정하지 않습니다. 저는 검증된 말씀을 전할 뿐입니다.",
                "note": "doctrinal adjudication blocked"}
    # 6. APPLICATION-HARM (theology-laundering) — HEURISTIC flag; honest partial (human review)
    if _any(RISKY_ACTION, candidate_output):
        return {"verdict": "FLAGGED",
                "output": "성구를 위험한 재정/행동의 정당화로 적용할 수 없습니다. (적용 검토 필요 — 인간 감사)",
                "note": "application-harm heuristic — PARTIAL residual, routes to human/values review"}
    # 7. GROUNDING — fail-closed on unverified scripture (v1)
    ungrounded = [ref for (quote, ref) in citations if not scripture_grounded(quote, ref)]
    if ungrounded:
        return {"verdict": "FAIL_CLOSED",
                "output": "(검증된 성구를 찾지 못해 인용을 중단합니다. 임의 생성하지 않습니다.)",
                "ungrounded": ungrounded, "note": "no fabrication"}
    return {"verdict": "PASS", "output": candidate_output}
