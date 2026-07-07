from pathlib import Path

from sqlalchemy import JSON, Column, event
from sqlmodel import Field, Session, SQLModel, create_engine, select

DB_PATH = Path(__file__).parent / "ultimate_xi.db"

MAX_RATING = 5.0

# Source of truth for how stats group into pentagon categories. The app and the
# seed script both read this, so column names below must match these entries.
CATEGORIES: dict[str, list[str]] = {
    "physical": ["pace", "stamina", "strength", "agility"],
    "technical": ["passing", "shooting", "dribbling", "tackling", "interceptions"],
    "mental": ["positioning", "vision", "aggression", "composure"],
    "goalkeeping": ["reflexes", "handling", "positioning_gk", "distribution"],
    "hidden": ["consistency", "injury_resilience"],
}
STAT_FIELDS = [stat for stats in CATEGORIES.values() for stat in stats]

# The four coarse Positions a Character can be assigned to (see CONTEXT.md).
POSITIONS = ["goalkeeper", "defence", "midfield", "attack"]
GOALKEEPER = "goalkeeper"
TEAM_SIZE = 11


def team_tally(positions: list[str]) -> dict[str, int]:
    """Count of filled Placements per Position."""
    return {pos: positions.count(pos) for pos in POSITIONS}


def team_issues(positions: list[str]) -> list[str]:
    """Human-readable reasons a Team isn't complete; empty means complete."""
    issues = []
    if len(positions) != TEAM_SIZE:
        issues.append(f"{len(positions)}/{TEAM_SIZE} slots filled")
    gk = positions.count(GOALKEEPER)
    if gk != 1:
        issues.append(f"{gk} goalkeepers (need exactly 1)")
    return issues

# First-pass default weights per Position over the Stats that matter for it.
# Relative magnitudes only — Fit normalizes by their sum, so these need not add
# to anything. Omitted Stats (and all hidden Stats) simply do not contribute.
# Tunable in-app via the weights editor.
DEFAULT_POSITION_WEIGHTS: dict[str, dict[str, float]] = {
    "goalkeeper": {
        "reflexes": 10, "positioning_gk": 8, "handling": 7,
        "distribution": 4, "agility": 3, "composure": 3,
    },
    "defence": {
        "tackling": 9, "interceptions": 9, "strength": 7, "positioning": 7,
        "aggression": 5, "pace": 4, "composure": 4, "passing": 3,
    },
    "midfield": {
        "passing": 9, "vision": 8, "stamina": 8, "dribbling": 6, "composure": 6,
        "interceptions": 5, "positioning": 5, "tackling": 4, "pace": 3,
    },
    "attack": {
        "shooting": 9, "pace": 7, "dribbling": 7, "positioning": 7,
        "composure": 5, "agility": 5, "passing": 4, "vision": 4,
    },
}

# The radar "view" that plots category averages instead of a single category's stats.
OVERALL_VIEW = "Overall"


def view_axis_keys(view: str) -> list[str]:
    """Axis keys (category names, or stat names) for a given radar view."""
    return list(CATEGORIES) if view == OVERALL_VIEW else CATEGORIES[view]


class Player(SQLModel, table=True):
    # Streamlit's file-watcher re-executes this module on save, but SQLModel's
    # metadata lives in the cached sqlmodel package and survives the reload —
    # so re-registering the table would raise "already defined". The schema is
    # identical each time, so allowing redefinition is safe.
    __table_args__ = {"extend_existing": True}

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
    injury_resilience: float

    link_up_partners: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    def category_overall(self, category: str) -> float:
        stats = CATEGORIES[category]
        return sum(getattr(self, stat) for stat in stats) / len(stats)

    @property
    def overall(self) -> float:
        return sum(getattr(self, stat) for stat in STAT_FIELDS) / len(STAT_FIELDS)

    def axis_values(self, view: str) -> list[float]:
        """Radar r-series for a view: category averages, or one category's stats."""
        if view == OVERALL_VIEW:
            return [self.category_overall(cat) for cat in CATEGORIES]
        return [getattr(self, stat) for stat in CATEGORIES[view]]

    def fit(self, weights: dict[str, float]) -> float:
        """Positional Fit: normalized weighted blend of Stats, on the 0-5 scale."""
        total = sum(weights.values())
        if total == 0:
            return 0.0
        return sum(getattr(self, stat) * w for stat, w in weights.items()) / total


class PositionWeight(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    position: str = Field(primary_key=True)
    stat: str = Field(primary_key=True)
    weight: float


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


def load_players() -> dict[str, Player]:
    with Session(engine) as session:
        return {p.name: p for p in session.exec(select(Player)).all()}


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


def seed_position_weights() -> None:
    """Insert the default Position weights for any (position, stat) not yet present."""
    init_db()
    with Session(engine) as session:
        for position, weights in DEFAULT_POSITION_WEIGHTS.items():
            for stat, weight in weights.items():
                if session.get(PositionWeight, (position, stat)) is None:
                    session.add(PositionWeight(position=position, stat=stat,
                                               weight=float(weight)))
        session.commit()


def load_position_weights() -> dict[str, dict[str, float]]:
    """Return {position: {stat: weight}} for all four Positions."""
    weights: dict[str, dict[str, float]] = {pos: {} for pos in POSITIONS}
    with Session(engine) as session:
        for row in session.exec(select(PositionWeight)).all():
            weights.setdefault(row.position, {})[row.stat] = row.weight
    return weights


def update_position_weights(position: str, weights: dict[str, float]) -> None:
    """Persist edited weights for one Position in a single transaction."""
    with Session(engine) as session:
        for stat, weight in weights.items():
            row = session.get(PositionWeight, (position, stat))
            if row is None:
                row = PositionWeight(position=position, stat=stat, weight=weight)
            else:
                row.weight = weight
            session.add(row)
        session.commit()
