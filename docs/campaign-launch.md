# 캠페인 런칭 그래프

YAML 브리프 한 장으로 Meta 광고 카피 3개를 만들고, 규칙으로 검수하고, 사람이 승인하면 광고 관리자에 올릴 런칭 패키지를 만듭니다. **광고 계정에는 아무것도 쓰지 않습니다.** 예산·기간·타깃은 CSV에 넣지 않고 사람이 광고 관리자 화면에서 입력합니다.

```
load_brief ─▶ research ─▶ copy ─▶ review ─┬─▶ approval ⏸ 사람 ─▶ package ─▶ handoff
     │                     ▲              │
     └─▶ blocked           └── 재작성 ◀───┘  걸린 변형만 · 최대 2회
```

| 노드 | 하는 일 | LLM |
|---|---|---|
| load_brief | 브리프 필수값·https·CTA·예산 상한(오타 방지)·기간 확인. 걸리면 여기서 멈춤 | — |
| research | 최근 M1 브리프에서 키워드가 겹치는 인사이트 3개, 수요 레이더 급상승 키워드 | — |
| copy | 변형 3개 작성. 2회차부터는 검수에서 걸린 변형만 다시 씀 | Codex (gpt-5.5) |
| review | 표시광고법상 실증이 필요한 표현(1위·최초·100%·보장 등), 조건 없는 '무료', 카피 속 링크, 자리표시자, 금지어, 필수 문구, Meta 권장 글자 수 | — |
| approval | 승인 카드를 Telegram·Slack 홈 채널로 보내고 멈춤 | — |
| package | `{date}_campaign_{id}_launch.md` + `{date}_campaign_{id}_ads.csv` (모든 광고 `PAUSED`) | — |
| handoff | 광고세트 이름을 meta-fatigue 감시 루프에 넘김 | — |

권장 글자 수 초과는 잘려 보일 뿐이라 재작성만 요청하고 막지 않습니다. 근거 없는 최상급 표현은 재작성 후에도 남으면 그 변형을 뺍니다. 통과한 변형이 2개 미만이면 승인 카드 없이 멈춥니다.

## 쓰는 법

```bash
python3 scripts/campaign-launch.py new ax-webinar-oct              # content/campaigns/briefs/ax-webinar-oct.yaml 생성
# 브리프를 채운 뒤
python3 scripts/campaign-launch.py run ax-webinar-oct --mode codex  # 승인 카드까지
```

승인은 텔레그램·슬랙에서 **일반 메시지**로 합니다.

| 메시지 | 동작 |
|---|---|
| `캠페인 승인 ax-webinar-oct` | 통과한 변형 전부로 패키지 생성 |
| `캠페인 승인 ax-webinar-oct 1 3` | 1·3번만 |
| `캠페인 반려 ax-webinar-oct 톤이 너무 딱딱함` | 반려 기록. 브리프를 고쳐 `run`을 다시 돌림 |
| `캠페인 목록` / `/pending` | 승인 대기 목록 |

`/approve campaign ...`처럼 **슬래시 명령으로 보내지 마세요.** Hermes 게이트웨이의 exec quick command는 슬래시 뒤 글자를 스크립트에 넘기지 않아서, `/approve`는 항상 `approve all`(콘텐츠 발행 전체 승인)로 실행됩니다. Mac 터미널에서는 `hermes-agent.sh approve campaign <id>`도 됩니다.

승인 요청 뒤 브리프 파일이나 카피가 바뀌면 승인이 거부됩니다. 다시 `run`해서 새 카드를 받으세요.

## 패키지 올리는 순서

1. 광고 관리자에서 캠페인·광고세트를 만들고 `launch.md` 1번 표의 값(목표·예산·기간·타깃)을 넣습니다. 켜지 않습니다.
2. 광고 1개를 임시로 만들어 내보내기(export)하고 CSV 열 이름을 비교합니다. 가져오기 템플릿 열 이름은 계정·시점마다 다를 수 있어서, 다르면 `config/campaign-launch.yaml`의 `package.columns`만 고치고 `campaign-launch.py repackage <id>`로 다시 만듭니다.
3. `ads.csv`를 가져오기 합니다. 모든 광고가 일시중지 상태로 들어옵니다.
4. 이미지·영상을 연결하고 `launch.md`의 "켜기 전 확인"을 마친 뒤 직접 켭니다.

## 지금 상태: 샘플 모드

```bash
python3 scripts/campaign-launch.py run tests/fixtures/campaign/brief_sample.yaml
python3 scripts/campaign-launch.py approve sample-ax-webinar
./scripts/campaign-launch-eval.sh
```

샘플은 1회차에 2번 변형(근거 없는 '1위'·'100%'·'보장')과 3번 변형(제목 41자)이 걸리고 2회차에 두 변형만 다시 써서 통과하는 흐름입니다. 산출물은 `_sample_` 접두사라 Notion에 올라가지 않고 알림도 보내지 않습니다.

실제로 쓰려면 `config/campaign-launch.yaml`의 `mode`를 `codex`로 바꾸거나 `run ... --mode codex`로 실행합니다. Codex 호출 전 loop budget을 확인하고, 사용량은 cost ledger에 `HERMES_CAMPAIGN_COPY`로 남습니다.

## 저장 위치

| 파일 | 위치 | 공개 레포 |
|---|---|---|
| 브리프 | `content/campaigns/briefs/{id}.yaml` | 제외 (`.gitignore`) |
| 상태·승인 카드 | `.harness/campaigns/{id}.json` · `{id}.approval.md` | 제외 |
| 런칭 패키지 | `content/campaigns/{date}_campaign_{id}_launch.md` · `_ads.csv` | 제외 → Notion `Campaign Launch` |

## 검수 규칙의 한계

규칙은 표현 단위로만 봅니다. 카피가 브리프에 없는 사실(시간·인원·성과 숫자)을 지어냈는지, 이미지 속 문구, 개인 특성 암시(Meta 정책)는 코드가 판단하지 못합니다. 승인 카드와 `launch.md`의 확인 목록이 그 부분을 사람에게 넘깁니다. 실증 필요 표현 목록은 법률 자문이 아니라 사내 검수용 기본값입니다.
