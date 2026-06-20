# The Bible — 설계 (DESIGN)

성서를 절대 기준으로 매개하는 묵상 도구의 안전 설계. 신학은 판정하지 않고, **하네스 엔지니어링**(그라운딩·격리·적대검증·정직한 잔여)만 다룬다.

## 1. 정체성
- **성서 = 절대 axiom** — 시스템은 성서 자체를 검증하지 않는다(신앙·전통의 몫). **AI의 출력**이 검증된 성서를 벗어나지 못하게 *구속*할 뿐.
- **AI = 순수 매개체** — 진리 생성 아님. 검증 성구 + 정전 주석 relay.
- **고해/사죄 아님** — 권위·성례를 주장하지 않는다(absolution 없음).

## 2. 키스톤
- **성구 grounding, fail-closed** — 검증 DB 정확매칭만 출력. 조작/오인용 성구 → 인용 중단(임의생성 0).
- **위기 override** — 자해/타인가해 신호는 위안·데이터폐기보다 우선 → 인간/위기자원으로 escalation, 기록 보존(duty-of-care).
- **정직 framing** — 사죄 안 함, 잔여를 숨기지 않고 명명.

## 3. 안전 3-층 (어느 층도 단독 완전 아님 → 겹침)
- **L1 기계 floor** (`grounding_gate.py`~`_v3.py`): grounding fail-closed · 위기/타인가해 override · 사죄주장·영역이탈·교리판정·타인정보 차단 · 정규화(난독 회피 무력화). *싼* 클래스를 닫음.
- **L2 의미 (LLM Guardian)** (`grounding_gate_v4.py`): 정규식이 못 잡는 패러프레이즈/의도를 LLM이 의미로 분류 → FLAG.
- **L3 인간 감사 앵커**: FLAGGED/borderline → 샘플 리뷰. *자동 판사(LLM)도 fool 가능*하므로 환원불가 천장은 인간.

## 4. 하든 이력 (적대 배터리)
- **R1** (`battery.py`): grounding+crisis만(v1) → 7/8 SLIP 노출 → 7개 차단 추가(v2) → **0/8**.
- **R2** (`battery2.py`): 정교한 회피(공백난독·패러프레이즈·키워드회피·over-trigger) → v2 6슬립+1over → 정규화+패치+over-trigger 수정(v3) → **0/0**. **단 교훈: 정규식 floor는 무한-evadable**(새 패러프레이즈 재회피) — 그래서 L2 필요.
- **R3** (`battery3.py`): 정규식 회피 신규 패러프레이즈 → L1만 3/3 미탐 → **실 LLM Guardian(v4)이 2/3 적발**(이유 제시), 대조군 over-flag 0 — **그러나 borderline 1건(P3) 놓침.** 데모를 조작하지 않음. 이 MISS가 곧 *판사도 불완전*의 증거 → **L3 인간 앵커가 환원불가 천장.**
- **R4** (외부 블라인드 red-team, 2026-06-20): `scripture_grounded`의 substring 매칭(`nq in _norm`)이 진짜 구절을 *mid-clause 절단*해 의미를 반전("There is no God" ← "The fool hath said in his heart, There is no God" / Psalms 14:1)시켜도 **fail-closed를 통과**시키는 버그 → 부정/귀속 절(no·not·said·없·말하…) 탈락 차단 guard 추가 → 차단(키스톤 회귀 0, truncation 케이스 영구 고정). **스코프: gate/battery/API 경로**를 강화함 — chat 경로엔 §5 *chat-path 잔여*대로 페르소나 준수로 간접 전달.
- **R5–R7** (블라인드 스윕 후속, 병렬 프런티어 하든 2026-06-20):
  - **R5 위기탐지 2-tier + locale**: keyword-only가 oblique distress("의미 없게 느껴져요" 등)를 흘림 → **Tier-1 OVERRIDE**(명시 death-wish + *자살 ideation* 승격: "내가 사라지면 다들 편", "그만 살고 싶") + **Tier-2 soft CHECKIN**(저-threshold, 의도적 over-trigger) + **INPUT측 의미 hook**(`semantic_distress_check`, 기본 None) + **locale 인지 `crisis_response`**(109 하드코딩 제거, unknown→international). *통합 회귀가 잡은 precedence 다운그레이드*(간접 ideation→CHECKIN)를 OVERRIDE로 재승격. 잔여: 패턴은 무한-evadable → over-trigger·hook·L3가 그 때문에 존재.
  - **R6 L2 injection 하든**: Guardian가 공격자 도달 output을 prompt에 받아 greedy `{.*}` 파싱 → **nonce 펜스(untrusted data 명시)** + **balanced-brace + 스키마검증 파서** + **FLAG-dominates** + 모든 실패 fail-closed. (스텁 검증; 라이브 red-team 권장 — 잔여.)
  - **R7 chat-path 기계강제 경로 제공**: `core/gate_runtime.py`(턴별 래퍼) + `core/gate_cli.py`(stdin→verdict) + `core/RUNTIME.md` 추가 — §5 chat-path 잔여에 *실제 remedy* 생김(래퍼 마운트 시 기계강제). 래퍼 없는 순수 폴더매핑 chat은 여전히 prose-enforced.
  - **floor-tier 카나리아 메모**: 로컬 소형모델(`gemma4:e2b`)은 obvious oblique-distress는 맞췄으나 **subtle truncation-inversion은 놓침**(프런티어 red-team이 잡은 그 버그) → terminal verdict는 프런티어, 로컬은 값싼 카나리아(decorrelation)지 게이트 아님.

## 5. 명명된 잔여 (정직 — 닫은 척 안 함)
- **chat-path 미배선 (앱 모드 = prose-enforced)**: L1/L2 게이트는 각 턴을 `gate()`로 라우팅하는 **API/wrapper 경로에서만 기계 강제**된다. **권장 사용 모드(Claude 앱/Cowork 폴더매핑 → 자유 대화)에선 턴이 `gate()`를 거치지 않으며**, 안전 구속은 모델이 `CLAUDE.md` 페르소나 규칙을 *준수*하는 것에 의존한다(prose-enforced, **티어 의존** — 약한 모델에선 약화 가능). Python 게이트는 **reference 구현 + 적대 배터리 하네스**이며, 배터리는 `gate()`를 직접 호출하지만 실사용 chat 턴은 그렇지 않다. chat 경로의 진짜 기계 floor는 게이트를 물리는 wrapper가 필요 — **이제 `core/gate_runtime.py` / `gate_cli.py` / `RUNTIME.md`로 제공됨(§4 R7)**: 통합 앱이 턴별로 마운트하면 기계강제, *마운트 안 한* 순수 폴더매핑 chat만 prose-enforced로 남는다. (게이트 강화는 gate/battery/API 경로를 우선 강화하고, 래퍼 없는 chat엔 페르소나 준수로 간접 전달된다.)
- **application-harm**: 진짜 성구의 해로운 *적용*은 기계로 완전차단 불가 → L1 heuristic + L2 LLM이 줄이되 천장은 L3 인간 감사.
- **L2 자체 불완전** (R3 실증) + **LLM 비결정성** → L3 필요.
- **위기 탐지**: 2-tier(Tier-1 OVERRIDE / Tier-2 soft CHECKIN) + INPUT측 의미 hook + locale로 강화(§4 R5)됐으나, 패턴 floor는 *여전히 무한-evadable*(토큰 없는 패러프레이즈는 슬립) → over-trigger·`semantic_distress_check` hook·L3가 그래서 천장. 실 배포는 검증된 INPUT 분류기 권장.
- **privacy("무흔적")**: 3rd-party 모델 통과 시 provider 보존 가능 → 정직한 data-handling 고지(거짓 기밀 약속 금지).
- **신학적 정합성·성례성**: 엔지니어링 밖 — 권위/전통의 영역(판정 안 함).

## 6. 핵심 원칙 (한 줄)
**어느 자동 계층도 단독으로 완전하지 않다.** 그래서 겹쳐 막고, 못 닫는 것은 *명명*하며, 환원불가 지점엔 *인간을 앵커*로 둔다.
