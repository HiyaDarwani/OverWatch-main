import json
from datetime import datetime, timezone
from pathlib import Path


class ModelRegistry:
    """Small JSON model registry supporting activation and metrics."""

    def __init__(self, registry_path="models/registry.json"):
        self.registry_path = Path(registry_path)
        self.registry = self._load()

    def _load(self):
        if not self.registry_path.exists():
            return {"models": {}, "active": None}
        with self.registry_path.open(encoding="utf-8") as registry_file:
            value = json.load(registry_file)
        if not isinstance(value, dict) or not isinstance(value.get("models", {}), dict):
            raise ValueError("Invalid model registry format")
        value.setdefault("active", None)
        return value

    def _save(self):
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as registry_file:
            json.dump(self.registry, registry_file, indent=2)
        temporary_path.replace(self.registry_path)

    def register_model(self, name, path, metadata=None):
        if not name or not path:
            raise ValueError("model name and path are required")
        self.registry["models"][name] = {
            "path": str(path),
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "metrics": {},
        }
        self._save()

    def set_active(self, name):
        if name not in self.registry["models"]:
            raise ValueError(f"Model {name} not found in registry")
        self.registry["active"] = name
        self._save()

    def get_active_model_path(self):
        active = self.registry.get("active")
        return self.registry["models"].get(active, {}).get("path")

    def update_metrics(self, name, metrics):
        if name not in self.registry["models"]:
            raise ValueError(f"Model {name} not found in registry")
        self.registry["models"][name]["metrics"].update(metrics)
        self._save()
