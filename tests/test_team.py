import pytest

from models import STAT_FIELDS, Player
from team import (
    Placement,
    TeamDoc,
    overall_mean_fit,
    position_mean_fits,
    team_validation_errors,
)

KNOWN = {"mario", "luigi", "peach", "bowser", "yoshi", "link", "zelda",
         "kirby", "fox", "pikachu", "samus", "ness"}


def _player(name: str, value: float) -> Player:
    return Player(name=name, **{stat: value for stat in STAT_FIELDS})


def complete_doc() -> TeamDoc:
    order = ["mario", "luigi", "peach", "bowser", "yoshi", "link", "zelda",
             "kirby", "fox", "pikachu", "samus"]
    positions = (["goalkeeper"] + ["defence"] * 4 + ["midfield"] * 4
                 + ["attack"] * 2)
    return TeamDoc(
        name="Test XI",
        placements=[Placement(character=c, position=p)
                    for c, p in zip(order, positions)],
    )


def test_teamdoc_roundtrips_through_json():
    doc = complete_doc()
    restored = TeamDoc.model_validate_json(doc.model_dump_json())
    assert restored == doc


def test_complete_team_has_no_validation_errors():
    assert team_validation_errors(complete_doc(), KNOWN) == []


def test_wrong_count_and_gk_are_flagged():
    doc = TeamDoc(placements=[Placement(character="mario", position="attack")])
    errors = team_validation_errors(doc, KNOWN)
    assert any("1/11" in e for e in errors)
    assert any("goalkeeper" in e for e in errors)


def test_duplicate_character_is_flagged():
    doc = complete_doc()
    doc.placements[1].character = "mario"  # duplicate of slot 0
    errors = team_validation_errors(doc, KNOWN)
    assert any("duplicate characters: mario" in e for e in errors)


def test_unknown_character_is_flagged():
    doc = complete_doc()
    doc.placements[0].character = "sonic"  # not in KNOWN
    errors = team_validation_errors(doc, KNOWN)
    assert any("unknown characters: sonic" in e for e in errors)


def test_unknown_position_is_flagged():
    doc = complete_doc()
    doc.placements[0].position = "sweeper"
    errors = team_validation_errors(doc, KNOWN)
    assert any("unknown positions: sweeper" in e for e in errors)


def test_position_mean_fits_averages_placements_in_each_position():
    # Two defenders rated 4 and 2; any weight set yields Fit == the flat rating,
    # so the defence mean is 3.0. Attack has one player rated 5 -> 5.0.
    doc = TeamDoc(placements=[
        Placement(character="a", position="defence"),
        Placement(character="b", position="defence"),
        Placement(character="c", position="attack"),
    ])
    players = {"a": _player("a", 4.0), "b": _player("b", 2.0), "c": _player("c", 5.0)}
    weights = {pos: {"pace": 1.0} for pos in ["goalkeeper", "defence", "midfield", "attack"]}
    means = position_mean_fits(doc, players, weights)
    assert means["defence"] == pytest.approx(3.0)
    assert means["attack"] == pytest.approx(5.0)
    assert means["midfield"] == 0.0  # no placements


def test_overall_mean_fit_averages_all_placements():
    doc = TeamDoc(placements=[
        Placement(character="a", position="defence"),
        Placement(character="c", position="attack"),
    ])
    players = {"a": _player("a", 4.0), "c": _player("c", 2.0)}
    weights = {pos: {"pace": 1.0} for pos in ["goalkeeper", "defence", "midfield", "attack"]}
    assert overall_mean_fit(doc, players, weights) == pytest.approx(3.0)
