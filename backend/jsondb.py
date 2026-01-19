# backend/jsondb.py

import json, os, threading
from datetime import datetime

lock = threading.Lock()

class JSONDatabase:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, name):
        return os.path.join(self.folder, f"{name}.json")

    def _read(self, name):
        path = self._path(name)
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write(self, name, data):
        with lock:
            temp = self._path(name) + ".tmp"
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp, self._path(name))

    # -----------------------------------------------------
    # INSERT — keeps given ID or auto-generates one
    # -----------------------------------------------------
    def insert(self, name, record):
        data = self._read(name)

        # If record has no ID, auto-assign next ID
        if "id" not in record:
            next_id = max((r.get("id", 0) for r in data), default=0) + 1
            record["id"] = next_id

        # Always add timestamp
        record["created_at"] = datetime.utcnow().isoformat() + "Z"

        data.append(record)
        self._write(name, data)

        return record

    # -----------------------------------------------------
    # FIND ALL
    # -----------------------------------------------------
    def find_all(self, name, filter_fn=None):
        data = self._read(name)
        return list(filter(filter_fn, data)) if filter_fn else data

    # -----------------------------------------------------
    # FIND ONE
    # -----------------------------------------------------
    def find_one(self, name, filter_fn):
        for r in self._read(name):
            if filter_fn(r):
                return r
        return None

    # -----------------------------------------------------
    # UPDATE RECORDS
    # -----------------------------------------------------
    def update(self, name, filter_fn, updater_fn):
        data = self._read(name)
        updated = False

        for i, r in enumerate(data):
            if filter_fn(r):
                updated_record = updater_fn(r)
                updated_record["updated_at"] = datetime.utcnow().isoformat() + "Z"
                data[i] = updated_record
                updated = True

        if updated:
            self._write(name, data)

        return updated

    # -----------------------------------------------------
    # DELETE RECORDS
    # -----------------------------------------------------
    def delete(self, name, filter_fn):
        data = self._read(name)
        new_data = [r for r in data if not filter_fn(r)]
        self._write(name, new_data)
        return True
