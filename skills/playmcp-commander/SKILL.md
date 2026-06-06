---
name: playmcp-commander
description: "PlayMCP(Kakao) MCP-Gateway 커맨더: Slack과 동일한 명령·대화 채널 역할."
version: 1.1.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [playmcp, kakao, mcp, commander, gateway, command-channel]
    related_skills: [content-pipeline, marketing-research, vibe-coding-cursor]
---

# PlayMCP Commander — Kakao MCP 커맨더 채널

PlayMCP MCP-Gateway(`https://playmcp.kakao.com/mcp`)를 Slack Bot과 **동일한 커맨더(명령) 채널**로 사용합니다.

## 역할 정의 (Slack 대비)

| 역할 | Slack (Bot Token) | PlayMCP (MCP-Gateway) |
|------|-------------------|------------------------|
| 명령 수신 | @mention / DM | Hermes chat + PlayMCP 도구 |
| 콘텐츠 파이프라인 트리거 | cron deliver `slack:#채널` | `hermes -z` + `--skills playmcp-commander,...` |
| 외부 도구 연동 | Slack API | 도구함 MCP 서버 (최대 10개) |
| 인증 | xoxb- + xapp- | OTT → Bearer 토큰 |

## 사전 조건

1. PlayMCP 로그인: https://playmcp.kakao.com
2. 도구함에 필요한 MCP 서버 추가: https://playmcp.kakao.com/toolbox
3. 연결 설정: `~/hermes-content-studio/scripts/setup-playmcp.sh`
4. Hermes MCP: `playmcp` 서버 enabled (`~/.hermes/config.yaml`)

## 커맨더 명령 (Hermes CLI)

```bash
# 리서치 (Slack 대화와 동일한 트리거)
hermes -z "이번 주 AI 마케팅 트렌드 리서치 브리프 작성해줘" \
  --skills playmcp-commander,marketing-research

# 콘텐츠 패키지
hermes -z "이번 주 리서치 기반 블로그+인스타+링크드인 초안 만들어줘" \
  --skills playmcp-commander,content-pipeline

# PlayMCP 도구함 도구 활용 (카카오맵, 검색 등)
hermes chat -s playmcp-commander
```

## 워크플로

1. 사용자 명령 수신 (Hermes chat / cron / 수동 `-z`)
2. `playmcp-commander` 스킬로 커맨더 컨텍스트 로드
3. PlayMCP MCP 도구(`mcp_playmcp_*`)로 도구함 서버 호출
4. `content-pipeline` 등 오케스트레이션 스킬과 연계
5. 산출물 → `~/hermes-content-studio/content/{channel}/`

## 토큰 갱신

액세스 토큰 만료 시 PlayMCP 도구함에서 새 OTT 발급 후:

```bash
ONE_TIME_TOKEN=새OTT ~/hermes-content-studio/scripts/setup-playmcp.sh
```

## 품질 게이트

- [ ] `hermes mcp test playmcp` 연결 확인
- [ ] 도구함에 콘텐츠 파이프라인에 필요한 MCP 서버 등록
- [ ] 산출물은 `content/` 채널 폴더에 저장
- [ ] Getdesign.md 톤·레이아웃 준수
