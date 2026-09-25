# Phase 8: Deep Git Integration

Phase 8 adds comprehensive Git functionality with approval gates for dangerous operations.

## Features

**Git Service:**
- Status (branch, ahead/behind, changed files)
- Diff (file-level diffs with insertions/deletions)
- Log (commit history)
- Branches (local and remote)
- Checkout
- Add (stage files)
- Commit (approval required)
- Stash
- Show (inspect refs)
- Blame (line-by-line history)
- Reset (approval required)
- Rebase (approval required)

**Safety:**
- Commit requires HTTP 428 approval before execution
- Reset requires HTTP 428 approval
- Rebase requires HTTP 428 approval
- No automated push or force operations

**API Endpoints:**
- `GET /api/v1/git/status`
- `GET /api/v1/git/diff?file=...`
- `GET /api/v1/git/log?n=20`
- `GET /api/v1/git/branches`
- `POST /api/v1/git/checkout`
- `POST /api/v1/git/add`
- `POST /api/v1/git/commit` (requires approval)
- `POST /api/v1/git/stash`
- `GET /api/v1/git/show/{ref}`
- `GET /api/v1/git/blame/{file}`
- `POST /api/v1/git/reset` (requires approval)
- `POST /api/v1/git/rebase` (requires approval)

**UI:**
- Git panel with branch display
- Status and sync info
- Changed files listing
- Commit interface with approval checkbox
- Command history

Phase 8 is complete. Stop here.
