"""Run the whole pipeline in order: M1 -> M2 -> M3 -> M4 -> screenshots."""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
(HERE.parent / "outputs" / "results.json").unlink(missing_ok=True)
for m in ["m1_data_acquisition", "m2_preprocessing", "m3_univariate_bivariate", "m4_multivariate_statistics",
          "make_screenshots"]:
    print(f"\n{'=' * 30} {m} {'=' * 30}")
    runpy.run_path(str(HERE / f"{m}.py"), run_name="__main__")
