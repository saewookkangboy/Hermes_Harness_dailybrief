# RAG 평가 — AX 실무 레터

## 제목 후보

- A: RAG 평가, 어디부터 자동화할까요
- B: RAG 평가 실무 지도: 도구·사례·전망

## 30초 TLDR

- 근거 40건을 7개 렌즈로 정리했고, 가장 먼저 자동화할 단계는 측정·분석이에요.
- 성숙도는 L1에서 L3까지 끌어올리는 걸 목표로 잡았어요.
- 18개월 이후 신호도 5개 잡혀 있어서 관찰 목록에 올려 뒀어요.

## 오늘의 1가지

저는 이번 주 'RAG 평가' 자료를 보면서 측정·분석 단계의 자동화 여지가 가장 크다고 판단했어요. 채널 지표 자동 수집 → 주간 성과 리포트·이상 탐지부터 시작하고, 성과는 '리포트 작성 시간·이상 탐지 리드타임'으로 확인해요.

## 3분 읽기

### 1. AX 설계

- 측정·분석 (Quick Win): 채널 지표 자동 수집 → 주간 성과 리포트·이상 탐지부터 시작해요.
- 기획·전략 (Quick Win): 브리프 → 콘텐츠 캘린더·메시지 하우스 초안 자동 생성부터 시작해요.
- 콘텐츠 제작 (Quick Win): 채널별 카피·이미지·숏폼 변형을 템플릿 기반으로 대량 생성부터 시작해요.

### 2. 도구와 리소스

- Ragas: RAG 평가 용도로 써요. https://docs.ragas.io
- LangGraph: 에이전트 워크플로 용도로 써요. https://www.langchain.com/langgraph
- Model Context Protocol: 에이전트-도구 연결 표준 용도로 써요. https://modelcontextprotocol.io

### 3. 앞으로의 흐름

- Now (0–6개월): 앞으로 6개월 안에는 'RAG 평가'의 정의·개념 신호가 실무 의사결정으로 이어질 가능성이 커요.
- Next (6–18개월): 6~18개월 사이에는 도구·플랫폼 통합 역량이 'RAG 평가' 성과 격차를 만들 거예요.
- Future (18–36개월): 18~36개월 뒤 'RAG 평가'의 판도는 claude, genai, 시스템 같은 신규 용어에서 먼저 드러날 수 있어요.

## 이번 주 실습 1가지

측정·분석: 'RAG 평가' 파일럿 범위를 정하고 '리포트 작성 시간·이상 탐지 리드타임' 기준선을 이번 주에 기록해요. 한 주 뒤에 숫자를 비교해 보세요.

## 출처

- Tencent/WeKnora — https://github.com/Tencent/WeKnora
- A Matryoshka Hierarchical RAG for Efficient Multi-Hop Question Answering — http://arxiv.org/abs/2610.01767v1
- Retrieval-Augmented Generation (RAG): The Complete Guide to How AI Chooses, Retrieves, and Cites Web Pages — https://almcorp.com/retrieval-augmented-generation-rag-complete-guide
