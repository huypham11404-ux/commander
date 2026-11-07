import pytest
import os
import tempfile
from pathlib import Path
from commander.storage.session_memory import ProjectSessionMemory, SecurityPathError

def test_canonical_path_blocks_system_directory():
    # Attempting to set project_dir to /etc or /bin should raise SecurityPathError
    with pytest.raises(SecurityPathError):
        ProjectSessionMemory("/etc")
    with pytest.raises(SecurityPathError):
        ProjectSessionMemory("/bin/subpath")

def test_dot_dot_traversal_resolution():
    with tempfile.TemporaryDirectory() as base_tmp:
        safe_subdir = os.path.join(base_tmp, "user_project")
        os.makedirs(safe_subdir, exist_ok=True)

        # Relative path with dots resolving inside allowed workspace
        traversal_path = os.path.join(safe_subdir, "..", "user_project")
        mem = ProjectSessionMemory(traversal_path, allowed_workspace_roots=[base_tmp])
        assert mem.project_dir == str(Path(safe_subdir).resolve())

def test_workspace_root_escape_blocked():
    with tempfile.TemporaryDirectory() as approved_root:
        with tempfile.TemporaryDirectory() as unapproved_root:
            # Trying to escape approved_root to unapproved_root should fail
            with pytest.raises(SecurityPathError):
                ProjectSessionMemory(unapproved_root, allowed_workspace_roots=[approved_root])

def test_symlink_escape_blocked():
    with tempfile.TemporaryDirectory() as approved_root:
        outside_target = tempfile.mkdtemp()
        symlink_path = os.path.join(approved_root, "sneaky_symlink")
        try:
            os.symlink(outside_target, symlink_path)
            with pytest.raises(SecurityPathError):
                ProjectSessionMemory(symlink_path, allowed_workspace_roots=[approved_root])
        finally:
            if os.path.exists(symlink_path):
                os.remove(symlink_path)
