---
name: content-studio-slides
description: "Getdesign.md 기반 강의 슬라이드: 기획→HTML→pptx 템플릿 제작."
version: 1.1.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [slides, lecture, powerpoint, design, getdesign, education]
    related_skills: [content-pipeline, design-md, powerpoint, claude-design]
---

# Content Studio Slides — 강의 자료 제작

[Getdesign.md](https://getdesign.md/) 디자인 프리셋 + 로컬 `Getdesign.md`를 디자인 시스템으로 사용하여
강의 자료를 기획·HTML·슬라이드(.pptx)까지 생성합니다.

## 빠른 실행

```bash
# 기본: 템플릿 HTML + PPTX (로컬, 빠름)
~/hermes-content-studio/scripts/run-lecture-slides.sh "AEO 실전 가이드" \
  --content-file my-outline.txt --preset claude

# claude-design 연동: PPTX(로컬) + Hermes claude-design HTML(1920×1080) + Notion
~/hermes-content-studio/scripts/run-lecture-slides.sh "AEO 실전 가이드" \
  --content-file my-outline.txt \
  --design-mode claude-design --notion-sync

# 주간 브리프 + claude-design (파이프라인)
LECTURE_DESIGN_MODE=claude-design ~/hermes-content-studio/scripts/run-pipeline.sh

# Telegram Permalink 포함
TELEGRAM_CHAT_ID=8975802496 ~/hermes-content-studio/scripts/run-lecture-slides.sh \
  "AEO 실전" --content-file outline.txt --design-mode claude-design --notion-sync
```

### design-mode 비교

| 모드 | HTML | PPTX | Hermes | Notion |
|------|------|------|--------|--------|
| `basic` (기본) | slide_generator 템플릿 | ✓ | 선택(HERMES_ENHANCE) | 수동 |
| `claude-design` | claude-design 스킬 1920×1080 | ✓ | ✓ | `--notion-sync` 자동 |

설정: `config/lecture-design.yaml`

## 사전 조건

1. `config/design-catalog.yaml` — getdesign.md 프리셋 선택
2. `Getdesign.md` — Content Studio 기본 토큰
3. `content/research/` 최신 브리프 참조 (데이터·출처)
4. `templates/slides/lecture-outline.md` 템플릿
5. `pip install -r requirements.txt` (python-pptx)

## 워크플로우

### Phase 1: 아이디어 기획
출력: `content/lectures/YYYY-MM-DD_{slug}_outline.md`

- 학습 목표 3개
- 아젠다 (시간·슬라이드 수)
- proof-object 목록 (다이어그램/테이블/스크린샷)
- 데이터 수집 체크리스트

### Phase 2: 데이터 수집
- 리서치 브리프에서 관련 인사이트 인용
- 통계/출처 3개 이상 확보
- 실습 예제 (코드 스니펫, 스크린샷 설명)

### Phase 3: HTML 초안
출력: `content/lectures/YYYY-MM-DD_{slug}.html`

Getdesign.md 토큰 적용:
- Primary #111111, Tertiary #FFE500 (cover/closing)
- Pretendard 폰트
- Cover: yellow 배경 + 좌측 대형 제목
- Body: 상단 제목 + gray bullet band + proof-object
- FAQ 섹션 (AEO)

```html
<!-- 슬라이드 구조 예시 -->
<section class="slide cover" style="background:#FFE500">
  <h1>강의 제목</h1>
</section>
<section class="slide body">
  <div class="bullet-band">프레이밍 요약</div>
  <div class="proof-object"><!-- 다이어그램/테이블 --></div>
</section>
```

### Phase 4: claude-design HTML (design-mode=claude-design)
스킬: `claude-design` + `content-studio-slides`

```bash
~/hermes-content-studio/scripts/run-lecture-slides.sh "제목" \
  --content-file outline.txt --design-mode claude-design --notion-sync
```

1. `generate-lecture-slides.py` — outline + PPTX + `_base.html`
2. `polish-lecture-claude-design.sh` — Hermes claude-design 1920×1080 HTML
3. `archive-to-notion.sh` — outline + final HTML Notion sync

### Phase 5: 슬라이드 제작 (.pptx) — basic 모드
스킬: `powerpoint` 사용

1. 기존 템플릿 참조:
   - `~/Desktop/교육_강의_자료/02_강의안_교육자료/` 내 .pptx
   - 또는 `~/Desktop/` AIC_Seoul, AX전환 슬라이드 스타일

2. Getdesign.md 규칙 적용:
   - Cover: Yellow(#FFE500) 배경, Black 제목
   - Body: White 배경, 상단 룰, gray band
   - Table: thin gray borders, compact text
   - Footer: 우하단 페이지 번호 (gray, small)

3. 출력: `content/lectures/YYYY-MM-DD_{slug}.pptx`

```bash
# markitdown으로 기존 슬라이드 분석 (참조용)
python -m markitdown ~/Desktop/교육_강의_자료/02_강의안_교육자료/*.pptx
```

## 슬라이드 레이아웃 체크리스트

- [ ] Cover: Yellow + Black + 좌측 세로 바
- [ ] Body: proof-object 1개/슬라이드
- [ ] Gray bullet band (상단 8–14%)
- [ ] 페이지 번호 (우하단)
- [ ] Red accent 스파링 사용
- [ ] Closing: Yellow + takeaway 3개

## Anti-patterns (금지)

- 모든 슬라이드 sparse bullet
- 그라데이션·장식 일러스트
- 키노트형 중앙 정렬
- Yellow/Red 과다

## 발표자 노트

각 body 슬라이드에 speaker notes 포함:
- 핵심 메시지 1문장
- 전환 멘트
- 예상 Q&A 1개
