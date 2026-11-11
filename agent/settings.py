import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv("GIGBID_STATE_DIR") or ROOT / ".state")


@lru_cache
def settings() -> dict:
    return yaml.safe_load((ROOT / "agent/config.yaml").read_text(encoding="utf-8"))


@lru_cache
def policy() -> dict:
    path = Path(os.getenv("GIGBID_POLICY") or ROOT / "data/policy_pack/local.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))

