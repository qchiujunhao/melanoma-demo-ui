import sys
import shutil
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from make_mock_data import generate


def test_patient_switch_and_reveal():
    app = AppTest.from_file(str(ROOT / "src/app.py"), default_timeout=20).run()
    assert not app.exception
    assert [metric.value for metric in app.metric][:3] == ["79.0%", "85.0%", "81.7%"]
    app.sidebar.selectbox[0].select("P03").run()
    assert not app.exception
    assert [metric.value for metric in app.metric][:2] == ["81.0%", "32.0%"]
    assert any("modalities disagree" in element.value for element in app.info)
    app.toggle[0].set_value(True).run()
    assert any("Observed: Responder" in element.value for element in app.markdown)
    before = [metric.value for metric in app.metric]
    app.button[0].click().run()
    assert [metric.value for metric in app.metric] == before


def test_real_mode_missing_predictions_has_no_mock_results():
    app = AppTest.from_file(str(ROOT / "src/app.py"), default_timeout=20).run()
    app.radio[0].set_value("Real model outputs").run()
    assert not app.exception
    assert app.error and "missing" in app.error[0].value
    assert len(app.metric) == 0


def test_real_mode_reads_outputs_without_optional_panels(tmp_path):
    shutil.copytree(ROOT / "src", tmp_path / "src")
    shutil.copytree(ROOT / "demo_data", tmp_path / "demo_data")
    output = tmp_path / "results/predictions"
    generate(output)
    (output / "narratives.json").unlink()
    (output / "feature_importances.json").unlink()
    (output / "tile_predictions.csv").unlink()
    app = AppTest.from_file(str(tmp_path / "src/app.py"), default_timeout=20).run()
    app.radio[0].set_value("Real model outputs").run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "79.0%"
    assert any("No narrative" in element.value for element in app.info)
    assert any("No tile predictions" in element.value for element in app.info)
    assert not any("SYNTHETIC DEMO" in element.value for element in app.warning)
