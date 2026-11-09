"""The one-time v0.2 converters (R-58): every converted file validates; the output is stable."""
import pytest

from medomni.core import contracts as c
from medomni.core.contracts import convert
from medomni.core.contracts.convert import agents, cards, families


@pytest.fixture(scope="module")
def fam(repo):
    return families.convert(repo)


def test_families_convert_and_validate(fam):
    outputs, notes = fam
    assert len(outputs) == 42
    for rel, data in outputs.items():
        f = c.load_data(data, c.FamilyFile, rel)
        assert rel == f"core/families/{f.id}.yaml"
        assert "reader" not in data and "valid_range" not in data["protocol"] and "unit" not in data["protocol"]
    assert sum(n["dtype"] == "stated" for n in notes.values()) == 11
    assert outputs["core/families/spo2-series-10hz-pct.yaml"]["protocol"]["range"] == [0.0, 100.0]


def test_families_dtype_spelling(fam):
    outputs, _ = fam
    dtypes = {d["protocol"]["dtype"] for d in outputs.values()}
    assert dtypes <= {"int16", "uint8", "uint16", "float32", "float64", "text", "mixed"}
    assert outputs["core/families/retinal-heightmap-surfaces-f32.yaml"]["protocol"]["dtype"] == "float32"


def test_conversion_is_stable(repo, tmp_path):
    a = convert.write(families.convert(repo)[0], tmp_path / "a")
    b = convert.write(families.convert(repo)[0], tmp_path / "b")
    assert [p.read_bytes() for p in a] == [p.read_bytes() for p in b]


def test_agents_convert_and_match_committed(repo):
    outputs, notes = agents.convert(repo)
    assert len(outputs) == 9
    for rel, data in outputs.items():
        c.load_data(data, c.AgentConfig, rel)
        assert (repo / rel).read_text(encoding="utf-8") == convert.dump(data), f"{rel} differs from the converter"
    assert outputs["bench/agents/terminus-2-replay.yaml"]["route"] == "local"
    assert outputs["bench/agents/terminus-2-astra.yaml"]["model_served"] == "gpt-6-astra"
    assert sum(n["route"] == "cloud" for n in notes.values()) == 8


def test_committed_agents_are_all_converted(repo):
    committed = {p.relative_to(repo).as_posix() for p in (repo / "bench/agents").glob("*.yaml")}
    assert committed == set(agents.convert(repo)[0])


def test_cards_convert_and_validate(repo):
    outputs, notes = cards.convert(repo)
    assert len(outputs) == 44 == len(cards.shipped(repo))
    for rel, data in outputs.items():
        card = c.load_data(data, c.ModelCard, rel)
        assert card.authors and all(a.name for a in card.authors)
        assert list(data)[list(data).index("summary") + 1] == "authors"
    assert all(";" not in d["license"] for d in outputs.values())  # U2.11: the prose license is not shipped


def test_responses_of_shipped_encoders_validate(repo):
    found = cards.responses(repo)
    assert len(found) == 44
    n = 0
    for eid, responses in found.items():
        for r in responses:
            c.load_data(r, c.ContainerResponse, eid)
            n += 1
    assert n == 105


def test_shipped_cards_are_converted(repo):
    """R-66: Stage 3 part 1 commits the 44 converted cards at their v0.2 paths; each carries authors (R-62)."""
    from medomni.core.contracts import ModelCard, load

    rels = list(cards.convert(repo)[0])
    assert len(rels) == 44
    for rel in rels:
        assert load(repo / rel, ModelCard).authors, rel


@pytest.mark.parametrize("kind", ["task-set", "result-record"])
def test_not_converted(kind):
    with pytest.raises(convert.NotConverted, match="Stage 3"):
        convert.refuse(kind)
