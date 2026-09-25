# Phase 7: Playwright browser testing

Phase 7 adds a BrowserAgent and API for testing approved local applications. It supports navigation, inspection, click/type/select actions, screenshots, console errors, network failures, visible-error detection, extracted text, timestamps, URLs, and evidence files.

Only `localhost` and `127.0.0.1` are approved by default. External domains require `allow_external: true`, which should be treated as an explicit user permission.

Install the optional browser dependency:

```bash
pip install -r backend/requirements-browser.txt
playwright install chromium
```

Run a test with `POST /api/v1/browser/tests`. Evidence is written under `.localforge/browser-evidence` below the configured projects root. The policy is application-level domain validation; it is not network isolation.
