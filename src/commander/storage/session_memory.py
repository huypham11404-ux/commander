"""Project Session Memory managing persistent context without logging secrets."""
import os
import json
import time
from typing import Dict, Any, Optional

SESSION_SCHEMA_VERSION = "1.0"

class ProjectSessionMemory:
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.filepath = os.path.join(project_dir, "commander_session.json")
        self.data: Dict[str, Any] = {
            "version": SESSION_SCHEMA_VERSION,
            "created_at": time.time(),
            "updated_at": time.time(),
            "project_goals": {},
            "musical_context": {
                "key": None,
                "bpm": None,
                "genre": None
            },
            "conversation_history": [],
            "user_preferences": {}
        }
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if loaded.get("version") == SESSION_SCHEMA_VERSION:
                        self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        os.makedirs(self.project_dir, exist_ok=True)
        self.data["updated_at"] = time.time()
        tmp = self.filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, self.filepath)

    def update_musical_context(self, key: Optional[str] = None, bpm: Optional[float] = None, genre: Optional[str] = None):
        if key is not None:
            self.data["musical_context"]["key"] = key
        if bpm is not None:
            self.data["musical_context"]["bpm"] = bpm
        if genre is not None:
            self.data["musical_context"]["genre"] = genre
        self.save()

    def append_message(self, role: str, content: str):
        # Sanitize against accidental secret logging
        sanitized = content
        for secret_kw in ["api_key", "bearer ", "token="]:
            if secret_kw in sanitized.lower():
                sanitized = "[REDACTED_SECRET_OCCURRENCE]"

        self.data["conversation_history"].append({
            "timestamp": time.time(),
            "role": role,
            "content": sanitized
        })
        self.save()
