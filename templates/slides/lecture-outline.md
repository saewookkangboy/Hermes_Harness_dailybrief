# 강의 자료 기획 템플릿

## 기본 정보
- 강의명: {{LECTURE_TITLE}}
- 대상: {{AUDIENCE}}
- 소요: {{DURATION}}분
- 날짜: {{DATE}}

## 학습 목표 (3개)
1. {{LO_1}}
2. {{LO_2}}
3. {{LO_3}}

## 아젠다
| # | 섹션 | 시간 | 슬라이드 수 |
|---|------|------|------------|
| 1 | 오프닝 | 5분 | 2 |
| 2 | 핵심 개념 | 15분 | 8 |
| 3 | 실습/데모 | 20분 | 6 |
| 4 | 사례 | 10분 | 4 |
| 5 | Q&A + 마무리 | 10분 | 2 |

## 슬라이드 상세 (Getdesign.md 적용)

### Cover
- Yellow 배경, 좌측 대형 제목
- 부제: {{SUBTITLE}}
- 날짜/강사명

### Body slides
각 슬라이드:
- proof-object 1개 (다이어그램 | 테이블 | 스크린샷)
- 상단 gray bullet band (프레이밍 2–3줄)
- 발표자 노트 (speaker notes)

### Closing
- Yellow 배경, 핵심 takeaway 3개
- 다음 단계 / 연락처

## 데이터 수집 체크리스트
- [ ] 리서치 브리프 참조 (`content/research/`)
- [ ] 통계/출처 3개 이상
- [ ] 실습 예제 코드/스크린샷
- [ ] FAQ 3개 (AEO용)

## 산출물
- `content/lectures/{{DATE}}_{{SLUG}}_outline.md` — 이 파일
- `content/lectures/{{DATE}}_{{SLUG}}.pptx` — 슬라이드
- `content/lectures/{{DATE}}_{{SLUG}}.html` — HTML deck (선택)
