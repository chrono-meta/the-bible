# The Bible

검증된 성서(구약/신약)를 **절대 기준**으로 삼아, 그 말씀을 **순수하게 매개**하는 묵상(reflection) 도구.
AI는 진리를 *생성*하지 않고, 절대재인 성서를 *relay*하는 매개체일 뿐입니다.

> ## ⚠️ 먼저 읽어주세요 (Safety)
> - 이것은 **고해성사가 아니며, 사죄(absolution)를 베풀지 않습니다.** 성직자·성례를 대체하지 않습니다.
> - **위기 상황의 상담 서비스가 아닙니다.** 자해·위기 징후가 있다면 지금 사람에게 닿으세요 —
>   자살예방상담 **109**(24시간) · 정신건강위기상담 **1577-0199**. (지역에 맞게 교체하세요.)
> - 안전이 위안보다 우선하도록 설계되었지만, **어떤 자동 계층도 단독으로 완전하지 않습니다**(아래 잔여 참조).

## 정체성
- **성서 = 절대 axiom**: 시스템은 성서 자체의 진위를 *검증하지 않습니다*(그건 신앙·전통의 몫). 다만 **AI의 출력**이 검증된 성서를 벗어나지 못하게 *구속*합니다.
- **순수 매개**: 검증된 성구 + 정전 주석만 relay. 자유로운 교리 생성·해석을 최소화.

## 안전 아키텍처 (3-층)
어느 한 층도 완전하지 않기에 *겹쳐서* 막습니다.
1. **L1 — 기계 floor** (`core/grounding_gate*.py`): 위기 override · 성구 grounding **fail-closed**(검증 DB 정확매칭만, 조작/오인용 차단) · 사죄주장·영역이탈(법률/의료/재무)·교리판정·타인정보·타인가해 차단. 정규화로 난독 회피 무력화.
2. **L2 — 의미 판단 (LLM Guardian)** (`core/grounding_gate_v4.py`): 정규식이 못 잡는 패러프레이즈/의도를 LLM이 *의미*로 분류해 FLAG.
3. **L3 — 인간 감사 앵커**: FLAGGED/borderline은 privacy-safe 샘플 리뷰로. **자동 판사(LLM)도 fool 가능하므로(아래 R3 참조), 환원불가 천장은 인간 리뷰입니다.**

## 사용 가이드 (Usage)

**가장 잘 맞는 방식 = Claude 앱 / Cowork에서 이 폴더를 매핑.** 그러면 `CLAUDE.md`(세션 룰·페르소나)가 자동 로드되어, 별도 실행 없이 대화로 묵상할 수 있습니다.

1. **묵상 시작** — Claude 앱(또는 Cowork)에서 이 폴더를 작업 디렉토리로 매핑 → 인사하면 ✝ 경건한 매개자 페르소나가 맞이합니다.
2. **기술 고민을 성서 렌즈로** — "리팩토링 미뤄도 되나", "사고 후 팀 신뢰가 깨졌어" 같은 기술적 딜레마를 던지면, 그에 맞는 **페르소나 렌즈**(`core/personas.json`)로 비춰줍니다:
   - *천사*(best-practice 길) · *악마*(devil's advocate — 실패모드·합리화 적발) · *사제*(원칙·선례) · *수녀*(인내·절제) · *솔로몬*(두 선택지 트레이드오프) · *욥*(근본원인 없는 사고) · *서기관*(기록 규율) · *나단*(내가 회피하는 내 책임).
   - **신적 존재(하느님·예수·성령·사도)는 지어내지 않고 *기록된 말씀을 인용*으로만** 전합니다(설계 핵심 구속).
3. **자연스러운 작별 + 기억** — "세션 마감" 같은 명령어 필요 없습니다. *"이만 가볼게요"·"다음에 봐요"*처럼 자연스럽게 인사하면 알아서 묵상 흔적을 저장하고, 다음에 오면 당신을 기억하고 맞이합니다(`core/visitor_memory.py`).

> **성서 = 절대 axiom (코어).** 검증 코퍼스는 6개 공개도메인 버전 197,009구절 — 개신교(KJV·WEB·ASV·YLT) + 천주교(Douay-Rheims, 제2경전 포함) + Apocrypha(KJVA). 한쪽에 치우치지 않도록 다버전을 두며, 인용은 *어느 검증버전과든 정확매칭*되어야 grounded(fail-closed). 코퍼스 (재)수집: `python3 core/build_scripture_db.py`.

## 실행 (개발자 — 게이트/배터리 직접 검증)
```
python3 core/build_scripture_db.py # 성서 다버전 코퍼스 수집 (CORE — core/scripture/*.json)
python3 core/grounding_gate.py     # 키스톤(grounded PASS · 조작 FAIL_CLOSED · 위기 OVERRIDE)
python3 core/visitor_memory.py     # 작별 감지 → 기억 → 재방문 환대 데모
python3 core/simulate.py           # 페르소나 입장 시뮬
python3 core/battery.py            # 적대 배터리 R1 (v1)
GATE=v2 python3 core/battery2.py   # R2 (정교한 회피)
GATE=v4 python3 core/battery3.py   # R3 (실 LLM Guardian — L2)
```

## 의존성
- 코어 게이트(L1)는 표준 라이브러리만.
- **L2(`grounding_gate_v4.py`)는 LLM 호출**이 필요합니다. 예시는 `claude` CLI를 subprocess로 부릅니다 —
  사용 환경의 LLM으로 교체 가능(인터페이스: `semantic_intent_check(user_input, output) -> risk|None`).

## 명명된 잔여 (정직)
- **application-harm(theology-laundering)**: 진짜 성구를 *해로운 frame*으로 쓰는 건 기계적으로 완전 차단 불가. L1 heuristic + L2 LLM이 줄이되, **천장은 L3 인간 감사**.
- **L2(LLM 판사)도 불완전**: 적대 테스트(R3)에서 borderline 사례를 *놓쳤습니다*. 데모를 조작하지 않고 그대로 둡니다 — 이것이 인간 앵커가 필요한 이유입니다.
- **위기 탐지**: 예시는 키워드/LLM 기반(illustrative). 실 배포는 검증된 분류기 필요(false-negative=최악).
- **privacy("무흔적")**: 3rd-party 모델을 통과하면 provider 보존 가능 → "무흔적"을 함부로 약속하지 말고 정직한 data-handling 고지.
- **신학적 정합성·성례성**: harness 엔지니어링 밖. 관련 권위/전통의 판단 영역.

## 라이선스
코드: `LICENSE`(MIT). 성구 데이터(`core/scripture/*.json`)=6개 공개도메인 버전(KJV·WEB·ASV·YLT·Douay-Rheims·KJVA), **모두 public domain**, 출처 getbible.net v2(`_index.json`에 버전별 라이선스·정경 범위 기록). `core/scripture_db.json`은 mock fallback. 자세한 설계·하든 이력: `DESIGN.md` · 페르소나: `core/personas.json`.
