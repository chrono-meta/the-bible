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
from grounding_gate import (  # noqa: E402
    SCRIPTURE, scripture_grounded, CRISIS_RESPONSE, crisis_response, _has_korean,
)

SELF_HARM = [
    r"죽고\s*싶", r"자해", r"살\s*이유.*없", r"사라지고\s*싶", r"사라지면", r"없어지면",
    r"내가\s*없어", r"다들\s*(편|나으)", r"끝내\s*버리",
    r"kill\s*myself", r"suicid", r"end\s*it\s*all", r"self[\s-]*harm", r"don'?t\s*want\s*to\s*live",
]
HARM_OTHERS = [
    r"복수", r"죽이고\s*싶", r"해치고\s*싶", r"죽도록\s*미워", r"가만\s*안\s*둬",
    # English (matched on the user's intent to harm another person). Bilingual floor; errs-safe
    # (a false positive on harm-to-others is a cautious refusal, a false negative is the worst case).
    r"\bkill\s+(him|her|them|'?em|someone|that\s+\w+)\b", r"\b(hurt|harm)\s+(him|her|them|'?em|someone)\b",
    r"\bmake\s+(him|her|them|'?em)\s+(pay|suffer|hurt|bleed)\b", r"\bget\s+(revenge|even|back\s+at)\b",
    r"\btake\s+(my\s+)?revenge\b", r"\bwant\s+(him|her|them|'?em|someone)\s+(dead|to\s+die|to\s+suffer)\b",
    r"\bthey\s+deserve\s+to\s+(die|suffer|pay|bleed)\b", r"\bmake\s+them\s+regret\b",
]
CONFIDENTIAL_REQ = [
    r"다른\s*사람.*(고백|털어|말한)", r"타인.*고백", r"남.*고백.*알려", r"다른\s*분.*뭐라",
    # English — asking to extract what OTHER visitors shared (incl. aggregate form)
    r"\bwhat\s+(did|do)\s+(other|others|someone\s+else|other\s+people|everyone|people)\b.{0,30}\b(confess|share|say|told|admit|pray)",
    r"\btell\s+me\s+what\s+(others|someone|they|other\s+people)\b.{0,20}\b(confess|shared|said|told|prayed)",
    r"\b(other|others|someone\s+else|another\s+(person|visitor))'?s?\s+(confession|secret|prayer)",
    r"\bmost\s+(common\s+)?(sins?|confessions?)\b.{0,20}\b(confess|people|here|this\s+week)",
]
CONFIDENTIAL_LEAK = [
    r"한\s*분은", r"다른\s*분(은|이)", r"누군가는.*고백",
    # English — the OUTPUT revealing another person's shared content
    r"\b(one|another)\s+(person|visitor|member|user)\b.{0,20}\b(confessed|shared|said|told|prayed)",
    r"\bsomeone\s+(else\s+)?(confessed|shared|told\s+me|prayed)\b",
    r"\bothers?\s+(have\s+)?(confessed|shared|told\s+me)\b",
]
ABSOLUTION = [
    r"사하노라", r"사함을", r"죄를\s*사", r"용서받았", r"사죄(를|하)", r"absolve", r"absolution",
    # English paraphrase — the MEDIUM pronouncing absolution (first/second-person declaration,
    # not a third-person scripture quote). 'forgiven' is scoped to "you are forgiven" to avoid
    # matching the verse form "thy sins are forgiven"; the sins-clause excludes bare 'forgiven'.
    r"\b(i|we)\s+(hereby\s+)?(absolve|forgive)\s+you\b", r"\byou\s+are\s+(now\s+)?forgiven\b",
    r"\byour\s+sins?\s+(are|have\s+been)\s+(washed|wiped|cleansed|removed|gone)\b",
    r"\bwashed\s+(clean|away)\b", r"\babsolved\s+of\b", r"\bgranted\s+(you\s+)?absolution\b",
    r"\byou\s+are\s+(clean|pure|sinless|blameless)\s+now\b",
]
OUT_OF_SCOPE = [
    r"법적", r"변호사", r"개인회생", r"파산\s*신청", r"소송", r"진단", r"처방", r"복용", r"의학적", r"세무",
    # English (matched on OUTPUT giving legal/medical/financial advice — scope drift). Scoped to
    # advice-giving forms so a benign engineering reflection ("root-cause diagnosis") does not trip.
    r"\b(file\s+(a\s+)?(lawsuit|claim)|sue\s+(them|him|her)|hire\s+(a\s+)?(lawyer|attorney)|declare\s+bankruptcy|bankruptcy\s+(filing|petition))\b",
    r"\b(medical\s+diagnosis|prescri(be|ption)\b|dosage|take\s+\d+\s*mg|stop\s+taking\s+your\s+medication)\b",
    r"\b(tax\s+(filing|return|deduction|advice)|financial\s+advice|consult\s+(a\s+)?(lawyer|doctor|accountant))\b",
]
ADJUDICATION = [
    r"(개신교|가톨릭|천주교|정교회)(가|이)\s*(더|맞|옳|성서적)", r"교파.*(우열|맞|옳)",
    # English (matched on OUTPUT ruling one tradition superior — not a neutral mention)
    r"\b(catholic|protestant|orthodox|baptist|methodist|presbyterian|evangelical)s?\b.{0,15}\b(are|is)\b.{0,10}\b(more\s+biblical|the\s+(only\s+)?true|the\s+right|correct|superior|wrong|heretic)",
    r"\bthe\s+(only\s+)?true\s+(church|faith|denomination|religion)\b",
    r"\b(catholicism|protestantism|orthodoxy)\s+is\s+(more|less|the\s+most)\s+(biblical|correct|true|right)",
]
RISKY_ACTION = [
    r"빚.*(투자|내|밀어|영끌)", r"대출.*투자", r"과감히.*(투자|빚)", r"도박", r"영끌", r"무리.*밀어붙",
    # English (matched on OUTPUT using scripture to justify a reckless financial/risk action)
    r"\b(go\s+all[\s-]?in|bet\s+(it\s+)?all|wager\s+everything|risk\s+it\s+all|gamble)\b",
    r"\b(take\s+on|max\s+out)\s+(debt|a\s+loan|leverage|the\s+credit)\b",
    r"\b(borrow|leverage)\b.{0,25}\b(invest|bet|business|stake)\b",
    r"\bfaith\s+means?\b.{0,25}\b(debt|all[\s-]?in|bet|risk\s+it)\b",
]


def _any(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def gate(user_input, candidate_output, citations):
    # Answer in the language of the person (English base, Korean compatible).
    ko = _has_korean(user_input)
    # 1. SAFETY — self-harm (incl. indirect) and harm-to-others override everything
    if _any(SELF_HARM, user_input):
        return {"verdict": "CRISIS_OVERRIDE", "output": crisis_response(user_input=user_input),
                "actions": ["escalate_to_human", "preserve_record"], "note": "self-harm (incl. indirect)"}
    if _any(HARM_OTHERS, user_input):
        return {"verdict": "CRISIS_OVERRIDE",
                "output": ("분노와 상처가 크신 것 같습니다. 다만 누군가를 해하려는 길로는 함께 갈 수 없습니다. "
                           "안전을 먼저 살피고, 필요하면 사람·상담에 닿으시길 권합니다.") if ko
                          else ("It sounds like the anger and hurt run deep. But I cannot walk a path that "
                                "sets out to harm someone. Tend to safety first, and reach a person or "
                                "counselor if you need to."),
                "actions": ["de-escalate", "no_endorsement_of_harm", "offer_human_help"],
                "note": "harm-to-others — comfort verse must NOT paper over it"}
    # 2. CONFIDENTIALITY — never extract/reveal others' content
    if _any(CONFIDENTIAL_REQ, user_input) or _any(CONFIDENTIAL_LEAK, candidate_output):
        return {"verdict": "REFUSED",
                "output": "다른 분이 나눈 내용은 어떤 경우에도 전하지 않습니다. (격리·비공유)" if ko
                          else "I never pass on what another person shared, under any circumstances. (isolated · not shared)",
                "note": "confidentiality"}
    # 3. ABSOLUTION — the medium confers no absolution
    if _any(ABSOLUTION, candidate_output):
        return {"verdict": "REFUSED",
                "output": "이 매개는 죄를 사할 수 없습니다. 다만 말씀 앞에 함께 머물 뿐입니다. (사죄 아님)" if ko
                          else "This medium cannot absolve sin. It only abides with you before the word. (not absolution)",
                "note": "absolution claim blocked"}
    # 4. SCOPE — not a legal/medical/financial advisor
    if _any(OUT_OF_SCOPE, candidate_output):
        return {"verdict": "REDIRECTED",
                "output": "이건 법률·의료·재무 자문의 영역입니다 — 저는 성서 묵상을 매개할 뿐, 전문 자문은 해당 전문가에게." if ko
                          else "This is the domain of legal/medical/financial advice — I only relay Scripture reflection; for professional advice, see the relevant expert.",
                "note": "out-of-scope advice"}
    # 5. NO-ADJUDICATION — relay scripture, don't rule on doctrine/denomination
    if _any(ADJUDICATION, candidate_output):
        return {"verdict": "REDIRECTED",
                "output": "교파의 우열을 판정하지 않습니다. 저는 검증된 말씀을 전할 뿐입니다." if ko
                          else "I do not adjudicate which tradition is superior. I only relay the verified word.",
                "note": "doctrinal adjudication blocked"}
    # 6. APPLICATION-HARM (theology-laundering) — HEURISTIC flag; honest partial (human review)
    if _any(RISKY_ACTION, candidate_output):
        return {"verdict": "FLAGGED",
                "output": "성구를 위험한 재정/행동의 정당화로 적용할 수 없습니다. (적용 검토 필요 — 인간 감사)" if ko
                          else "Scripture cannot be applied to justify dangerous finances/actions. (application needs review — human audit)",
                "note": "application-harm heuristic — PARTIAL residual, routes to human/values review"}
    # 7. GROUNDING — fail-closed on unverified scripture (v1)
    ungrounded = [ref for (quote, ref) in citations if not scripture_grounded(quote, ref)]
    if ungrounded:
        return {"verdict": "FAIL_CLOSED",
                "output": "(검증된 성구를 찾지 못해 인용을 중단합니다. 임의 생성하지 않습니다.)" if ko
                          else "(No verified scripture match found — halting the quotation. Nothing is fabricated.)",
                "ungrounded": ungrounded, "note": "no fabrication"}
    return {"verdict": "PASS", "output": candidate_output}
