"""`medomni studio dummy` (part 5, R-70): the same folder as Core's make_dataset with the package's labels planted."""
from medomni.core import hashing
from medomni.core.cli import main
from medomni.studio.dummy import make as make_dataset
from medomni.studio.testing import DATASETS


def test_command_writes_what_make_dataset_writes(tmp_path, capsys):
    assert main(["studio", "dummy", str(DATASETS / "dummy-bdsp"), "--out", str(tmp_path / "cmd"), "--subjects", "3"]) == 0
    assert "planted labels" in capsys.readouterr().out
    direct = make_dataset(DATASETS / "dummy-bdsp", tmp_path / "direct", subjects=3)
    assert hashing.dir_hash(tmp_path / "cmd/raw") == hashing.dir_hash(direct.root)
    assert (tmp_path / "cmd/planted.json").read_bytes() == (tmp_path / "direct/planted.json").read_bytes()


def test_by_name(tmp_path):
    assert main(["studio", "dummy", "dummy-omop", "--out", str(tmp_path / "o"), "--subjects", "3", "--seed", "4"]) == 0
    assert (tmp_path / "o/raw/clinical_data/person.csv").read_text().count("\n") == 4


def test_unknown_package(tmp_path, capsys):
    assert main(["studio", "dummy", "no-such-dataset", "--out", str(tmp_path / "x")]) == 2
    assert "no dataset package" in capsys.readouterr().err
