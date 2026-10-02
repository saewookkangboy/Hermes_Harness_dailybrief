# [AX Blueprint] CDP 도입 방법

> 2026-10-02 · 도메인 데이터·CRM · 성숙도 L1 → L3

## AX 성숙도

- **현재:** L1 AI 보조 — 개별 작업에 생성형 AI를 도구로 써요
- **목표:** L3 에이전트 — 에이전트가 계획·실행하고 사람은 승인 지점만 맡아요
- 현재 수준은 일반적인 마케팅 팀 기준 가정치예요.

## 자동화 기회 매트릭스

| 가치사슬 | 영향도 | 실행 가능성 | 구분 | 목표 레벨 | 추천 도구 |
|----------|--------|-------------|------|-----------|-----------|
| 측정·분석 | 5 | 5 | Quick Win | L3 | Segment, GA4, Looker Studio |
| 최적화·개인화 | 5 | 5 | Quick Win | L3 | Salesforce Data Cloud, Optimizely, Braze |
| 콘텐츠 제작 | 4 | 4 | Quick Win | L3 | Canva Magic Studio, Gemini (Nano Banana), CapCut |
| 기획·전략 | 3 | 4 | 효율 개선 | L2 | NotebookLM, Claude |
| 배포·채널 운영 | 4 | 3 | 전략 과제 | L2 | n8n, Zapier, Buffer |
| 시장·고객 리서치 | 3 | 3 | 보류 | L2 | Perplexity, Google Trends, 네이버 데이터랩 |

## 단계별 설계

### 측정·분석 · Quick Win

- **자동화:** 채널 지표 자동 수집 → 주간 성과 리포트·이상 탐지 — 'CDP 도입' 기준으로 설계해요.
- **KPI:** 리포트 작성 시간·이상 탐지 리드타임
- **HITL:** 지표 해석과 다음 액션 결정은 사람이 해요.
- **리스크:** 개인정보·동의 범위를 벗어난 데이터 결합이 없는지 점검해야 해요.
- **근거:** Tracardi/tracardi — https://github.com/Tracardi/tracardi
- **근거:** rudderlabs/rudder-sdk-js — https://github.com/rudderlabs/rudder-sdk-js

### 최적화·개인화 · Quick Win

- **자동화:** A/B·세그먼트별 메시지 자동 실험과 예산 재배분 제안 — 'CDP 도입' 기준으로 설계해요.
- **KPI:** 전환율·ROAS·CTOR 개선폭
- **HITL:** 예산 재배분 승인·개인정보 사용 범위 결정은 사람이 해요.
- **리스크:** 개인정보·동의 범위를 벗어난 데이터 결합이 없는지 점검해야 해요.
- **근거:** 에이전시를 위한 Adobe Real-Time CDP Collaboration 사용 사례 — https://business.adobe.com/kr/resources/sdk/real-time-cdp-collaboration-for-agencies.html
- **근거:** CDP Use Cases: 11 Enterprise Marketing Examples - Insider — https://insiderone.com/cdp-use-cases

### 콘텐츠 제작 · Quick Win

- **자동화:** 채널별 카피·이미지·숏폼 변형을 템플릿 기반으로 대량 생성 — 'CDP 도입' 기준으로 설계해요.
- **KPI:** 에셋당 제작 시간·변형 수
- **HITL:** 브랜드 톤·사실 확인 검수는 사람이 해요.
- **리스크:** 근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요.
- **근거:** What Is a Customer Data Platform? CDP Guide [2026] — https://cdp.com/basics/what-is-a-customer-data-platform-cdp
- **근거:** 11 Best Customer Data Platforms (CDPs) Compared for 2026 — https://insiderone.com/best-customer-data-platform

### 기획·전략 · 효율 개선

- **자동화:** 브리프 → 콘텐츠 캘린더·메시지 하우스 초안 자동 생성 — 'CDP 도입' 기준으로 설계해요.
- **KPI:** 기획 사이클 타임(일)
- **HITL:** 포지셔닝·메시지 최종 승인은 사람이 해요.
- **리스크:** 근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요.
- **근거:** What Is a Customer Data Platform? A Guide for New Businesses — https://www.salesforce.com/marketing/data/what-is-a-customer-data-platform/smb
- **근거:** Top CDP Use Cases and How To Develop Them — https://cdp.com/articles/how-to-develop-cdp-use-cases

### 배포·채널 운영 · 전략 과제

- **자동화:** 채널별 최적 시간 예약 발행·크로스포스팅 워크플로 — 'CDP 도입' 기준으로 설계해요.
- **KPI:** 발행 리드타임·채널 커버리지
- **HITL:** 위기 이슈 시 발행 중단(stop button)은 사람이 해요.
- **리스크:** 근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요.
- **근거:** 7 CDP Challenges in 2026 (And How to Overcome Them) — https://cdp.com/articles/common-cdp-challenges
- **근거:** Top 5+ Vietnam Customer Data Platform Solutions in 2026 — https://www.tmasolutions.com/insights/vietnam-customer-data-platform

### 시장·고객 리서치 · 보류

- **자동화:** 검색·소셜·리뷰 신호를 매일 수집해 요약하는 리서치 에이전트 — 'CDP 도입' 기준으로 설계해요.
- **KPI:** 인사이트 리드타임(시간)
- **HITL:** 주간 우선순위 확정은 사람이 해요.
- **리스크:** 근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요.
- **근거:** Customer Data Platform Market Size, Share, Trends & Forecast What Is a Customer Data Platform? — https://www.fortunebusinessinsights.com/industry-reports/customer-data-platform-market-100633
- **근거:** Adobe Customer Data Platform Trends Report 2026 — https://business.adobe.com/resources/sdk/agentic-era-for-cdps.html

## 30/60/90일 로드맵

- **30일:** 측정·분석, 최적화·개인화
- **60일:** 콘텐츠 제작, 배포·채널 운영
- **90일:** 기획·전략, 시장·고객 리서치

## 거버넌스

- 모든 자동 발행에는 사람이 누르는 중단 버튼(stop button)을 둬요.
- 생성 결과는 출처 URL과 함께 저장해 사후 감사가 가능하게 해요.
