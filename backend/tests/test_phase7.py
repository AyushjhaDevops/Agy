import pytest

from app.services.browser_service import BrowserAgent, BrowserApprovalRequired


def test_external_domains_require_approval(tmp_path) -> None:
    agent = BrowserAgent(str(tmp_path))
    with pytest.raises(BrowserApprovalRequired):
        agent._check_url("https://example.com")


def test_local_domains_are_allowed(tmp_path) -> None:
    agent = BrowserAgent(str(tmp_path))
    agent._check_url("http://localhost:5173/login")
    agent._check_url("http://127.0.0.1:8000")
