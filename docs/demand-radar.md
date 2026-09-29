# 네이버 데이터랩 수요 레이더

매주 월요일 08:40(KST)에 테마별 키워드의 네이버 검색 추이를 보고, 급상승 키워드를 Slack 홈 채널에 **제안**합니다. M1 리서치에는 자동으로 넣지 않습니다. 넣을 키워드는 사람이 골라 `/research <키워드>`로 실행합니다.

| 항목 | 값 (`config/demand-radar.yaml`) |
|---|---|
| 테마 | AI 에이전트·자동화 · AX·AI 교육 · AI 검색 최적화 (테마당 키워드 5개) |
| 기간 | 최근 12주, 주 단위 (지난주 월~일까지) |
| 급상승 | 지난주 ÷ 직전 4주 평균 ≥ +30%, 기준값 ≥ 2.0, 최대 5개 |
| 산출 | Slack 제안 + `content/signals/{date}_demand-radar.md` → Notion `Demand Radar` |

## 수치 읽는 법

데이터랩 ratio는 **요청 안에서 가장 큰 값을 100으로 둔 상대값**입니다. 그래서 레이더는 키워드를 다른 키워드와 비교하지 않고, 자기 과거와만 비교합니다. 표의 "지난주 17.0"은 검색량이 아니라 상대 지수입니다. 기준값이 아주 작은 키워드(예: 평균 0.8)는 한두 건 차이로 +300%가 나와서 제외합니다.

## 지금 상태: 샘플 모드

```bash
python3 scripts/demand-radar.py --mode sample --print-report
./scripts/demand-radar-eval.sh
```

샘플 산출물은 `_sample_` 접두사라 Notion에서 빠지고, cron도 등록되지 않습니다.

## 실데이터 연결 (키 준비 후)

네이버 오픈 API는 2026-07-31부터 NAVER API HUB로 이관됐습니다. 신규 키는 HUB 방식이고, 그 전에 받은 개발자센터 키는 2027-06-30까지 쓸 수 있습니다.

1. 키를 `~/.hermes/.env`에 넣습니다.
   ```
   # HUB (provider: hub, 기본)
   NAVER_HUB_API_KEY_ID=...
   NAVER_HUB_API_KEY=...
   # 개발자센터 키를 쓸 경우 (provider: legacy)
   NAVER_CLIENT_ID=...
   NAVER_CLIENT_SECRET=...
   ```
2. 키워드를 검토합니다. 요청당 그룹 5개 제한 때문에 키워드는 5개씩 나눠 조회합니다. HUB 한도는 월 50,000건이라 주 1회 실행은 여유가 충분합니다.
3. 한 번 수동 실행해 데이터랩 웹 화면과 추이를 대조합니다.
   ```bash
   python3 scripts/demand-radar.py --mode api --print-report
   ```
4. `mode: api`로 바꾸고 cron을 등록합니다.
   ```bash
   ./scripts/setup-demand-radar-cron.sh --dry-run
   ./scripts/setup-demand-radar-cron.sh
   ```
