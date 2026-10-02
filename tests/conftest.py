import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def isolated_topics(tmp_path, monkeypatch):
    """content/topics · lens feedback을 tmp로 격리."""
    monkeypatch.setenv("HERMES_TOPICS_ROOT", str(tmp_path / "topics"))
    monkeypatch.setenv("HERMES_TOPIC_FEEDBACK", str(tmp_path / "feedback.json"))
    return tmp_path
