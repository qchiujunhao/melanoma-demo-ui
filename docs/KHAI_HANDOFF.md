# Handoff: connect real model outputs

## What is ready

This repository provides the Streamlit UI for a multimodal melanoma ICB-response demo. It includes patient selection, three model scores, global feature importance for mIF and clinical models, ROC comparison, pre-generated narrative text, and an optional slide-aware tile map. A complete synthetic dataset makes the demo runnable before model results exist.

Khai's proposed task is to connect the real result files and check the end-to-end presentation flow. Model training, fusion, feature importance calculation, and narrative generation remain upstream tasks.

## Ownership

| Input / task | Producer or owner | Integration work |
| --- | --- | --- |
| mIF patient scores and importance | Alyssa | Export to the agreed schema |
| Clinical patient scores and importance | Isis | Export and align the patient IDs |
| Fused patient score | Model team; confirm a named owner | Confirm the fusion method and supply one score per patient |
| Nemotron narrative text | Paulo | Supply patient-keyed JSON |
| UI and synthetic demonstration | Junhao | Review presentation behavior |
| Real-data integration | Khai (proposed) | Align exports, validate files, run the real-data UI |
| Tile predictions | Alyssa, if available | Optional; can be omitted if time is short |

## Integration steps

1. Clone the repository in the environment with authorized access to the project data. Install dependencies using the README instructions.
2. Run the synthetic demo first. Use P01, P03, Model comparison, and the narrative panel to learn the expected presentation flow.
3. Obtain preliminary feature names from Alyssa. Confirm the canonical patient ID format against the project's `data/slide_id_map.csv` and `results/features/clinical_features.csv`. Keep IDs as strings.
4. Export one row per patient into `results/predictions/patient_predictions.csv`. Include all three scores and a known or blank outcome label. Confirm who produces the fused score; do not implement an unagreed average in the adapter.
5. Add `feature_importances.json` and Paulo's `narratives.json`. Use exactly matching patient IDs and readable feature names.
6. Select **Real model outputs**, click **Reload files**, and check **Data readiness**. Fix invalid-file warnings before presentation. Missing optional panels can remain empty temporarily.
7. Add `tile_predictions.csv` only if genuine tile-level scores are ready. Provide `slide_id` for multiple slides per patient. Otherwise skip this panel.
8. Verify a patient with agreeing scores and, if available, one with conflicting scores. Add UI progress and screenshots to the team's existing Hackathon presentation deck.

## Acceptance checklist

- [ ] Patient count and IDs match the intended evaluation cohort; no duplicate patient rows.
- [ ] Two selected patients' scores exactly match the producer's files, including the fused score.
- [ ] Labels use 1 = responder and 0 = non-responder; missing labels are blank.
- [ ] Feature bars use the intended global importance method and readable names.
- [ ] Each selected patient's narrative comes from that same patient's outputs.
- [ ] ROC inputs are held-out/out-of-fold patient predictions on the same cohort across models. Both outcome classes are present if ROC is shown.
- [ ] Reload picks up a new export, and missing optional inputs show empty panels rather than synthetic content.
- [ ] Tile maps, if included, do not merge slides and do not invent predictions.
- [ ] The presentation runs in the approved environment; real outputs are not committed to GitHub.

See [DATA_CONTRACT.md](DATA_CONTRACT.md) for validation rules and example file formats. The repository includes synthetic fixtures with the same schemas; they are a formatting reference, not clinical data or a model-performance target.
