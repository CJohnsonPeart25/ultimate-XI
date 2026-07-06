"""One-off: import seed.yaml into the SQLite database via SQLModel.

Safe to re-run — existing players are updated (merge), not duplicated.

    uv run python scripts/seed_db.py
"""
import sys
from pathlib import Path

import yaml
from sqlmodel import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Player, engine, init_db  # noqa: E402

SEED_FILE = Path(__file__).resolve().parent.parent / "seed.yaml"


def main() -> None:
    with SEED_FILE.open(encoding="utf-8") as fh:
        characters = yaml.safe_load(fh)["characters"]

    init_db()
    with Session(engine) as session:
        for name, data in characters.items():
            stat_values = {}
            for category, stats in data.items():
                if category == "synergies":
                    continue
                stat_values.update(stats)
            partners = data.get("synergies", {}).get("link_up_partners", [])
            session.merge(Player(name=name, link_up_partners=partners, **stat_values))
        session.commit()

    print(f"Seeded {len(characters)} players into {engine.url.database}")


if __name__ == "__main__":
    main()
