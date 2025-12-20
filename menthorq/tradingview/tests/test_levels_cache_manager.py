import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

# Charger dynamiquement levels_cache_manager sans paquet installé
def load_levels_cache_module():
    module_path = Path(__file__).resolve().parents[1] / "levels_cache_manager.py"
    spec = importlib.util.spec_from_file_location("levels_cache_manager", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # nécessaire pour dataclass
    spec.loader.exec_module(module)  # type: ignore
    return module

levels_cache_manager = load_levels_cache_module()
CACHE_DIR = levels_cache_manager.CACHE_DIR
update_cache_from_event = levels_cache_manager.update_cache_from_event
get_levels = levels_cache_manager.get_levels


def test_update_cache_from_event(tmp_path, monkeypatch):
    monkeypatch.setattr(levels_cache_manager, "CACHE_DIR", tmp_path)

    event = {
        "name": "levels_snapshot",
        "_exec_symbol": "ESZ2025",
        "time": "2025-09-28T15:30:00Z",
        "raw": {
            "levels": {
                "HVL": "5365.25",
                "GammaFlip": "5340.75",
                "PutWall": "5300",
            }
        },
    }

    snapshot = update_cache_from_event(event)
    assert snapshot is not None
    path = tmp_path / "ESZ2025.json"
    assert path.exists()

    data = json.loads(path.read_text())
    assert data["symbol"] == "ESZ2025"
    assert "hvl" in data["levels"]
    assert data["levels"]["hvl"] == 5365.25

    cached_levels = get_levels("ESZ2025")
    assert cached_levels["hvl"] == 5365.25
