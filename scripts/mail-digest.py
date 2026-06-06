#!/usr/bin/env python3
"""Email digest for personal-assistant — Mail.app / Himalaya / IMAP."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
OUTPUT_DIR = WORKDIR / "content" / "personal"


def slugify(s: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower())
    slug = re.sub(r"[-\s]+", "-", s).strip("-")[:max_len]
    return slug or "mail-digest"


def decode_mime(s: str) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for part, enc in parts:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


def fetch_mailapp(max_messages: int = 15) -> list[dict]:
    script = f'''
    set maxN to {max_messages}
    set outLines to {{}}
    tell application "Mail"
        set msgList to messages of inbox
        set n to count of msgList
        if n > maxN then set n to maxN
        repeat with i from 1 to n
            set m to item i of msgList
            set subj to subject of m
            set snd to sender of m
            set rcv to date received of m as string
            set prev to content of m
            if length of prev > 400 then set prev to text 1 thru 400 of prev
            set end of outLines to subj & "|||" & snd & "|||" & rcv & "|||" & prev
        end repeat
    end tell
    return outLines
    '''
    try:
        raw = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return [{"error": "Mail.app 응답 시간 초과 — 시스템 설정 > 개인정보 > 자동화에서 터미널/Cursor에 Mail 접근 허용, 또는 himalaya IMAP 설정"}]
    except FileNotFoundError as e:
        return [{"error": str(e)}]

    if raw.returncode != 0:
        err = (raw.stderr or raw.stdout or "Mail.app 오류").strip()
        return [{"error": err}]

    messages = []
    for line in raw.stdout.strip().split("\n"):
        if "|||" not in line:
            continue
        parts = line.split("|||", 3)
        if len(parts) < 4:
            continue
        messages.append({
            "subject": parts[0].strip(),
            "from": parts[1].strip(),
            "date": parts[2].strip(),
            "preview": parts[3].strip(),
        })
    return messages


def fetch_himalaya(max_messages: int = 15) -> list[dict]:
    try:
        raw = subprocess.run(
            ["himalaya", "envelope", "list", "--page-size", str(max_messages)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return [{"error": "himalaya CLI 미설치"}]
    if raw.returncode != 0:
        return [{"error": raw.stderr or "himalaya 실패"}]

    messages = []
    for line in raw.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("|---"):
            continue
        # id flags subject from date
        m = re.match(r"^\s*(\d+)\s+\S*\s+(.+?)\s{2,}(.+?)\s{2,}(\S.+)$", line)
        if m:
            messages.append({
                "id": m.group(1),
                "flags": "",
                "subject": m.group(2).strip(),
                "from": m.group(3).strip(),
                "date": m.group(4).strip(),
                "preview": "",
            })
    return messages


def format_digest(messages: list[dict], *, max_messages: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 이메일 다이제스트",
        f"**일시:** {today}",
        f"**건수:** {len([m for m in messages if 'error' not in m])}",
        "",
    ]
    if messages and "error" in messages[0]:
        lines.extend(["## ⚠️ 오류", "", messages[0]["error"], ""])
        lines.append("설정: `config/personal-tasks.yaml` · Himalaya 또는 Mail.app")
        return "\n".join(lines)

    lines.append("## 받편함 요약")
    lines.append("")
    for i, m in enumerate(messages[:max_messages], 1):
        subj = m.get("subject", "(제목 없음)")
        sender = m.get("from", "?")
        date = m.get("date", "")
        preview = m.get("preview", "")
        lines.append(f"### {i}. {subj}")
        lines.append(f"- **발신:** {sender}")
        lines.append(f"- **일시:** {date}")
        if preview:
            prev = re.sub(r"\s+", " ", preview)[:300]
            lines.append(f"- **미리보기:** {prev}")
        lines.append("")

    lines.extend([
        "## 액션 아이템 (Codex/Hermes 후처리용)",
        "",
        "- [ ] 긴급 회신 필요 메일 확인",
        "- [ ] follow-up 일정 정리",
        "",
        "_`/personal 이메일 액션 아이템 정리해줘` 로 Codex 심화 분석 가능_",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=15)
    parser.add_argument("--backend", choices=["mailapp", "himalaya", "auto"], default="auto")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-o", "--output", help="Output markdown path")
    args = parser.parse_args()

    backend = args.backend
    if backend == "auto":
        backend = "himalaya" if shutil.which("himalaya") else "mailapp"

    if backend == "himalaya":
        messages = fetch_himalaya(args.max)
    else:
        messages = fetch_mailapp(args.max)

    digest = format_digest(messages, max_messages=args.max)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = Path(args.output) if args.output else OUTPUT_DIR / f"{today}_mail-digest.md"
    out_path.write_text(digest, encoding="utf-8")

    if args.json:
        print(json.dumps({"path": str(out_path), "count": len(messages), "backend": backend}, ensure_ascii=False))
    else:
        print(str(out_path))
        print("")
        print(digest[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
