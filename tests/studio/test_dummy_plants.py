"""R-147: Studio derives Core's planting specs from a package's labels.yaml; Core's generator reads no recipe."""
import pytest

from medomni.core.families.dummy.datasets import make_dataset
from medomni.core.testing import DATASETS as CORE
from medomni.studio.dummy import make, plants
from medomni.studio.testing import DATASETS
from tests.core.test_dummy import PLANTS, SHAPES


@pytest.mark.parametrize("shape", SHAPES)
def test_plants_from_labels_are_cores_specs(shape):
    assert plants(DATASETS / shape) == PLANTS[shape]


@pytest.mark.parametrize("shape", SHAPES)
def test_studio_and_core_packages_make_the_same_data(shape, tmp_path):
    from medomni.core import hashing

    a = make(DATASETS / shape, tmp_path / "studio", subjects=4)
    b = make_dataset(CORE / shape, tmp_path / "core", subjects=4, plant=PLANTS[shape])
    assert hashing.dir_hash(a.root) == hashing.dir_hash(b.root) and a.planted == b.planted


def test_no_labels_file_plants_nothing(tmp_path):
    assert plants(CORE / "dummy-mimic") == {}
