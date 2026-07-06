from pathlib import Path

from sqlalchemy import JSON, Column, event
from sqlmodel import Field, Session, SQLModel, create_engine, select

DB_PATH = Path(__file__).parent / "ultimate_xi.db"

# Source of truth for how stats group into pentagon categories. The app and the
# seed script both read this, so column names below must match these entries.
CATEGORIES: dict[str, list[str]] = {
    "physical": ["pace", "stamina", "strength", "agility"],
    "technical": ["passing", "shooting", "dribbling", "tackling", "interceptions"],
    "mental": ["positioning", "vision", "aggression", "composure"],
    "goalkeeping": ["reflexes", "handling", "positioning_gk", "distribution"],
    "hidden": ["consistency", "injury_proneness"],
}


class Player(SQLModel, table=True):
    name: str = Field(primary_key=True)

    pace: float
    stamina: float
    strength: float
    agility: float

    passing: float
    shooting: float
    dribbling: float
    tackling: float
    interceptions: float

    positioning: float
    vision: float
    aggression: float
    composure: float

    reflexes: float
    handling: float
    positioning_gk: float
    distribution: float

    consistency: float
    injury_proneness: float

    link_up_partners: list[str] = Field(default_factory=list, sa_column=Column(JSON))


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    # WAL lets readers work during a write; busy_timeout makes a second writer
    # wait its turn instead of erroring (last-write-wins, no conflict detection).
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def load_characters() -> dict[str, dict[str, dict[str, float]]]:
    """Return {name: {category: {stat: value}}} for the comparison UI."""
    with Session(engine) as session:
        players = session.exec(select(Player)).all()
    result = {}
    for p in players:
        char = {
            cat: {stat: getattr(p, stat) for stat in stats}
            for cat, stats in CATEGORIES.items()
        }
        char["link_up_partners"] = p.link_up_partners
        result[p.name] = char
    return result


def update_player(name: str, stat_values: dict[str, float],
                  link_up_partners: list[str]) -> None:
    """Persist edited ratings for one player in a single transaction."""
    with Session(engine) as session:
        player = session.get(Player, name)
        for field, value in stat_values.items():
            setattr(player, field, value)
        player.link_up_partners = link_up_partners
        session.add(player)
        session.commit()
