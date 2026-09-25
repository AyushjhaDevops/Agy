from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4


class BrowserApprovalRequired(PermissionError):
    pass


@dataclass
class BrowserEvidence:
    screenshots: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    network_failures: list[str] = field(default_factory=list)
    visible_errors: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)


@dataclass
class BrowserTestResult:
    id: str
    url: str
    status: str
    actions: list[dict[str, Any]]
    evidence: BrowserEvidence
    error: str | None = None
    duration: float = 0.0


class BrowserAgent:
    """Playwright browser tester with an application-level approved-domain gate."""

    def __init__(self, evidence_root: str, approved_domains: set[str] | None = None) -> None:
        self.evidence_root = Path(evidence_root).expanduser().resolve()
        self.approved_domains = approved_domains or {"localhost", "127.0.0.1"}
        self._pages: dict[str, Any] = {}

    def _check_url(self, url: str, allow_external: bool = False) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Browser URL must be an absolute HTTP(S) URL")
        if parsed.hostname not in self.approved_domains and not allow_external:
            raise BrowserApprovalRequired(f"External domain requires explicit permission: {parsed.hostname}")

    async def run(self, url: str, actions: list[dict[str, Any]] | None = None, allow_external: bool = False, headless: bool = True) -> BrowserTestResult:
        self._check_url(url, allow_external)
        test_id = str(uuid4())
        evidence_dir = self.evidence_root / test_id
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence = BrowserEvidence()
        action_results: list[dict[str, Any]] = []
        started = time.perf_counter()
        result: BrowserTestResult
        try:
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise RuntimeError("Playwright is required. Install it and run 'playwright install chromium'.") from exc
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=headless)
                context = await browser.new_context()
                page = await context.new_page()
                self._pages[test_id] = page
                page.on("console", lambda message: evidence.console_errors.append(message.text) if message.type == "error" else None)
                page.on("requestfailed", lambda request: evidence.network_failures.append(f"{request.method} {request.url}: {request.failure}"))
                await page.goto(url, wait_until="domcontentloaded")
                await self._record(page, evidence, evidence_dir)
                for action in actions or []:
                    action_results.append(await self._action(page, action, evidence, evidence_dir))
                evidence.urls.append(page.url)
                visible = await page.locator("body").inner_text()
                evidence.visible_errors.extend(re.findall(r"(?im)^.*(?:error|failed|failure|invalid).*$", visible))
                status = "FAILED" if evidence.console_errors or evidence.network_failures or evidence.visible_errors else "COMPLETED"
                result = BrowserTestResult(test_id, url, status, action_results, evidence, duration=time.perf_counter() - started)
                await context.close()
                await browser.close()
        except Exception as exc:
            result = BrowserTestResult(test_id, url, "FAILED", action_results, evidence, str(exc), time.perf_counter() - started)
        finally:
            self._pages.pop(test_id, None)
            result_payload = locals().get("result")
            if result_payload is None:
                result_payload = BrowserTestResult(test_id, url, "FAILED", action_results, evidence, "Browser test failed", time.perf_counter() - started)
            (evidence_dir / "result.json").write_text(json.dumps(asdict(result_payload), default=str, indent=2), encoding="utf-8")
        return result

    async def _action(self, page: Any, action: dict[str, Any], evidence: BrowserEvidence, evidence_dir: Path) -> dict[str, Any]:
        kind = action.get("type")
        target = action.get("selector")
        if kind == "navigate":
            self._check_url(action["url"], action.get("allow_external", False)); await page.goto(action["url"], wait_until="domcontentloaded")
        elif kind == "click": await page.locator(target).click()
        elif kind == "type": await page.locator(target).fill(str(action.get("value", "")))
        elif kind == "select": await page.locator(target).select_option(str(action["value"]))
        elif kind == "screenshot": await self._record(page, evidence, evidence_dir, action.get("name", "action"))
        elif kind == "extract": return {"type": kind, "text": await page.locator(target).inner_text()}
        elif kind == "inspect": return {"type": kind, "text": await page.locator("body").inner_text()}
        else: raise ValueError(f"Unsupported browser action: {kind}")
        evidence.urls.append(page.url)
        return {"type": kind, "selector": target, "status": "completed"}

    async def _record(self, page: Any, evidence: BrowserEvidence, directory: Path, name: str = "page") -> None:
        filename = f"{len(evidence.screenshots):02d}-{re.sub(r'[^a-zA-Z0-9_-]', '-', name)}.png"
        await page.screenshot(path=str(directory / filename), full_page=True)
        evidence.screenshots.append(str(directory / filename))
        evidence.timestamps.append(datetime.now(timezone.utc).isoformat())

    async def cancel(self, test_id: str) -> bool:
        page = self._pages.get(test_id)
        if page is None: return False
        await page.close()
        return True
