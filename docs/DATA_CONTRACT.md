# Model output contract

The Streamlit UI consumes local files under `results/predictions/`. Paths below are relative to this repository. All outputs for a demo should come from a consistent model/evaluation run. The viewer reads files on interaction; stage a complete export before reloading to avoid observing a partially written bundle.

## Patient predictions — required

File: `patient_predictions.csv`

```csv
Patient_id,prob_mif,prob_clinical,prob_fused,actual_response
P01,0.79,0.85,0.82,1
P03,0.81,0.32,0.59,0
P04,0.28,0.31,0.29,
```

- One row per patient, with a unique non-empty `Patient_id`.
- All three scores are required, finite numbers in [0, 1], where larger means higher probability of responder. Percent strings such as `79%` are invalid.
- `prob_fused` must come from the agreed fusion method. The UI never computes a replacement fused score.
- `actual_response` is 1 for responder, 0 for non-responder, or blank if unknown. The column is required even when all labels are unknown.
- IDs are read as strings, preserving leading zeros. Outer whitespace is stripped in CSV IDs. The model team should export canonical IDs without whitespace and use exactly the same IDs across files.
- Extra columns are allowed but are not displayed as new features automatically.

The patient selector uses this file. It does not require a separate clinical features file. If the source clinical file uses different IDs, resolve the mapping during export; the UI does not infer mappings.

ROC evaluation uses all rows with known labels and the same rows for each model. Both outcome classes are needed. Supply held-out/out-of-fold patient predictions, keeping every patient's slides/tiles in the same fold. Do not export repeated fold rows for one patient; aggregate the intended evaluation score upstream. The UI cannot establish whether predictions were evaluated independently of training.

## Feature importance — optional until available

File: `feature_importances.json`

```json
{
  "mif": [
    {"feature": "CD3+ / CD8+ spatial clustering", "importance": 0.15}
  ],
  "clinical": [
    {"feature": "LDH level", "importance": 0.12}
  ]
}
```

Either modality may be provided independently. Each supplied modality needs a non-empty list of unique, non-empty feature names with finite numeric importance values. Signed importance values are supported. The UI sorts descending and displays the top 10 for each modality.

These are **global model importance values**. Provide readable names and document how the values were calculated. Do not put patient-level SHAP values in this file; they have a different interpretation. Scales are shown as supplied, without normalization or cross-modality ranking.

## Narratives — optional until available

File: `narratives.json`

```json
{
  "P01": "Pre-generated narrative for P01.",
  "P03": "Pre-generated narrative for P03."
}
```

Paulo's integration produces the text; Khai connects the export to the UI. Keys must exactly match prediction IDs. Values must be non-empty strings. A subset of patients is allowed; a selected patient without text shows a waiting message. Unknown IDs invalidate the narrative file to surface mapping mistakes.

The UI displays plain text and does not invoke a model. Supply narratives grounded in the selected patient's actual model outputs and the approved input features. Do not replace missing narratives with synthetic patient-specific claims.

## Tile predictions — optional

File: `tile_predictions.csv`

```csv
Patient_id,slide_id,tile_x,tile_y,tile_prob
P01,A,1,1,0.85
P01,A,1,2,0.72
P01,B,1,1,0.61
```

- `Patient_id`, `tile_x`, `tile_y`, and `tile_prob` are required.
- Use `slide_id` whenever a patient has more than one slide. It may be omitted only for a single slide per patient.
- Coordinates are finite numeric grid coordinates. `tile_prob` must be finite and in [0, 1].
- The tuple `(Patient_id, slide_id, tile_x, tile_y)` must be unique.
- All patient IDs must appear in patient predictions. Partial patient coverage is allowed.
- Export only retained tiles; missing coordinates remain blank rather than being filled with zero.
- Y increases downward in the viewer. The map is a grid visualization, not an image overlay.

Do not infer tile predictions by repeating patient-level scores. If genuine tile predictions are unavailable, omit this file and skip the optional map.

## Failure behavior

Invalid required predictions block the real-data view. Missing or invalid optional files leave only their corresponding panels empty. **Data readiness** shows the reason. Synthetic fixtures are never inserted into a real-data bundle.
