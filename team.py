from pydantic import BaseModel

from models import POSITIONS, team_issues


class Placement(BaseModel):
    character: str
    position: str


class TeamDoc(BaseModel):
    """A Team as a portable JSON document (see ADR-0001). Not a DB entity."""

    name: str = ""
    placements: list[Placement] = []


def team_validation_errors(doc: TeamDoc, known_characters: set[str]) -> list[str]:
    """Reasons an imported Team is invalid; empty means it's a complete valid Team."""
    positions = [p.position for p in doc.placements]
    errors = list(team_issues(positions))

    bad_positions = sorted({p.position for p in doc.placements
                            if p.position not in POSITIONS})
    if bad_positions:
        errors.append(f"unknown positions: {', '.join(bad_positions)}")

    characters = [p.character for p in doc.placements]
    duplicates = sorted({c for c in characters if characters.count(c) > 1})
    if duplicates:
        errors.append(f"duplicate characters: {', '.join(duplicates)}")

    unknown = sorted(set(characters) - known_characters)
    if unknown:
        errors.append(f"unknown characters: {', '.join(unknown)}")

    return errors
