import os
import json
import shutil
import tempfile
import threading

# Global file lock to ensure atomic, thread-safe JSON database updates
file_lock = threading.Lock()

def load_json_file(filename, default):
    with file_lock:
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"JSON Corruption detected in {filename}: {str(e)}")
                try:
                    backup_name = f"{filename}.corrupted"
                    shutil.copy(filename, backup_name)
                    print(f"Backed up corrupted file to {backup_name}")
                    os.remove(filename)
                except Exception as copy_err:
                    print(f"Failed to backup corrupted file {filename}: {str(copy_err)}")
        return default

def save_json_file(filename, data):
    with file_lock:
        dir_name = os.path.dirname(filename) or "."
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        # Create temp file in same directory for atomic replace
        fd, tmp_filepath = tempfile.mkstemp(dir=dir_name, prefix="temp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, indent=4)
            os.replace(tmp_filepath, filename)
        except Exception as e:
            print(f"Error saving file {filename}: {str(e)}")
            if os.path.exists(tmp_filepath):
                try:
                    os.remove(tmp_filepath)
                except Exception:
                    pass
            raise e
