---
version: alpha
name: Content Studio
description: 마케팅·교육 콘텐츠 스튜디오 비주얼 시스템 — SEO/AEO 블로그, 인스타그램, 링크드인, 강의 슬라이드 통합 디자인
colors:
  primary: "#111111"
  secondary: "#666666"
  tertiary: "#FFE500"
  accent: "#E60012"
  neutral: "#F7F7F7"
  surface: "#FFFFFF"
  border: "#D9D9D9"
typography:
  h1:
    fontFamily: Pretendard
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  h2:
    fontFamily: Pretendard
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body-md:
    fontFamily: Pretendard
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0"
  caption:
    fontFamily: Pretendard
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "0"
rounded:
  sm: 4px
  md: 8px
  lg: 16px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: 12px
  button-primary-hover:
    backgroundColor: "#333333"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: 12px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 16px
  callout:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 12px
  slide-cover:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.primary}"
    typography: h1
---

## Overview

Content Studio 디자인 시스템은 **실무형·문서형·밀도 높은** 비주얼을 기본으로 합니다.
키노트형 장식보다 **전략 메모·컨설팅 제안서·교육 자료**에 가까운 톤을 유지합니다.

적용 대상:
- SEO/AEO 블로그 HTML 초안
- 인스타그램 캡션·캐러셀 구조
- 링크드인 뉴스피드 포스트
- 강의 슬라이드 (.pptx, HTML deck)
- 리서치 브리프 문서

## Colors

- **Primary (#111111):** 제목, 본문, 핵심 텍스트
- **Secondary (#666666):** 부제, 캡션, 메타 정보, 페이지 번호
- **Tertiary (#FFE500):** 커버·클로징 슬라이드, 방향 강조 화살표 (과용 금지)
- **Accent (#E60012):** KPI·위험·핵심 강조 (스파링하게)
- **Neutral (#F7F7F7):** 상단 밴드, 콜아웃 배경, 테이블 헤더
- **Surface (#FFFFFF):** 본문 슬라이드·블로그 본문 배경
- **Border (#D9D9D9):** 테이블·구분선·다이어그램 스캐폴딩

금지: 그라데이션, 다색 팔레트, 장식용 일러스트, 이모지 남용, 글로시 SaaS 카드

## Typography

- **제목:** Pretendard Bold/Medium, 20–28pt (슬라이드), 2rem (웹)
- **본문:** Pretendard Regular, 9–14pt (슬라이드), 1rem (웹), 줄간격 1.5–1.6
- **캡션/출처:** 0.75rem, Secondary 색상
- **숫자 강조:** 작은 회색 페이지 번호 (슬라이드 하단 우측)

한국어 제목 + 필요 시 영문 용어 병기. 본문은 짧은 문단·번호 목록·컴팩트 불릿 선호.

## Layout

### 슬라이드 레이아웃 패밀리
1. **Cover:** 전체 Tertiary 배경, 좌측 대형 제목, 좌측 세로 검정 바
2. **Agenda:** 흰 배경, 좌측 정렬 목차 + 페이지 번호
3. **Body (Proof-object):** 상단 제목 + 가로 룰, 회색 상단 밴드, 중앙 다이어그램/테이블/스크린샷
4. **Table/Appendix:** 얇은 회색 테두리 그리드, 밀도 높은 한국어 텍스트
5. **Closing:** Cover와 동일한 Yellow/Black 정체성

### 웹/HTML 레이아웃
- 최대 너비 720px (블로그), 1080px (강의 HTML deck)
- H1 → H2 → 본문 → CTA 순서
- FAQ 섹션 (AEO): `<section itemscope itemtype="https://schema.org/FAQPage">`
- 메타: title, description, og:image, canonical URL 필수

### 소셜 미디어
- **인스타그램:** 1080×1080 또는 1080×1350, 첫 슬라이드=훅, 마지막=CTA
- **링크드인:** 1300자 이내, 첫 2줄=훅, 불릿 3–5개, 해시태그 3–5개

## Components

- **Title block:** 상단 제목 + 얇은 가로 룰 (body 슬라이드 필수)
- **Gray bullet band:** 상단 8–14% 영역, 프레이밍 요약 2–3줄
- **Callout card:** Neutral 배경, rounded-md, 좌측 정렬 텍스트
- **Evidence panel:** 스크린샷/사진을 rounded-lg 컨테이너에 배치
- **Table:** 얇은 Border, Neutral 헤더, 컴팩트 텍스트

## Do's and Don'ts

**Do:**
- 슬라이드마다 하나의 proof-object (다이어그램, 테이블, 증거 이미지)
- SEO: H1 1개, H2 구조화, 내부 링크, alt 텍스트
- AEO: FAQ 스키마, 직접 답변형 첫 문단, 구조화 데이터
- 강의 자료: 학습목표 → 핵심개념 → 실습 → 요약 → 다음 단계

**Don't:**
- 모든 슬라이드를 sparse bullet로 채우기
- Yellow/Red 과다 사용
- 장식용 아이콘·일러스트 추가
- 키노트형 중앙 정렬 남용
