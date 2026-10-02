<p align="center">
  <img src="../assets/docs/banner-docs-hub.svg" width="100%" alt="Hermes Documentation — Architecture, loops, wiki, multi-studio, agent model">
</p>

# Docs

Hermes Content Studio 운영·아키텍처 문서 허브예요.  
**Brief SoT**와 결정적 M1→M5를 중심으로, 버전 동결 아카이브와 통합 전략을 한곳에서 찾습니다.

| 먼저 볼 것 | 역할 |
|------------|------|
| [architecture/SYSTEM-LOGIC.md](./architecture/SYSTEM-LOGIC.md) | **현행 SoT (v2.1)** |
| [architecture/README.md](./architecture/README.md) | 버전 타임라인 · 아카이브 인덱스 |
| [../README.md](../README.md) | 저장소 홈 · 빠른 시작 · Gate A–D |

**최신 품질 기준선 (2026-08-12):** quick 40/0 · record 31/0 · pipeline 20–26s · Newsletter Gate A–D PASS · publishable=true

<p align="center">
  <img src="../assets/docs/diagram-channels.svg" width="100%" alt="Brief SoT → Blog · Threads · IG · LinkedIn · Newsletter">
</p>

<p align="center">
  <img src="../assets/docs/diagram-quality-gates.svg" width="100%" alt="Newsletter Gate A–D quality stack">
</p>

---

## 문서 맵

<p align="center">
  <img src="../assets/docs/diagram-timeline.svg" width="100%" alt="v1.0 Brief through v2.1 Graph Token Playbook timeline">
</p>

| 문서 | 한 줄 |
|------|--------|
| [SYSTEM-LOGIC.md](./architecture/SYSTEM-LOGIC.md) | Commander · M1–M5 · F1–F4 · Newsletter Gate A–D |
| [MULTI-STUDIO-ARCHITECTURE.md](./MULTI-STUDIO-ARCHITECTURE.md) | 부모 content-studio + sibling ×8 |
| [LLM-WIKI-INTEGRATION.md](./LLM-WIKI-INTEGRATION.md) | 일별 공장 유지 + 누적 wiki/graph 선택 도입 |
| [content-loops.md](./content-loops.md) | L1 triage · L2 supervised · L3 HITL |
| [HERMES-CONVERSATIONAL-AGENT-MODEL.md](./HERMES-CONVERSATIONAL-AGENT-MODEL.md) | 대화형 Agent · CAR · 이중 런타임 |

---

## 최근 설계 · 계획

| 문서 | 상태 |
|------|------|
| [AI Agent 블로그+Threads 설계](./superpowers/specs/2026-08-11-ai-agent-blog-threads-daily-report-design.md) | Approved — Velog형 리포트 + Threads 패키지 |
| [AI Agent 블로그+Threads 구현 계획](./superpowers/plans/2026-08-11-ai-agent-blog-threads-daily-report.md) | Config + Assembler 교체 |
| [Newsletter Production Readiness](./plans/2026-07-27-001-feat-newsletter-production-readiness-plan.md) | Gate A–D 완료 · 품질 harden 후속 |

---

## 빠른 검증

```bash
~/Hermes_Harness_dailybrief/scripts/init.sh --skip-health
~/Hermes_Harness_dailybrief/scripts/harness-eval.sh --quick
~/Hermes_Harness_dailybrief/scripts/newsletter-gate-c-eval.sh   # publishable
~/Hermes_Harness_dailybrief/scripts/e2e-smoke-test.sh
~/Hermes_Harness_dailybrief/scripts/generate-architecture-md.py
```

Notion 동기화: `~/Hermes_Harness_dailybrief/scripts/export-architecture-notion.sh`

---

## Plans · Archive

| 종류 | 경로 | 규칙 |
|------|------|------|
| 구현 계획 | [`plans/`](./plans/) · [`superpowers/plans/`](./superpowers/plans/) · [`superpowers/specs/`](./superpowers/specs/) | 요구사항·수용 기준 SoT |
| 버전 동결 | [`architecture/archive/`](./architecture/archive/) | bump 시만 추가 · 현행으로 편집 금지 |

비주얼 토큰: [`Getdesign.md`](../Getdesign.md) · SVG: [`assets/docs/`](../assets/docs/)  
방법론: [beautify-github-readme](https://github.com/oil-oil/beautify-github-readme) · Pure SVG · Value → Proof → First use
