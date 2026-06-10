import os
from typing import Dict, Any, List

IGNORED_DIRS = {"node_modules", "dist", "build", ".git", "coverage", ".next"}

def is_binary_file(filepath: str) -> bool:
    """
    Checks if a file is binary by reading its first chunk and scanning for null bytes.
    Also employs a fast check based on common binary file extensions.
    """
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    # Common binary file extensions
    binary_extensions = {
        # Databases / state files
        ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".sqlitedb",
        # Images & Media
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf",
        # Audio / Video
        ".mp3", ".mp4", ".wav", ".avi", ".mkv", ".mov", ".flac",
        # Fonts
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        # Archives & Executables
        ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll", ".so", ".dylib", ".bin", ".msi",
        # Compiled binaries
        ".pyc", ".pyo", ".pyd", ".class", ".o", ".a", ".lib",
        # Next.js / Build / Cache binaries
        ".sst", ".meta", ".body", ".cache"
    }
    
    if ext in binary_extensions:
        return True
        
    try:
        with open(filepath, 'rb') as f:
            # Check up to 64KB for null bytes, in case header has no nulls but body does
            chunk = f.read(65536)
            return b'\x00' in chunk
    except Exception:
        # If we cannot read it, treat as binary/inaccessible to skip line-counting
        return True

def count_lines(filepath: str) -> int:
    """
    Safely counts the lines in a text file. Handles encoding fallbacks.
    """
    try:
        # Read file with utf-8, ignore decoding errors
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        # Fallback to Latin-1 if UTF-8 fails completely
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

class FileScanner:
    @staticmethod
    def scan(root_dir: str) -> List[Dict[str, Any]]:
        """
        Recursively scans root_dir, gathers metrics on files, and ignores excluded folders.
        Returns:
            List[Dict[str, Any]]: List of file records containing path, extension, size, and line_count.
        """
        file_records = []
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Prune ignored directories in-place to prevent os.walk from entering them
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
                
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue  # Skip files that can't be sized (e.g. broken symlinks)
                
                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                
                line_count = 0
                if not is_binary_file(full_path):
                    line_count = count_lines(full_path)
                
                file_records.append({
                    "path": rel_path,
                    "extension": ext,
                    "size": size,
                    "line_count": line_count
                })
                
        return file_records
