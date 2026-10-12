import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_loader import load_bundle, predictions, roc_results, tiles
from make_mock_data import generate


@pytest.fixture
def bundle_dir(tmp_path):
    generate(tmp_path)
    return tmp_path


def test_repeatable_fixtures_and_shared_roc_cohort(bundle_dir):
    before = (bundle_dir / "patient_predictions.csv").read_bytes()
    generate(bundle_dir)
    assert before == (bundle_dir / "patient_predictions.csv").read_bytes()
    bundle = load_bundle(bundle_dir)
    assert len(bundle["patients"]) == 19
    curves, count = roc_results(bundle["patients"])
    assert count == 19
    assert set(curves) == {"mIF", "Clinical", "Fused"}
    perfect = bundle["patients"].copy()
    for field in ["prob_mif", "prob_clinical", "prob_fused"]:
        perfect[field] = perfect["actual_response"]
    assert all(c["auc"] == 1 for c in roc_results(perfect)[0].values())
    perfect["actual_response"] = 1
    assert roc_results(perfect)[0] == {}


@pytest.mark.parametrize("column,value", [("prob_mif", "1.2"), ("prob_fused", "nan"),
                                         ("prob_clinical", ""), ("actual_response", "yes"),
                                         ("Patient_id", "")])
def test_reject_invalid_patient_outputs(bundle_dir, column, value):
    path = bundle_dir / "patient_predictions.csv"
    frame = pd.read_csv(path, dtype=str)
    frame.loc[0, column] = value
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        predictions(path)


def test_duplicate_ids_and_leading_zeros(bundle_dir):
    path = bundle_dir / "patient_predictions.csv"
    frame = pd.read_csv(path, dtype=str)
    frame.loc[0, "Patient_id"] = "001"
    frame.to_csv(path, index=False)
    assert "001" in predictions(path)["Patient_id"].tolist()
    frame.loc[1, "Patient_id"] = "001"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        predictions(path)


def test_optional_failures_do_not_invent_data(bundle_dir):
    (bundle_dir / "narratives.json").unlink()
    (bundle_dir / "feature_importances.json").write_text("{not JSON}")
    (bundle_dir / "tile_predictions.csv").unlink()
    bundle = load_bundle(bundle_dir)
    assert bundle["narratives"] == {}
    assert bundle["importances"] == {}
    assert bundle["tiles"].empty
    assert bundle["status"]["Status"].tolist() == ["Ready", "Missing", "Invalid", "Missing"]


def test_unknown_labels_excluded(bundle_dir):
    path = bundle_dir / "patient_predictions.csv"
    frame = pd.read_csv(path, dtype=str)
    frame.loc[0, "actual_response"] = ""
    frame.to_csv(path, index=False)
    curves, count = roc_results(predictions(path))
    assert count == 18 and len(curves) == 3


def test_multiple_slides_cannot_be_merged(bundle_dir):
    path = bundle_dir / "tile_predictions.csv"
    ids = set(load_bundle(bundle_dir)["patients"]["Patient_id"])
    frame = tiles(path, ids)
    assert frame.loc[frame["Patient_id"].eq("P01"), "slide_id"].nunique() == 2
    frame.drop(columns="slide_id").to_csv(path, index=False)
    with pytest.raises(ValueError, match="slide_id"):
        tiles(path, ids)


def test_unknown_narrative_id_is_not_silently_accepted(bundle_dir):
    (bundle_dir / "narratives.json").write_text(json.dumps({"other-id": "Text"}))
    bundle = load_bundle(bundle_dir)
    assert bundle["narratives"] == {}
    assert bundle["status"].iloc[1]["Status"] == "Invalid"
