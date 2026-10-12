"""Read the agreed model-output files without substituting synthetic values."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import auc, roc_curve


MODELS = {"prob_mif": "mIF", "prob_clinical": "Clinical", "prob_fused": "Fused"}


def read_csv(path, columns):
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {', '.join(sorted(missing))}.")
    if frame.empty:
        raise ValueError(f"{path.name}: file has no rows.")
    return frame


def patient_ids(frame, filename):
    frame["Patient_id"] = frame["Patient_id"].str.strip()
    if frame["Patient_id"].eq("").any():
        raise ValueError(f"{filename}: Patient_id cannot be blank.")


def numbers(frame, columns, filename, probability=False):
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if not np.isfinite(values).all():
            raise ValueError(f"{filename}: {column} must contain finite numbers in every row.")
        if probability and not values.between(0, 1).all():
            raise ValueError(f"{filename}: {column} must be between 0 and 1.")
        frame[column] = values


def predictions(path):
    frame = read_csv(path, ["Patient_id", *MODELS, "actual_response"])
    patient_ids(frame, path.name)
    if frame["Patient_id"].duplicated().any():
        raise ValueError(f"{path.name}: one row per patient is required; duplicate Patient_id found.")
    numbers(frame, MODELS, path.name, probability=True)
    label = frame["actual_response"]
    numeric = pd.to_numeric(label, errors="coerce")
    if (~label.eq("") & ~numeric.isin([0, 1])).any():
        raise ValueError(f"{path.name}: actual_response must be 0, 1, or blank (unknown).")
    frame["actual_response"] = numeric
    return frame.sort_values("Patient_id").reset_index(drop=True)


def narratives(path, ids):
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and value.strip()
        for key, value in payload.items()
    ):
        raise ValueError(f"{path.name}: expected an object mapping Patient_id to non-empty text.")
    if set(payload) - ids:
        raise ValueError(f"{path.name}: patient IDs do not match the prediction file.")
    return payload


def importances(path):
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or not payload or set(payload) - {"mif", "clinical"}:
        raise ValueError(f"{path.name}: expected mif and/or clinical feature lists.")
    result = {}
    for modality, rows in payload.items():
        if not isinstance(rows, list) or not rows or not all(
            isinstance(row, dict) and isinstance(row.get("feature"), str)
            and row["feature"].strip() and "importance" in row for row in rows
        ):
            raise ValueError(f"{path.name}: {modality} requires feature and importance per row.")
        frame = pd.DataFrame(rows)[["feature", "importance"]]
        if frame["feature"].duplicated().any():
            raise ValueError(f"{path.name}: duplicate feature names in {modality}.")
        numbers(frame, ["importance"], path.name)
        # Signed permutation importance is valid; preserve the producer's values.
        result[modality] = frame.sort_values("importance", ascending=False)
    return result


def tiles(path, ids):
    frame = read_csv(path, ["Patient_id", "tile_x", "tile_y", "tile_prob"])
    patient_ids(frame, path.name)
    if set(frame["Patient_id"]) - ids:
        raise ValueError(f"{path.name}: patient IDs do not match the prediction file.")
    numbers(frame, ["tile_x", "tile_y"], path.name)
    numbers(frame, ["tile_prob"], path.name, probability=True)
    if "slide_id" not in frame:
        frame["slide_id"] = "Single slide"
    else:
        frame["slide_id"] = frame["slide_id"].str.strip()
        if frame["slide_id"].eq("").any():
            raise ValueError(f"{path.name}: slide_id cannot be blank.")
    if frame.duplicated(["Patient_id", "slide_id", "tile_x", "tile_y"]).any():
        raise ValueError(f"{path.name}: duplicate tile coordinates; provide slide_id for multiple slides.")
    return frame


def load_bundle(folder):
    folder = Path(folder)
    path = folder / "patient_predictions.csv"
    if not path.exists():
        raise ValueError("patient_predictions.csv is missing. Copy model outputs into results/predictions/ and reload.")
    try:
        patients = predictions(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError("patient_predictions.csv could not be read as CSV.") from error
    ids = set(patients["Patient_id"])
    data = {"patients": patients, "narratives": {}, "importances": {}, "tiles": pd.DataFrame()}
    status = [{"File": path.name, "Status": "Ready", "Detail": f"{len(patients)} patients"}]
    for key, filename, reader in [
        ("narratives", "narratives.json", lambda p: narratives(p, ids)),
        ("importances", "feature_importances.json", importances),
        ("tiles", "tile_predictions.csv", lambda p: tiles(p, ids)),
    ]:
        path = folder / filename
        if not path.exists():
            status.append({"File": filename, "Status": "Missing", "Detail": "Panel remains empty; no synthetic substitute"})
            continue
        try:
            data[key] = reader(path)
            detail = "Loaded"
            if key == "narratives":
                detail = f"{len(data[key])}/{len(ids)} patients have narrative text"
            status.append({"File": filename, "Status": "Ready", "Detail": detail})
        except (ValueError, TypeError, OSError, pd.errors.ParserError) as error:
            detail = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "Invalid file format; check the data contract"
            status.append({"File": filename, "Status": "Invalid", "Detail": detail})
    data["status"] = pd.DataFrame(status)
    return data


def roc_results(patients):
    labeled = patients.dropna(subset=["actual_response"])
    if labeled["actual_response"].nunique() < 2:
        return {}, len(labeled)
    curves = {}
    for column, name in MODELS.items():
        fpr, tpr, _ = roc_curve(labeled["actual_response"], labeled[column], pos_label=1)
        curves[name] = {"fpr": fpr, "tpr": tpr, "auc": auc(fpr, tpr)}
    return curves, len(labeled)
