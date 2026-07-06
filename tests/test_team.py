from team import Placement, TeamDoc, team_validation_errors

KNOWN = {"mario", "luigi", "peach", "bowser", "yoshi", "link", "zelda",
         "kirby", "fox", "pikachu", "samus", "ness"}


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
