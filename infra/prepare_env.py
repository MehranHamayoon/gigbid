"""Seed private local settings without putting credentials in the repository."""
from pathlib import Path
from secrets import token_hex

destination = Path(".env")
if destination.exists():
    raise SystemExit("An .env already exists. Update it directly.")
settings = {"APP_SECRET_KEY": token_hex(32), "GIGBID_INTERNAL_TOKEN": token_hex(32),
            "POSTGRES_PASSWORD": token_hex(24), "GIGBID_DEMO_ACCESS": "1"}
destination.write_text("".join(f"{key}={value}\n" for key, value in settings.items()), encoding="utf-8")
print("Created .env with local secrets. It is ignored by Git.")
