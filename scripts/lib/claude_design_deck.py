"""Build Hermes prompt for claude-design lecture deck polish."""
from __future__ import annotations

from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"


def build_claude_design_prompt(
    topic: str,
    stamp: str,
    outline_path: Path,
    base_html_path: Path,
    output_html_path: Path,
    pptx_path: Path,
    preset_name: str = "claude",
) -> str:
    outline_excerpt = ""
    if outline_path.exists():
        text = outline_path.read_text(encoding="utf-8")
        outline_excerpt = text[:4000]

    return f"""claude-design 스킬로 1920×1080 HTML 강의 덱을 제작하세요.

## 과제
- **주제:** {topic}
- **날짜:** {stamp}
- **디자인:** getdesign.md Claude 프리셋 ({preset_name}) — terracotta #D97757, editorial 톤
- **참조:** ~/hermes-content-studio/Getdesign.md, config/design-catalog.yaml

## 입력 (반드시 읽기)
1. 강의 기획: `{outline_path}`
2. 템플릿 HTML (구조·슬라이드 수 참고): `{base_html_path}`
3. PPTX는 이미 생성됨 (내용 일치): `{pptx_path}`

## 출력 (필수)
- **저장 경로:** `{output_html_path}` (정확히 이 경로에 write_file)
- 1920×1080 fixed canvas, viewport scale
- 키보드 네비 (← →), 슬라이드 번호 표시, localStorage 현재 슬라이드
- Cover / Agenda / Body / Closing 슬라이드 유지 (기획 outline 기준)
- CSS variables로 Claude terracotta 팔레트 적용
- AI 슬롭 금지 (그라데이션·글래스모orphism·장식 일러스트)
- 한국어 본문, 기술 용어 영문 병기

## 검증 (claude-design 스킬 Phase 6)
- 파일 존재 확인
- 브라우저/console 오류 없음 (가능 시)
- 완료 시 정확한 파일 경로 보고

## 기획 요약
{outline_excerpt}
"""


def paths_to_json(paths: dict[str, Path], topic: str, stamp: str, preset: str) -> dict:
    return {
        "topic": topic,
        "stamp": stamp,
        "preset": preset,
        "outline": str(paths["outline"]),
        "html": str(paths["html"]),
        "html_base": str(paths.get("html_base", paths["html"])),
        "pptx": str(paths["pptx"]),
    }
