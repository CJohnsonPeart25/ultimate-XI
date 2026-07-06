import pytest
from sqlmodel import Session, SQLModel, create_engine

import models
from models import CATEGORIES, STAT_FIELDS, Player


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
