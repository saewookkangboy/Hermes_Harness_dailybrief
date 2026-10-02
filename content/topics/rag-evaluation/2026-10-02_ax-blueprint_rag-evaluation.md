# [AX Blueprint] RAG 평가

> 2026-10-02 · 도메인 AI 기술 · 성숙도 L1 → L3

## AX 성숙도

- **현재:** L1 AI 보조 — 개별 작업에 생성형 AI를 도구로 써요
- **목표:** L3 에이전트 — 에이전트가 계획·실행하고 사람은 승인 지점만 맡아요
- 현재 수준은 일반적인 마케팅 팀 기준 가정치예요.

## 자동화 기회 매트릭스

| 가치사슬 | 영향도 | 실행 가능성 | 구분 | 목표 레벨 | 추천 도구 |
|----------|--------|-------------|------|-----------|-----------|
| 측정·분석 | 4 | 5 | Quick Win | L3 | Ragas, GA4, Looker Studio |
| 기획·전략 | 4 | 4 | Quick Win | L3 | NotebookLM, Claude |
| 콘텐츠 제작 | 4 | 4 | Quick Win | L3 | LangGraph, Canva Magic Studio, Gemini (Nano Banana) |
| 시장·고객 리서치 | 4 | 3 | 전략 과제 | L2 | Perplexity, Google Trends, 네이버 데이터랩 |
| 최적화·개인화 | 4 | 3 | 전략 과제 | L2 | Optimizely, Braze |
| 배포·채널 운영 | 3 | 3 | 보류 | L2 | Model Context Protocol, n8n, Zapier |

## 단계별 설계

### 측정·분석 · Quick Win

- **자동화:** 채널 지표 자동 수집 → 주간 성과 리포트·이상 탐지 — 'RAG 평가' 기준으로 설계해요.
- **KPI:** 리포트 작성 시간·이상 탐지 리드타임
- **HITL:** 지표 해석과 다음 액션 결정은 사람이 해요.
- **리스크:** 개인정보·동의 범위를 벗어난 데이터 결합이 없는지 점검해야 해요.
- **근거:** 기업용 RAG 솔루션 선택 가이드: 검색 정확도·보안·운영 방식으로 외 — https://blog.bigshift.kr/기업용-rag-솔루션-선택-가이드-검색-정확도보안운영-방식으로-외주-업체-고르는-법
- **근거:** RAG 평가 — ragas·faithfulness로 검색 품질 재는 법 — https://labelwebs.tistory.com/583

### 기획·전략 · Quick Win

- **자동화:** 브리프 → 콘텐츠 캘린더·메시지 하우스 초안 자동 생성 — 'RAG 평가' 기준으로 설계해요.
- **KPI:** 기획 사이클 타임(일)
- **HITL:** 포지셔닝·메시지 최종 승인은 사람이 해요.
- **리스크:** 근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요.
- **근거:** RAG Testing and Evaluation: How to Validate Retrieval — https://shiftasia.com/column/rag-testing-and-evaluation-how-to-validate-rag-systems
- **근거:** Ragas Guide 2026 / Evaluation framework for RAG pipelines — https://tools.zgba.com/tools/ragas

### 콘텐츠 제작 · Quick Win

- **자동화:** 채널별 카피·이미지·숏폼 변형을 템플릿 기반으로 대량 생성 — 'RAG 평가' 기준으로 설계해요.
- **KPI:** 에셋당 제작 시간·변형 수
- **HITL:** 브랜드 톤·사실 확인 검수는 사람이 해요.
- **리스크:** 'RAG Testing and Evaluation: How to Validate Retrieval' 같은 규제·신뢰 이슈를 발행 전 체크리스트로 관리해야 해요.
- **근거:** RAG 시스템, 어떻게 평가해야 할까? — RAGAS로 정량적 품질 검증 - CH — https://blog.choonzang.com/it/ai/4990
- **근거:** [실용화 완전 가이드] 생성 AI의 사내 도입 (RAG)을 성공으로 이끄는 — https://note.com/aka_sh/n/n9e993c07a5c1?hl=ko

### 시장·고객 리서치 · 전략 과제

- **자동화:** 검색·소셜·리뷰 신호를 매일 수집해 요약하는 리서치 에이전트 — 'RAG 평가' 기준으로 설계해요.
- **KPI:** 인사이트 리드타임(시간)
- **HITL:** 주간 우선순위 확정은 사람이 해요.
- **리스크:** 근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요.
- **근거:** A Matryoshka Hierarchical RAG for Efficient Multi-Hop Question Answering — http://arxiv.org/abs/2610.01767v1
- **근거:** Mapping the RAG Landscape: A Four Axis Taxonomy of Efficiency, Defense, Interactivity, and Reasoning — http://arxiv.org/abs/2610.01936v1

### 최적화·개인화 · 전략 과제

- **자동화:** A/B·세그먼트별 메시지 자동 실험과 예산 재배분 제안 — 'RAG 평가' 기준으로 설계해요.
- **KPI:** 전환율·ROAS·CTOR 개선폭
- **HITL:** 예산 재배분 승인·개인정보 사용 범위 결정은 사람이 해요.
- **리스크:** 'RAG Testing and Evaluation: How to Validate Retrieval' 같은 규제·신뢰 이슈를 발행 전 체크리스트로 관리해야 해요.
- **근거:** [초점] '에이전틱 AI' 시대의 도래 아웃소싱 산업, 인력 공급 넘어 '통제권' 경쟁으로 — https://www.outsourcing.co.kr/news/articleView.html?idxno=203885
- **근거:** RAG의 보안 위험과 대책｜사내 도입을 본 운영까지 진행하기 위한 설 — https://note.com/hike_inc/n/nefd439c42908?hl=ko

### 배포·채널 운영 · 보류

- **자동화:** 채널별 최적 시간 예약 발행·크로스포스팅 워크플로 — 'RAG 평가' 기준으로 설계해요.
- **KPI:** 발행 리드타임·채널 커버리지
- **HITL:** 위기 이슈 시 발행 중단(stop button)은 사람이 해요.
- **리스크:** 'RAG Testing and Evaluation: How to Validate Retrieval' 같은 규제·신뢰 이슈를 발행 전 체크리스트로 관리해야 해요.
- **근거:** promptfoo/promptfoo — https://github.com/promptfoo/promptfoo
- **근거:** dataelement/bisheng — https://github.com/dataelement/bisheng

## 30/60/90일 로드맵

- **30일:** 측정·분석, 기획·전략
- **60일:** 콘텐츠 제작, 시장·고객 리서치
- **90일:** 배포·채널 운영

## 거버넌스

- 모든 자동 발행에는 사람이 누르는 중단 버튼(stop button)을 둬요.
- 생성 결과는 출처 URL과 함께 저장해 사후 감사가 가능하게 해요.
- 주의 이슈: RAG Testing and Evaluation: How to Validate Retrieval.
- 주의 이슈: RAG Evaluation 2026: The Four Core Metrics and How to Read.
