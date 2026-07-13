# Hermes Content Studio — Architecture Docs

> 시스템 로직·Mermaid 다이어그램 SoT · 구현 단계별 버전 아카이브

## 현행 (Current)

| 문서 | 버전 | 기간 | 설명 |
|------|------|------|------|
| [SYSTEM-LOGIC.md](./SYSTEM-LOGIC.md) | **v2.0** | 2026-07-12 ~ | Multi-Studio · JARVIS · Notion OAuth · EasyTool |

자동 생성 (Notion 동기화용):

```bash
~/hermes-content-studio/scripts/generate-architecture-md.py
~/hermes-content-studio/scripts/export-architecture-notion.sh
```

산출: `content/logs/{date}_studio-resources-spec.md` · `{date}_studio-dependency-diagrams.md` · `{date}_cursor-agent-resources.md`

## 버전 아카이브 (Implementation Timeline)

| 버전 | 아카이브 | 커밋 시대 | 핵심 마일스톤 |
|------|----------|-----------|---------------|
| v1.0 | [archive/v1.0-daily-brief-baseline.md](./archive/v1.0-daily-brief-baseline.md) | 2026-06-07 | 결정적 M1 Top 7 · Harness v1.2 초기 |
| v1.1 | [archive/v1.1-harness-telegram.md](./archive/v1.1-harness-telegram.md) | 2026-06-08 | Telegram Commander · Notion M5 · Brief SoT |
| v1.2 | [archive/v1.2-newsletter-commander.md](./archive/v1.2-newsletter-commander.md) | 2026-06-08 | B2B Newsletter P0–P6 · hermes-agent CLI |
| v1.3 | [archive/v1.3-content-loops-agents.md](./archive/v1.3-content-loops-agents.md) | 2026-06-27 | Content Loops L1/L2 · Agent A–D · Wiki |
| v1.4 | [archive/v1.4-quality-stack.md](./archive/v1.4-quality-stack.md) | 2026-07-01 | Voice/Naturalness/Budget P4–P15 |
| v2.0 | [archive/v2.0-multi-studio-jarvis.md](./archive/v2.0-multi-studio-jarvis.md) | 2026-07-13 | 8 Studio · JARVIS · OAuth watch (스냅샷) |

> **규칙:** major 버전 bump 시 이전 `SYSTEM-LOGIC.md` 내용을 `archive/v{X.Y}-*.md`로 복사한 뒤 현행 문서를 갱신한다.

## 관련 문서

| 문서 | 역할 |
|------|------|
| [HERMES-CONVERSATIONAL-AGENT-MODEL.md](../HERMES-CONVERSATIONAL-AGENT-MODEL.md) | 대화형 Agent · CAR 매핑 |
| [content-loops.md](../content-loops.md) | L1/L2/L3 루프 cadence |
| [MULTI-STUDIO-ARCHITECTURE.md](../MULTI-STUDIO-ARCHITECTURE.md) | 8 Studio registry · upstream |
| [LLM-WIKI-INTEGRATION.md](../LLM-WIKI-INTEGRATION.md) | Wiki 이중 메모리 |
| [JARVIS.md](../../JARVIS.md) | 프로젝트 메모리 · OMM |
| [HARNESS.md](../../HARNESS.md) | 5-Subsystem · Voice/Budget |
