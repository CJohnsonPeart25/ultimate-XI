import pytest
from sqlmodel import Session, SQLModel, create_engine

import models
from models import CATEGORIES, POSITIONS, STAT_FIELDS, Player, PositionWeight


def make_player(name: str = "test", **overrides) -> Player:
    values = {stat: 3.0 for stat in STAT_FIELDS}
    values.update(overrides)
    return Player(name=name, **values)


def test_overall_is_mean_of_every_stat():
    player = make_player(pace=1.0, stamina=2.0, strength=3.0, agility=4.0)
    expected = (1.0 + 2.0 + 3.0 + 4.0 + 3.0 * 15) / len(STAT_FIELDS)
    assert player.overall == pytest.approx(expected)


def test_category_overall_averages_only_that_category():
    player = make_player(pace=1.0, stamina=2.0, strength=3.0, agility=4.0)
    assert player.category_overall("physical") == pytest.approx(2.5)
    assert player.category_overall("mental") == pytest.approx(3.0)


def test_axis_values_for_category_returns_its_stats_in_order():
    player = make_player(pace=1.0, stamina=2.0, strength=3.0, agility=4.0)
    assert player.axis_values("physical") == [1.0, 2.0, 3.0, 4.0]


def test_axis_values_for_overall_returns_category_averages():
    player = make_player(pace=1.0, stamina=2.0, strength=3.0, agility=4.0)
    values = player.axis_values("Overall")
    assert len(values) == len(CATEGORIES)
    assert values[0] == pytest.approx(2.5)  # physical
    assert values[2] == pytest.approx(3.0)  # mental


def test_fit_is_normalized_weighted_blend():
    player = make_player(reflexes=5.0, handling=1.0)
    # weights need not sum to 1; Fit divides by their sum.
    fit = player.fit({"reflexes": 3.0, "handling": 1.0})
    assert fit == pytest.approx((5.0 * 3 + 1.0 * 1) / 4)


def test_fit_uses_only_weighted_stats():
    # Only stats present in the weights dict move Fit; everything else (including
    # hidden stats, which default weights never include) is ignored.
    player = make_player(shooting=5.0, consistency=1.0)
    assert player.fit({"shooting": 1.0}) == pytest.approx(5.0)


def test_fit_with_zero_weights_is_zero():
    assert make_player().fit({}) == 0.0


def test_team_issues_flags_incomplete_and_gk_count():
    assert models.team_issues([]) != []
    assert "0/11" in " ".join(models.team_issues([]))
    eleven_no_gk = ["defence"] * 11
    assert any("goalkeeper" in i for i in models.team_issues(eleven_no_gk))
    two_gk = ["goalkeeper", "goalkeeper"] + ["midfield"] * 9
    assert any("2 goalkeeper" in i for i in models.team_issues(two_gk))


def test_team_issues_empty_when_complete():
    positions = ["goalkeeper"] + ["defence"] * 4 + ["midfield"] * 4 + ["attack"] * 2
    assert len(positions) == 11
    assert models.team_issues(positions) == []


def test_team_tally_counts_per_position():
    positions = ["goalkeeper", "defence", "defence", "attack"]
    tally = models.team_tally(positions)
    assert tally == {"goalkeeper": 1, "defence": 2, "midfield": 0, "attack": 1}


def test_update_position_weights_roundtrip(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'w.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(models, "engine", engine)

    models.seed_position_weights()
    seeded = models.load_position_weights()
    assert set(seeded) == set(POSITIONS)
    assert seeded["goalkeeper"]["reflexes"] > 0

    models.update_position_weights("goalkeeper", {"reflexes": 99.0})
    assert models.load_position_weights()["goalkeeper"]["reflexes"] == pytest.approx(99.0)


def test_update_player_roundtrip(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(make_player("mario", link_up_partners=["luigi"]))
        session.commit()

    monkeypatch.setattr(models, "engine", engine)

    stat_values = {stat: 4.5 for stat in STAT_FIELDS}
    models.update_player("mario", stat_values, ["peach"])

    reloaded = models.load_players()["mario"]
    assert reloaded.pace == pytest.approx(4.5)
    assert reloaded.overall == pytest.approx(4.5)
    assert reloaded.link_up_partners == ["peach"]
