"""Streamlit viewer for precomputed melanoma ICB-response model outputs."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import MODELS, load_bundle, roc_results


ROOT = Path(__file__).resolve().parents[1]
COLORS = {"mIF": "#087F8C", "Clinical": "#7567AC", "Fused": "#172C40"}
st.set_page_config(page_title="Melanoma | Response Explorer", page_icon="🧬", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1440px; padding-top: 2.5rem; padding-bottom: 3rem;}
h1 {letter-spacing: -0.045em; font-weight: 700 !important;}
h3 {letter-spacing: -0.02em;}
.eyebrow {color:#087F8C; font-size:0.75rem; letter-spacing:0.15em; font-weight:700; margin-bottom:0.5rem;}
[data-testid="stMetric"] {background:white; border:1px solid #DCE5EB; border-radius:12px; padding:18px 22px;}
[data-testid="stMetricLabel"] {color:#657889;}
[data-testid="stSidebar"] {border-right:1px solid #DCE5EB;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
</style>
""", unsafe_allow_html=True)


def style_chart(fig, height=310):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=8, r=18, t=12, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial, sans-serif", color="#172C40", size=12))
    return fig


def chart(fig, key):
    st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False})


def reset_patient():
    # A mode transition replaces the dataset and may remove the patient widget.
    for mode_name in ["Synthetic demo", "Real model outputs"]:
        st.session_state.pop(f"patient_{mode_name}", None)


with st.sidebar:
    st.markdown('<div class="eyebrow">MULTIMODAL ONCOLOGY</div>', unsafe_allow_html=True)
    st.title("Response explorer")
    st.caption("Precomputed model outputs, brought together for a research demonstration.")
    st.divider()
    mode = st.radio("Data source", ["Synthetic demo", "Real model outputs"], key="source", on_change=reset_patient)
    st.button("Reload files", width="stretch", help="Read the current files again. No cached model results.")

folder = ROOT / ("demo_data" if mode == "Synthetic demo" else "results/predictions")
try:
    bundle = load_bundle(folder)
except ValueError as error:
    st.title("Connect model outputs")
    st.error(str(error))
    st.info("Start with patient_predictions.csv. Other panels can be added independently. Select Synthetic demo to preview the complete interface.")
    st.code("results/predictions/\n  patient_predictions.csv\n  feature_importances.json\n  narratives.json\n  tile_predictions.csv  # optional")
    st.caption("See docs/DATA_CONTRACT.md for file schemas and validation rules.")
    st.stop()

patients = bundle["patients"]
with st.sidebar:
    patient = st.selectbox("Select patient", patients["Patient_id"].tolist(), key=f"patient_{mode}")
    reveal = st.toggle("Reveal observed response", value=False, key="reveal")
    st.caption("Responder = 1 · Non-responder = 0\n\nDisplay threshold: P(response) ≥ 0.50.")
    st.divider()
    st.markdown("**Suggested demo sequence**")
    st.caption("1. Explore a patient's scores.\n2. Compare the two modalities.\n3. Open Model comparison.\n4. Review the narrative.")
    if mode == "Synthetic demo":
        st.caption("P01: agreeing scores\n\nP03: conflicting scores")

row = patients.loc[patients["Patient_id"].eq(patient)].iloc[0]
synthetic = mode == "Synthetic demo"
st.markdown('<div class="eyebrow">MELANOMA · IMMUNOTHERAPY RESPONSE</div>', unsafe_allow_html=True)
st.title("Two modalities. One patient view.")
st.caption("Explore spatial multiplex immunofluorescence (mIF), clinical features, and their fused prediction of response to immune checkpoint blockade (ICB).")
if synthetic:
    st.warning("SYNTHETIC DEMO · All patient IDs, scores, heatmaps, importance values, and narratives are invented. These are not study results.", icon="🧪")
else:
    st.info("REAL MODEL OUTPUTS · Loaded from local files. Predictions and narratives are research outputs for this demonstration.", icon="📂")

predicted = "Responder" if row["prob_fused"] >= .5 else "Non-responder"
label_col, count_col = st.columns([3, 1])
with label_col:
    st.subheader(f"{patient} · Predicted {predicted.lower()}")
    st.caption("Fused model classification at a display threshold of 0.50; scores are shown as supplied by the model team.")
with count_col:
    st.caption(f"COHORT VIEW · {len(patients)} patients")
    if reveal:
        label = row["actual_response"]
        observed = "Unknown" if pd.isna(label) else ("Responder" if label == 1 else "Non-responder")
        st.markdown(f"**Observed: {observed}**")

for col, (field, name) in zip(st.columns(3), MODELS.items()):
    with col:
        st.metric(f"{name} · P(response)", f"{row[field]:.1%}")

overview, comparison, readiness = st.tabs(["Patient overview", "Model comparison", "Data readiness"])
with overview:
    st.write("")
    if (row["prob_mif"] >= .5) != (row["prob_clinical"] >= .5):
        st.info("The modalities disagree at the 0.50 threshold. Compare their scores and the precomputed fused prediction.")
    else:
        st.caption("MODEL AGREEMENT · Both modalities fall on the same side of the display threshold.")
    features_col, narrative_col = st.columns([1.65, 1], gap="large")
    with features_col, st.container(border=True):
        st.subheader("What the models use")
        st.caption("Global feature importance · top 10 per modality. These are model-level values, not explanations of this individual patient.")
        for col, modality, name in zip(st.columns(2), ["mif", "clinical"], ["mIF", "Clinical"]):
            with col:
                st.markdown(f"**{name} features**")
                frame = bundle["importances"].get(modality)
                if frame is None:
                    st.info("Awaiting valid feature importance data.")
                else:
                    frame = frame.head(10).iloc[::-1]
                    fig = go.Figure(go.Bar(x=frame["importance"], y=frame["feature"], orientation="h",
                                           marker_color=COLORS[name], hovertemplate="%{y}<br>Importance: %{x:.4f}<extra></extra>"))
                    fig.update_xaxes(title="Importance", zeroline=True, zerolinecolor="#DCE5EB")
                    chart(style_chart(fig, max(250, 30 * len(frame) + 65)), f"importance_{modality}")
        st.caption("Importance scales depend on the producer's method and should not be compared across modalities without that context.")
    with narrative_col, st.container(border=True):
        st.subheader("Clinical narrative")
        st.caption("Synthetic example" if synthetic else "Pre-generated text from the Nemotron integration")
        narrative = bundle["narratives"].get(patient)
        if narrative:
            st.text(narrative)
        else:
            st.info("No narrative is available for this patient yet.")
        st.divider()
        st.caption("The viewer displays supplied text. Reload files after the model team produces new narratives.")
    with st.expander("Spatial tile map · optional"):
        st.caption("Tile-level model scores on a coordinate grid. This is not a tissue image or an individual feature attribution.")
        tile_data = bundle["tiles"]
        selected = tile_data.loc[tile_data["Patient_id"].eq(patient)] if not tile_data.empty else tile_data
        if selected.empty:
            st.info("No tile predictions available for this patient. The main demo works without this panel.")
        else:
            slide = st.selectbox("Slide", sorted(selected["slide_id"].unique()), key=f"slide_{mode}_{patient}")
            selected = selected.loc[selected["slide_id"].eq(slide)]
            grid = selected.pivot(index="tile_y", columns="tile_x", values="tile_prob").sort_index().sort_index(axis=1)
            # Missing coordinates remain empty; they are never filled with zero scores.
            fig = go.Figure(go.Heatmap(x=grid.columns, y=grid.index, z=grid.values, zmin=0, zmax=1,
                                      colorscale=[[0, "#EEEAF5"], [.5, "#9DD7CF"], [1, "#087F8C"]],
                                      hoverongaps=False, colorbar=dict(title="P(response)"),
                                      hovertemplate="X: %{x}<br>Y: %{y}<br>P(response): %{z:.1%}<extra></extra>"))
            fig.update_xaxes(title="Tile X", constrain="domain")
            fig.update_yaxes(title="Tile Y", autorange="reversed", scaleanchor="x", scaleratio=1)
            chart(style_chart(fig, 400), "tiles")
            st.caption("Coordinate convention: Y increases downward. Use slide_id to keep different slides separate.")

with comparison:
    st.write("")
    st.subheader("Does fusion improve discrimination?")
    st.caption("Receiver operating characteristic (ROC) curves compare all three models on the same labeled patients.")
    curves, labeled_count = roc_results(patients)
    if curves:
        plot_col, text_col = st.columns([1.8, 1], gap="large")
        with plot_col, st.container(border=True):
            fig = go.Figure()
            for name, curve in curves.items():
                fig.add_trace(go.Scatter(x=curve["fpr"], y=curve["tpr"], mode="lines",
                                         name=f"{name} · AUC {curve['auc']:.3f}",
                                         line=dict(color=COLORS[name], width=3)))
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance",
                                     line=dict(color="#A1AEB8", dash="dash")))
            fig.update_layout(legend=dict(orientation="h", y=-.25))
            fig.update_xaxes(title="False positive rate", range=[0, 1], constrain="domain")
            fig.update_yaxes(title="True positive rate", range=[0, 1], scaleanchor="x", scaleratio=1, constrain="domain")
            chart(style_chart(fig, 480), "roc")
        with text_col:
            st.markdown("**Area under the curve**")
            for name, curve in curves.items():
                st.metric(name, f"{curve['auc']:.3f}")
            st.caption(f"Evaluation cohort: {labeled_count} labeled patients. {len(patients) - labeled_count} unknown labels excluded.")
            st.caption("Synthetic curves illustrate the demo only." if synthetic else "For a fair comparison, supply patient-level held-out or out-of-fold predictions on the same evaluation cohort. The viewer cannot verify their provenance.")
            st.caption("AUC measures ranking, not calibration. No claim that fusion is superior is assumed by the viewer.")
    else:
        st.info(f"ROC needs at least one responder and one non-responder. Currently {labeled_count} patients have known labels.")

with readiness:
    st.write("")
    st.subheader("Data connection status")
    st.caption("Synthetic fixture files" if synthetic else "Local model output files · results/predictions/")
    st.dataframe(bundle["status"], hide_index=True, width="stretch")
    st.markdown("**Integration order**")
    st.markdown("1. Add patient predictions and confirm patient IDs.\n2. Add feature importance and pre-generated narratives.\n3. Add tile predictions if available.\n4. Select Real model outputs and reload files.")
    st.caption("See docs/DATA_CONTRACT.md for file schemas and validation rules. No training or NIM calls run inside this UI.")
    with st.expander("Inspect patient-level scores"):
        columns = ["Patient_id", *MODELS] + (["actual_response"] if reveal else [])
        st.dataframe(patients[columns], hide_index=True, width="stretch")

st.divider()
st.caption("Research prototype · precomputed outputs · local viewer" + (" · synthetic data" if synthetic else ""))
