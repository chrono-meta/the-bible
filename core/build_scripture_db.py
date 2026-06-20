#!/usr/bin/env python3
"""
build_scripture_db.py — 공개도메인 성서 다버전 수집기 (the-bible CORE).

성서 = 절대 axiom (DESIGN §1). 이 스크립트가 그 axiom의 *전체 코퍼스*를 만든다.
편향 방지를 위해 여러 공개도메인 버전을 수집한다 — grounding은 "어느 검증버전과든
정확매칭되면 grounded"이므로, 다버전 = 더 견고한 fail-closed + 개신교/천주교 포용.

출력: core/scripture/{version}.json  =  { "Book Chapter:Verse": "text", ... }
       (기존 grounding_gate.py의 {ref: text} 평탄 스키마와 동일 — 버전당 1파일)
메타:  core/scripture/_index.json     =  버전 목록 + 구절 수 + 라이선스 + 정경 범위

소스:
- getbible.net v2 (공개도메인 영어): kjv · web · asv · ylt
- Douay-Rheims (천주교, 제2경전 포함, 공개도메인): ebible.org 시도 (실패 시 명명된 잔여)
"""
import json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(__file__)
OUT_DIR = os.path.join(HERE, "scripture")
os.makedirs(OUT_DIR, exist_ok=True)

# (version_id, source_url, label, license, canon)
GETBIBLE = "https://api.getbible.net/v2/{}.json"
VERSIONS = [
    ("kjv", GETBIBLE.format("kjv"), "King James Version (1769)", "Public Domain", "Protestant 66"),
    ("web", GETBIBLE.format("web"), "World English Bible", "Public Domain", "Protestant 66 (modern)"),
    ("asv", GETBIBLE.format("asv"), "American Standard Version (1901)", "Public Domain", "Protestant 66"),
    ("ylt", GETBIBLE.format("ylt"), "Young's Literal Translation (1898)", "Public Domain", "Protestant 66"),
    # 천주교/제2경전 포용 (양쪽 정경 — DESIGN: 한쪽 편향 금지)
    ("douayrheims", GETBIBLE.format("douayrheims"), "Douay-Rheims (1899, American Ed.)", "Public Domain", "Catholic (제2경전 포함)"),
    ("kjva", GETBIBLE.format("kjva"), "KJV with Apocrypha (1769)", "Public Domain", "Protestant + Apocrypha 80"),
]


def fetch(url, retries=3, timebox=30):
    """M2 규율: 즉시 실패 단정 말고 backoff 재시도 소진 후에만 포기."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "the-bible-corpus/1.0"})
            with urllib.request.urlopen(req, timeout=timebox) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            if attempt < retries:
                wait = 1.0 * (2 ** (attempt - 1))
                print(f"  retry {attempt}/{retries} ({wait}s): {e}", file=sys.stderr)
                time.sleep(wait)
    raise last


def normalize_getbible(data):
    """getbible v2 {books:[{name,chapters:[{chapter,verses:[{verse,text}]}]}]} -> {ref: text}"""
    out = {}
    books = data.get("books") or []
    for b in books:
        name = b.get("name", "").strip()
        for ch in b.get("chapters", []):
            cn = ch.get("chapter")
            for v in ch.get("verses", []):
                ref = f"{name} {cn}:{v.get('verse')}"
                text = (v.get("text") or "").strip()
                if text:
                    out[ref] = text
    return out


def main():
    index = {"_meta": "the-bible CORE — verified multi-version scripture corpus (the ABSOLUTE axiom).",
             "versions": []}
    for vid, url, label, lic, canon in VERSIONS:
        print(f"[{vid}] fetching {label} ...")
        try:
            raw = fetch(url)
        except Exception as e:
            print(f"  FAILED (named residual): {e}", file=sys.stderr)
            index["versions"].append({"id": vid, "label": label, "status": "FAILED", "error": str(e)})
            continue
        verses = normalize_getbible(raw)
        path = os.path.join(OUT_DIR, f"{vid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(verses, f, ensure_ascii=False)
        print(f"  -> {path}  ({len(verses)} verses)")
        index["versions"].append({"id": vid, "label": label, "license": lic,
                                  "canon": canon, "verses": len(verses)})
    with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    total = sum(v.get("verses", 0) for v in index["versions"])
    ok = [v["id"] for v in index["versions"] if v.get("verses")]
    print(f"\nDONE: {len(ok)} versions, {total} total verse-records → {OUT_DIR}")


if __name__ == "__main__":
    main()
