# Meta Ads 루프 — 피로도 감시 · 주간 리포트

조회 전용 루프 두 개입니다. 광고 계정의 예산·입찰·오디언스·상태를 바꾸는 코드는 없습니다.

| 루프 | 시각 (KST) | 하는 일 | 게시 |
|---|---|---|---|
| `meta-fatigue` | 매일 09:00 | 최근 7일 vs 직전 7일, 광고세트별 노출·빈도·CTR 변화 판정 | 교체 검토 대상이 있을 때만 Slack 홈 채널 |
| `meta-weekly` | 월 09:05 | 계정 KPI(지출·CTR·CPC·CPM·전환·CPA)와 광고세트 표 | Slack 한 줄 + `content/ads/` 리포트 → Notion `Meta Ads Weekly` |

## 판정 규칙

세 조건을 **모두** 만족하면 "교체 검토"입니다. 값은 `config/meta-ads.yaml` `fatigue`에서 바꿉니다.

- 최근 7일 노출 ≥ 5,000
- 최근 7일 빈도 ≥ 3.5
- 직전 7일 대비 CTR 변화 ≤ -20%

## 지금 상태: 샘플 모드

`mode: sample`에서는 `tests/fixtures/meta/insights_sample.json`(합성 데이터)을 읽습니다. 산출물 파일명이 `_sample_`로 시작해 Notion 아카이브에서 빠지고, cron도 등록되지 않습니다.

```bash
python3 scripts/meta-ads.py fatigue --mode sample
python3 scripts/meta-ads.py weekly --mode sample --print-report
./scripts/meta-ads-eval.sh
```

## 실계정 연결 (토큰 준비 후)

1. Meta 비즈니스 관리자에서 시스템 사용자를 만들고 광고 계정에 **조회 권한만** 부여한 뒤 `ads_read` 권한 토큰을 발급합니다. 앱의 Marketing API 접근 등급도 확인합니다.
2. `~/.hermes/.env`에 추가합니다 (레포에는 넣지 않습니다).
   ```
   META_ACCESS_TOKEN=...
   META_AD_ACCOUNT_ID=123456789012345
   ```
3. 전환 기준이 리드가 아니면 `conversion_action_types`를 바꿉니다 (예: 구매는 `offsite_conversion.fb_pixel_purchase`).
4. 한 번 수동 실행해 수치를 광고 관리자와 대조합니다.
   ```bash
   python3 scripts/meta-ads.py weekly --mode api --print-report
   ```
5. `config/meta-ads.yaml`의 `mode`를 `api`로 바꾸고 cron을 등록합니다. 등록 스크립트는 실제 조회 1회로 토큰을 확인한 뒤 등록합니다.
   ```bash
   ./scripts/setup-meta-ads-cron.sh --dry-run
   ./scripts/setup-meta-ads-cron.sh
   ```

API 버전은 `config/meta-ads.yaml` `api.version`(2026-09 기준 v25.0)입니다. 빈도 데이터 보관 기간이 6개월로 줄어 7일 창 비교에는 영향이 없습니다.

광고 성과 파일(`content/ads/`)은 `.gitignore`에 있어 공개 레포에 올라가지 않습니다.
