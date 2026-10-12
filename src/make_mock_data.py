"""Generate synthetic fixtures only; never overwrite the real output directory."""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def generate(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    ids = [f"P{i:02d}" for i in range(1, 20)]
    labels = np.array([1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0])
    mif = np.clip(0.30 + labels * 0.33 + rng.normal(0, 0.23, 19), 0.05, 0.95)
    clinical = np.clip(0.34 + labels * 0.26 + rng.normal(0, 0.24, 19), 0.05, 0.95)
    mif[2], clinical[2] = 0.81, 0.32
    mif[0], clinical[0] = 0.79, 0.85
    fused = 0.55 * mif + 0.45 * clinical  # Synthetic illustration, not a fusion model.
    frame = pd.DataFrame({"Patient_id": ids, "prob_mif": mif, "prob_clinical": clinical,
                          "prob_fused": fused, "actual_response": labels}).round(4)
    frame.to_csv(folder / "patient_predictions.csv", index=False)
    tile_rows = []
    for patient, probability in zip(ids, mif):
        for slide in ["A", "B"] if patient == "P01" else ["A"]:
            for y in range(10):
                for x in range(12):
                    if ((x - 5.5) / 5.5) ** 2 + ((y - 4.5) / 4.5) ** 2 > 1:
                        continue
                    tile_rows.append({"Patient_id": patient, "slide_id": slide, "tile_x": x,
                                      "tile_y": y, "tile_prob": round(float(np.clip(
                                          probability + .15 * np.sin(x / 2) + rng.normal(0, .1), .02, .98)), 4)})
    pd.DataFrame(tile_rows).to_csv(folder / "tile_predictions.csv", index=False)
    payload = {patient: f"Synthetic narrative for {patient}. The demonstration combines spatial mIF and clinical model scores into a precomputed fused score of {probability:.0%}. These invented values illustrate the interface only. A real narrative supplied by the model team will appear here after integration."
               for patient, probability in zip(ids, fused)}
    (folder / "narratives.json").write_text(json.dumps(payload, indent=2) + "\n")
    features = {
        "mif": [{"feature": name, "importance": value} for name, value in [
            ("CD3+ / CD8+ spatial clustering", .24), ("PD-L1+ cell proportion", .19),
            ("iNOS+ cell proportion", .15), ("SOX10+ cell proportion", .12),
            ("CD8+ cell proportion", .08)]],
        "clinical": [{"feature": name, "importance": value} for name, value in [
            ("LDH level", .22), ("Prior ipilimumab", .17), ("Metastatic stage", .14),
            ("Number of metastatic sites", .11), ("Age", .06)]],
    }
    (folder / "feature_importances.json").write_text(json.dumps(features, indent=2) + "\n")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "demo_data")
