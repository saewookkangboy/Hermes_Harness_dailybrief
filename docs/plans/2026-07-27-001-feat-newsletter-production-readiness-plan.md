---
title: Newsletter Production Readiness - Plan
type: feat
date: 2026-07-27
topic: newsletter-production-readiness
artifact_contract: ce-unified-plan/v1
artifact_readiness: requirements-only
product_contract_source: ce-brainstorm
execution: code
---

# Newsletter Production Readiness - Plan

## Goal Capsule

- **Objective:** Daily Brief의 신선도를 보존하면서 이메일과 LinkedIn에서 바로 발행할 수 있는 장문 뉴스레터를 매일 안정적으로 생성한다.
- **Product authority:** `content/research/{date}_brief.md`를 주제와 사실의 단일 원천으로 사용한다.
- **Performance objective:** 제목이 열람을 유도하고, 본문이 스크롤을 유지하며, 본문과 직접 연결된 단일 CTA가 클릭을 유도하는 편집 흐름을 구축한다.
- **Execution profile:** 결정적 선별·조립·검증을 기본으로 유지하고 `HERMES_ENHANCE=1`일 때 LLM 산문 개선을 적용한다.
- **Open blockers:** 없음. 세부 보존 기간과 모델 호출 계약은 계획 단계에서 기존 하네스 규칙에 맞춰 확정한다.

---

## Product Contract

### Summary

현행 M2b 뉴스레터를 결정적 골격, 선택적 LLM 산문, 결정적 품질 게이트의 3단 구조로 고도화한다.
매 호 이메일 Markdown·HTML, LinkedIn 장문, 제목 후보와 점수, 실제 URL을 가진 단일 CTA, 16:9 타이틀 이미지 프롬프트, 복사·붙여넣기 패키지를 함께 생성한다.

### Problem Frame

현재 파이프라인은 브리프부터 Markdown·HTML·Notion 붙여넣기 팩까지 안정적으로 생성하지만, 구조 검증 통과가 발송 품질을 보장하지 않는다.
최근 브리프의 Top 인사이트는 매일 바뀌었지만 뉴스레터 제목, Hero, 일부 모듈과 CTA는 반복되었다.
영문 인사이트 제목을 정적 한국어 폴백으로 치환하는 과정에서 신선한 입력이 같은 주제로 수렴했고, 하드코딩된 Hero와 CTA가 오타와 내부 프로세스 문구까지 반복했다.

제목과 본문, 본문과 출처가 서로 다른 내용을 가리키는 사례도 존재했다.
CTA는 실제 이동 URL이 없는 플레이스홀더였고, CTOR 피드백은 평가용 소수 시드에 의존했다.
리서치 단계에서는 발송에 부적합한 정크·NSFW 출처가 후보로 들어올 수 있어 편집 안전성도 충분하지 않다.

### Key Decisions

- **D 범위로 한 번에 고도화한다.** 콘텐츠 품질, 채널 형식, 신선도, 성과 학습, 이미지 프롬프트를 같은 릴리스 범위에서 다룬다. (session-settled: user-directed — chosen over 이메일 본문만 우선 개선: 실사용에는 전 발행 흐름의 정합성이 필요함)
- **하이브리드 생성을 채택한다.** 결정적 계층이 선별·구조·정합·검증을 책임지고, LLM은 Hero·모듈·LinkedIn 장문·제목 변형·CTA 산문을 개선한다. (session-settled: user-directed — chosen over 결정적 전용 및 LLM 우선: 품질과 폴백 안정성을 함께 확보함)
- **Daily Brief를 콘텐츠 SoT로 유지한다.** 별도 뉴스 수집기를 뉴스레터에 추가하지 않고 브리프의 신선한 인사이트를 손실 없이 전달한다. (session-settled: user-approved — chosen over 뉴스레터 전용 리서치 파이프라인: 중복 리서치와 운영비를 피함)
- **이메일과 LinkedIn은 같은 논지를 공유하되 별도 원고로 생성한다.** 이메일은 클릭 전환, LinkedIn은 장문 가독성과 플랫폼 배포 특성에 맞춘다. (session-settled: user-directed — chosen over 동일 원고 복제: 채널별 독서 행동이 다름)
- **타이틀 이미지는 프롬프트까지만 자동 생성한다.** 매 호 16:9 아트디렉션을 제공하지만 이미지 API 호출과 실제 이미지 파일 생성은 이번 범위에서 제외한다. (session-settled: user-directed — chosen over API 자동 생성: 생성 통제와 운영 단순성을 우선함)
- **Notion 붙여넣기 배포를 유지한다.** 일반 뉴스레터 서비스에 사용할 Markdown·HTML 복사본을 강화하고 ESP 자동 발송은 현행 HITL 경계를 유지한다. (session-settled: user-approved — chosen over 이번 릴리스의 ESP 자동화: 발송 품질 안정화가 선행되어야 함)

### Actors

- A1. **콘텐츠 운영자:** 산출물을 검토하고 LinkedIn 또는 일반 뉴스레터 서비스에 복사·붙여넣어 발행한다.
- A2. **Daily Brief 파이프라인:** 매 호의 주제, 근거, 출처와 실무 관점을 제공한다.
- A3. **결정적 뉴스레터 계층:** 인사이트를 선별하고 중복·정합·안전·형식을 검증한다.
- A4. **선택적 LLM 개선 계층:** 제공된 근거 범위 안에서 채널별 장문 산문을 작성한다.
- A5. **독자:** 제목을 보고 열람하고, 본문을 읽은 뒤 단일 CTA를 클릭하거나 회신한다.

### Requirements

**Freshness and editorial safety**

- R1. 매 호는 해당 날짜 Daily Brief의 유효한 인사이트를 사용하며 정적 주제 폴백 때문에 최근 호와 같은 핵심 주제로 수렴해서는 안 된다.
- R2. 최근 발행 이력과 비교해 핵심 주제, 제목 패턴, 출처 URL과 본문 표현의 반복을 탐지하고 임계치를 넘으면 다음 적합 인사이트를 선택해야 한다.
- R3. 질문형, 숫자형, 대조형, 구체 명사구 등 제목 패턴을 순환하며 같은 패턴이 연속 발행되지 않도록 해야 한다.
- R4. NSFW, 정크, 내용 농장, 주제 비관련 출처는 뉴스레터 후보에서 제외해야 한다.
- R5. 금지 보일러플레이트, 내부 제작 메모, 플레이스홀더와 알려진 오타가 독자용 산출물에 포함되어서는 안 된다.
- R6. LLM 개선이 꺼져 있거나 실패해도 결정적 계층은 당일 브리프에 근거한 신선하고 완결된 발행 가능 초안을 출력해야 한다.

**Content coherence and performance**

- R7. 제목, 프리헤더, Hero, 핵심 논지, CTA와 대표 출처는 동일한 중심 인사이트를 설명해야 한다.
- R8. 각 호는 `earn open → earn scroll → earn click`의 세 행동 목표를 분리해 충족해야 한다.
- R9. 제목은 구체적인 독자 효익이나 긴장을 앞세우고, 프리헤더는 제목을 반복하지 않으며 본문이 실제로 제공하는 추가 가치를 약속해야 한다.
- R10. 본문은 하나의 중심 아이디어를 `problem → explanation → insight → practical application` 순서로 전개해야 한다.
- R11. CTA는 한 개만 제공하고, 본문 논지와 직접 연결된 실제 HTTPS URL을 사용하며, 독자가 클릭 후 무엇을 얻는지 명시해야 한다.
- R12. 제목이나 CTA의 성과를 높이기 위해 본문과 다른 약속을 사용해서는 안 된다.

**Email deliverables**

- R13. 이메일 본문은 600–1,200단어 범위에서 모바일로 훑어볼 수 있는 짧은 문단, 명확한 소제목과 단일 CTA를 사용해야 한다.
- R14. 이메일은 일반 뉴스레터 서비스에 복사·붙여넣을 수 있는 독립적인 Markdown과 이메일 호환 HTML을 함께 제공해야 한다.
- R15. HTML은 제목, 프리헤더, 본문, 실제 CTA URL과 타이틀 이미지 삽입 위치를 포함해야 하며 이메일 클라이언트 호환 구조를 유지해야 한다.
- R16. 붙여넣기 팩은 제목, 프리헤더, Markdown 본문, HTML 본문, CTA URL과 16:9 이미지 프롬프트를 구분된 블록으로 제공해야 한다.

**LinkedIn deliverable**

- R17. LinkedIn 뉴스레터는 이메일과 같은 중심 논지와 출처를 사용하되 이메일 문장을 그대로 복제하지 않는 별도 원고여야 한다.
- R18. LinkedIn 원고는 800–1,500단어, 도입 훅, 3–5개 주요 섹션, 200–300단어 간격의 소제목, 짧은 문단과 단일 CTA를 가져야 한다.
- R19. LinkedIn 원고는 16:9 타이틀 이미지의 삽입 위치와 접근 가능한 대체 텍스트를 제공해야 한다.
- R20. LinkedIn CTA도 실제 URL을 사용하고 해당 호의 논지와 연결되어야 한다.

**Title image prompt**

- R21. 매 호는 뉴스레터 전체를 대표하는 16:9 타이틀 이미지 프롬프트를 생성해야 한다.
- R22. 이미지 프롬프트는 중심 주제, 시각적 은유, 구도, 색상, 조명, 브랜드 톤, 금지 요소와 텍스트 오버레이 지침을 포함해야 한다.
- R23. 이미지 프롬프트는 이메일과 LinkedIn에서 공통 사용 가능해야 하며 실제 이미지 생성이나 외부 API 호출을 요구해서는 안 된다.

**Measurement and learning**

- R24. 오픈율은 Apple Mail Privacy Protection 영향을 받는 방향성 지표로 취급하고 CTOR, CTR, 회신율, 구독 해지율과 CTA 전환을 함께 기록해야 한다.
- R25. 초기 목표는 CTOR 10% 이상, CTR 2–3% 이상, 회신율 1% 이상과 구독 해지율 0.5% 미만으로 설정하되 자체 기준선 추세를 외부 벤치마크보다 우선해야 한다.
- R26. 제목 실험은 한 번에 한 변수만 바꾸고 제목 패턴별 결과를 누적해 다음 후보의 가중치에 반영해야 한다.
- R27. 실제 성과 데이터가 부족할 때 평가용 시드 수치를 학습된 성과처럼 사용해서는 안 된다.

**Quality gates and operations**

- R28. 발행 전 신선도, 제목-본문-출처 정합, CTA URL 유효성, 안전성, 보일러플레이트, 채널별 길이와 구조를 결정적으로 검사해야 한다.
- R29. 필수 품질 게이트가 실패하면 산출물을 발행 가능 상태로 표시하거나 Notion 배포 단계로 넘겨서는 안 된다.
- R30. 기존 일일 파이프라인, Notion 아카이브, ESP 승인 경계와 `validate-output.sh` 호환성을 유지해야 한다.

### Key Flows

- F1. **Daily issue generation**
  - **Trigger:** 해당 날짜 Daily Brief가 검증을 통과한다.
  - **Actors:** A2, A3, A4
  - **Steps:** 안전한 인사이트 선별 → 최근 호 중복 검사 → 제목 패턴 선택 → 채널 공통 콘텐츠 계약 생성 → 선택적 LLM 산문 개선 → 결정적 검증
  - **Outcome:** 이메일과 LinkedIn에 사용할 신선하고 정합한 발행 패키지가 생성된다.
  - **Covered by:** R1–R12, R24–R30

- F2. **Email publishing**
  - **Trigger:** 운영자가 일반 뉴스레터 서비스에 당일 호를 발행하려 한다.
  - **Actors:** A1, A3
  - **Steps:** 붙여넣기 팩에서 제목·프리헤더 선택 → Markdown 또는 HTML 복사 → 실제 CTA URL 확인 → 생성한 타이틀 이미지를 지정 위치에 삽입 → 미리보기 후 발행
  - **Outcome:** 별도 재작성 없이 이메일 캠페인을 준비할 수 있다.
  - **Covered by:** R13–R16, R21–R23, R28–R30

- F3. **LinkedIn publishing**
  - **Trigger:** 운영자가 LinkedIn 뉴스레터 글을 작성한다.
  - **Actors:** A1, A3
  - **Steps:** LinkedIn 전용 장문 복사 → 소제목과 CTA 확인 → 생성한 16:9 이미지를 타이틀로 삽입 → 대체 텍스트 입력 → 발행
  - **Outcome:** 플랫폼 형식에 맞는 장문을 재편집 없이 게시할 수 있다.
  - **Covered by:** R17–R23, R28–R30

- F4. **Performance feedback**
  - **Trigger:** 발행 후 오픈, 클릭, 회신과 구독 해지 데이터가 확보된다.
  - **Actors:** A1, A3
  - **Steps:** 실제 지표 기록 → 제목 패턴과 CTA 성과 연결 → 시드 데이터 제외 → 다음 호 제목 후보 가중치 조정
  - **Outcome:** 제목과 CTA 선택이 실제 독자 반응에 따라 점진적으로 개선된다.
  - **Covered by:** R24–R27

### Acceptance Examples

- AE1. **Fresh English source title**
  - **Covers:** R1, R2, R7
  - **Given:** 당일 최상위 브리프 인사이트가 영문 제목이고 최근 호와 다른 주제다.
  - **When:** 뉴스레터를 생성한다.
  - **Then:** 정적 한국어 폴백 대신 해당 인사이트의 의미를 보존한 제목과 본문이 생성된다.

- AE2. **Recent-topic collision**
  - **Covers:** R2, R3
  - **Given:** 최상위 후보가 최근 호의 핵심 주제 또는 제목 패턴과 중복된다.
  - **When:** 신선도 검사가 실행된다.
  - **Then:** 다음 적합 인사이트나 다른 제목 패턴이 선택되고 선택 이유가 품질 메타에 기록된다.

- AE3. **Enhancement unavailable**
  - **Covers:** R6
  - **Given:** `HERMES_ENHANCE=0`이거나 LLM 호출이 실패한다.
  - **When:** 일일 뉴스레터 파이프라인을 실행한다.
  - **Then:** 파이프라인은 실패하지 않고 당일 브리프 기반의 결정적 이메일·LinkedIn 초안을 출력한다.

- AE4. **Subject-body mismatch**
  - **Covers:** R7, R12, R28, R29
  - **Given:** 제목은 ChatGPT 광고를 약속하지만 Hero와 대표 출처는 Workspace Agents를 설명한다.
  - **When:** 정합성 검사가 실행된다.
  - **Then:** 발행 게이트가 실패하고 Notion 배포가 중단된다.

- AE5. **Invalid CTA**
  - **Covers:** R11, R16, R20, R28
  - **Given:** CTA가 `#`, 빈 값 또는 “통합 컨텍스트에서 확인” 같은 플레이스홀더를 사용한다.
  - **When:** CTA 검사가 실행된다.
  - **Then:** 발행 게이트가 실패하며 실제 HTTPS URL 없이는 통과하지 않는다.

- AE6. **Unsafe source**
  - **Covers:** R4
  - **Given:** 브리프 후보에 NSFW 또는 주제 비관련 콘텐츠가 포함된다.
  - **When:** 뉴스레터 인사이트를 선별한다.
  - **Then:** 해당 후보는 제외되고 안전한 다음 후보가 선택된다.

- AE7. **Paste-ready outputs**
  - **Covers:** R13–R23
  - **Given:** 모든 품질 게이트가 통과한다.
  - **When:** 운영자가 붙여넣기 팩을 연다.
  - **Then:** 이메일 Markdown·HTML, LinkedIn 장문, 실제 CTA URL, 16:9 이미지 프롬프트와 대체 텍스트를 명확히 구분해 복사할 수 있다.

- AE8. **Seed-only metrics**
  - **Covers:** R24–R27
  - **Given:** 성과 원장에 평가용 시드만 존재한다.
  - **When:** 다음 호 제목 점수를 계산한다.
  - **Then:** 시드는 실측 학습에서 제외되고 정적 기본 가중치가 사용된다.

### Success Criteria

- 최근 7개 발행 호에서 동일한 핵심 제목과 Hero 문단의 반복이 없다.
- 제목, Hero, 대표 출처와 CTA의 의미 정합 검사가 모든 발행 호에서 통과한다.
- 이메일과 LinkedIn 원고가 각각 정의된 길이와 구조를 충족한다.
- 모든 발행 패키지는 실제 HTTPS CTA URL을 한 개만 포함한다.
- 모든 발행 패키지는 16:9 이미지 프롬프트와 대체 텍스트를 포함한다.
- `HERMES_ENHANCE=0`과 LLM 실패 상황 모두에서 결정적 폴백 산출물이 검증을 통과한다.
- 파이프라인 도입 후 실제 캠페인 기준 CTOR, CTR, 회신율과 구독 해지율의 이동 평균이 기록된다.
- 최소 8개 실제 발행 데이터가 누적된 뒤 제목 패턴과 CTA 성과의 자체 기준선이 수립된다.

### Scope Boundaries

**Included**

- 이메일 뉴스레터 Markdown·HTML과 일반 서비스용 붙여넣기 팩
- LinkedIn 뉴스레터 전용 장문 원고
- Daily Brief 기반 신선도·중복 방지·안전 필터
- 제목·본문·출처·CTA 정합 검증
- 16:9 타이틀 이미지 프롬프트와 대체 텍스트
- 실제 성과 기반 제목 패턴 학습
- Notion 아카이브와 현행 HITL 발송 경계 유지

**Deferred**

- 이미지 API를 통한 실제 PNG/JPEG 생성
- ESP 자동 캠페인 생성과 무인 발송
- 구독자 세그먼트별 개인화 원고
- 다변량 테스트와 통계적 유의성 자동 판정

**Outside this release**

- Daily Brief를 대체하는 뉴스레터 전용 리서치 시스템
- LinkedIn 자동 로그인·자동 게시
- 클릭을 높이기 위한 다중 CTA 또는 본문과 무관한 프로모션

### Dependencies and Assumptions

- Daily Brief의 구조와 출처 URL은 뉴스레터 조립기가 파싱할 수 있는 현행 계약을 유지한다.
- 선택적 LLM은 브리프에 없는 사실을 추가하지 않고 제공된 근거 안에서만 산문을 개선한다.
- 운영자는 생성된 이미지 프롬프트를 외부 이미지 도구에서 실행하고 결과물을 직접 삽입한다.
- CTA 대상은 발행 전에 접근 가능한 실제 블로그 또는 Notion permalink로 확정된다.
- 성과 학습에는 평가 시드가 아닌 실제 발송 데이터만 사용한다.

### Sources and Research

- `scripts/lib/newsletter_quality.py` — 정적 제목 폴백, Hero, CTA와 현행 조립 흐름
- `config/newsletter.yaml` — 현행 CTOR 목표, 제목 제한, Notion paste와 ESP HITL 경계
- `content/research/2026-07-20_brief.md`–`content/research/2026-07-27_brief.md` — 일별 인사이트 신선도 근거
- `content/newsletter/2026-07-20_newsletter_ax-faq.md`–`content/newsletter/2026-07-27_newsletter_ax-faq.md` — 제목·Hero·오타 반복 근거
- `content/logs/2026-07-26_newsletter-eval-report.md` — 현행 구조 게이트의 통과 범위
- MailerLite 계열 2026 벤치마크 요약 — CTOR 중앙값 약 6.8%, 10% 이상 우수, Apple MPP로 오픈율 왜곡
- B2B founder/CEO newsletter 사례 — 단일 아이디어, 문제→설명→인사이트, 실용 프레임, 단일 soft CTA
- LinkedIn newsletter 2026 사례 — 800–1,500단어, 짧은 문단, 3–5개 섹션, 시각물 1개, 단일 구체 CTA
