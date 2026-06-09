import os
import re
import shutil
import stat
import uuid
from typing import Tuple
from git import Repo
from src.utils.config import settings

def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parses a public GitHub repository URL and returns (owner, repo_name).
    Raises ValueError if the URL is not a valid public GitHub URL.
    """
    # Clean the URL
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
        
    # Pattern to match: https://github.com/owner/repo
    pattern = r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)$"
    match = re.match(pattern, url)
    if not match:
        raise ValueError("Invalid public GitHub repository URL structure.")
        
    owner, repo_name = match.groups()
    return owner, repo_name

def _handle_readonly(func, path, exc_info):
    """
    Error handler for shutil.rmtree on Windows.
    Clears the read-only bit and retries removal.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        # If still failing, let the outer exception propagate
        pass

def cleanup_workspace(dir_path: str) -> None:
    """
    Safely deletes the cloned repository directory.
    Employs read-only bit clearing helper for Windows environments.
    """
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path, onerror=_handle_readonly)
        except Exception as e:
            # Fallback check or log warning
            print(f"Warning: Failed to fully clean up workspace {dir_path}: {e}")

class CloneService:
    @staticmethod
    def clone_repository(url: str) -> Tuple[str, str, str]:
        """
        Clones a public github repository into a unique subdirectory under TEMP_DIR.
        Returns:
            Tuple[str, str, str]: (local_directory_path, repo_owner, repo_name)
        """
        owner, repo_name = parse_github_url(url)
        
        # Ensure target TEMP_DIR exists
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        
        # Create a unique random directory name to avoid collision
        unique_id = uuid.uuid4().hex
        target_dir = os.path.join(settings.TEMP_DIR, f"{owner}_{repo_name}_{unique_id}")
        
        try:
            # Clone only the latest commit to optimize network I/O
            Repo.clone_from(url, target_dir, depth=1)
            return target_dir, owner, repo_name
        except Exception as e:
            # Ensure cleanup of partial clones
            cleanup_workspace(target_dir)
            raise RuntimeError(f"Git clone failed: {str(e)}")
