import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class ConversationStore:
    def __init__(self, database_url: str) -> None:
        path = database_url.removeprefix("sqlite:///")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                );
                """
            )

    def ensure_conversation(self, conversation_id: str | None, project_id: str | None) -> str:
        identifier = conversation_id or str(uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO conversations (id, project_id, created_at) VALUES (?, ?, ?)",
                (identifier, project_id, datetime.now(timezone.utc).isoformat()),
            )
        return identifier

    def add_message(self, conversation_id: str, role: str, content: str, model: str | None) -> str:
        identifier = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, content, model, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (identifier, conversation_id, role, content, model, datetime.now(timezone.utc).isoformat()),
            )
        return identifier

    def get_messages(self, conversation_id: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid",
                (conversation_id,),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]
