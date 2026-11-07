"""Project Session Memory managing persistent context with canonical path validation, symlink protection, and comprehensive secret redaction."""
import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

SESSION_SCHEMA_VERSION = "1.0"

# Protected operating system directories across platforms
PROTECTED_SYSTEM_DIRS_POSIX = [
    "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/boot", "/dev", "/proc", "/sys", "/root"
]
PROTECTED_SYSTEM_DIRS_WINDOWS = [
    "c:\\windows", "c:\\windows\\system32", "c:\\program files", "c:\\program files (x86)"
]

SECRET_PATTERNS = [
    re.compile(r'(api[_-]?key\s*[:=]\s*[\'"]?)([a-zA-Z0-9_\-]{8,})([\'"]?)', re.IGNORECASE),
    re.compile(r'(bearer\s+)([a-zA-Z0-9_\-\.]{12,})', re.IGNORECASE),
    re.compile(r'(token\s*[:=]\s*[\'"]?)([a-zA-Z0-9_\-]{8,})([\'"]?)', re.IGNORECASE),
    re.compile(r'(password\s*[:=]\s*[\'"]?)([^\s\'"]{4,})([\'"]?)', re.IGNORECASE),
    re.compile(r'(sk-[a-zA-Z0-9]{20,})', re.IGNORECASE)
]

class SecurityPathError(ValueError):
    pass

class ProjectSessionMemory:
    def __init__(self, project_dir: str, allowed_workspace_roots: Optional[List[str]] = None):
        self.project_dir = self.validate_and_canonicalize_path(project_dir, allowed_workspace_roots)
        self.filepath = os.path.join(self.project_dir, "commander_session.json")
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

    @staticmethod
    def validate_and_canonicalize_path(target_path: str, allowed_workspace_roots: Optional[List[str]] = None) -> str:
        """Resolve symbolic links, eliminate traversal dots, and block protected system directories."""
        if not target_path or not str(target_path).strip():
            raise SecurityPathError("Empty project directory path.")

        # Resolve path to canonical absolute form (resolving symlinks)
        p = Path(target_path).resolve()
        canonical_str = str(p)
        canonical_lower = canonical_str.lower()

        # 1. Block protected system directories
        if sys.platform != "win32":
            for s_dir in PROTECTED_SYSTEM_DIRS_POSIX:
                if canonical_lower == s_dir or canonical_lower.startswith(s_dir + "/"):
                    raise SecurityPathError(f"Access denied to protected system directory: {canonical_str}")
        else:
            for w_dir in PROTECTED_SYSTEM_DIRS_WINDOWS:
                if canonical_lower == w_dir or canonical_lower.startswith(w_dir + "\\"):
                    raise SecurityPathError(f"Access denied to protected Windows system directory: {canonical_str}")

        # 2. If workspace root whitelist is enforced, ensure path resides within approved roots
        if allowed_workspace_roots:
            authorized = False
            for root in allowed_workspace_roots:
                root_resolved = Path(root).resolve()
                try:
                    p.relative_to(root_resolved)
                    authorized = True
                    break
                except ValueError:
                    continue
            if not authorized:
                raise SecurityPathError(f"Path '{canonical_str}' escapes approved workspace roots: {allowed_workspace_roots}")

        return canonical_str

    @staticmethod
    def sanitize_secrets(content: str) -> str:
        """Redact sensitive tokens, API keys, passwords, and authorization headers."""
        sanitized = content
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(r'\1[REDACTED_SECRET]\3' if pattern.groups >= 3 else '[REDACTED_SECRET]', sanitized)
        # Fallback simple keyword match
        for kw in ["api_key", "bearer ", "token="]:
            if kw in sanitized.lower() and "[REDACTED" not in sanitized:
                sanitized = "[REDACTED_SECRET_OCCURRENCE]"
        return sanitized

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if loaded.get("version") == SESSION_SCHEMA_VERSION:
                        self.data.update(loaded)
            except Exception:
                # Corrupted file fallback: keep clean session defaults
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
        sanitized = self.sanitize_secrets(content)
        self.data["conversation_history"].append({
            "timestamp": time.time(),
            "role": role,
            "content": sanitized
        })
        self.save()
