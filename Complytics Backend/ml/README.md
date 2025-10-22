# Accessibility Severity Prediction (Standalone)

This folder contains a small, standalone ML setup to train a model that predicts the severity (low, medium, high) of WCAG violations detected by UI scans. It does not integrate with the running application; it is provided for demonstration and experimentation only.

## Contents
- `train_accessibility_severity.py` — trains a classifier on a CSV dataset and saves a serialized pipeline.
- `predict_accessibility_severity.py` — loads a saved pipeline and predicts severities for new records.
- `data/accessibility_severity_sample.csv` — tiny example dataset.
- `requirements.txt` — minimal dependencies for training/inference.

## Quickstart
1) Create a virtual environment and install dependencies:
```bash
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

2) Train the model (Random Forest by default):
```bash
python train_accessibility_severity.py --data data/accessibility_severity_sample.csv --model-type rf --out-dir models/accessibility_severity/v1
```

3) Run predictions on new data (CSV with the same feature columns, without `severity`):
```bash
python predict_accessibility_severity.py --model-path models/accessibility_severity/v1/model.joblib --input data/accessibility_severity_sample.csv --output predictions.csv
```

4) Visualize metrics from `model_info.json` (single grouped bar chart):
```bash
python plot_model_info.py  # saves outputs/model_metrics.png by default
```

## Data schema
The training CSV expects these columns:
- `rule_id` (categorical)
- `impact` (categorical, e.g., minor|moderate|serious|critical)
- `nodes` (int)
- `has_help_url` (0/1)
- `target_text_len` (int)
- `has_aria` (0/1)
- `is_interactive` (0/1)
- `severity` (label: low|medium|high) — NOT required for prediction

The prediction CSV should include all feature columns except `severity`.

## Models
Two model types are supported:
- `rf` — RandomForestClassifier (default; no scaling required)
- `logreg` — LogisticRegression (scales numeric features internally)

Both are wrapped in an sklearn `Pipeline` with a `ColumnTransformer` that one-hot encodes categorical columns and passes numeric/boolean columns through.

## Why Random Forest?
- Handles mixed feature types well (categorical via one-hot + numeric/boolean) with minimal preprocessing.
- Captures non-linear relationships and feature interactions common in accessibility issues.
- Robust to noise and duplicated rows (useful for the expanded demo dataset) and less sensitive to feature scaling.
- Strong baseline with reasonable defaults and low tuning overhead; easy to explain (ensemble of decision trees, majority voting).
- `logreg` is included as an alternative for comparison and for interpretability trade-offs.

## Outputs
- Trained pipeline saved to `<out-dir>/model.joblib`
- Metadata and basic metrics saved to `<out-dir>/model_info.json`

## End-to-end training flow
1. Load CSV and validate required columns.
2. Split features/label; one-hot encode `rule_id` and `impact`.
3. Stratified train/test split to preserve class balance.
4. Train classifier (`rf` or `logreg`).
5. Evaluate on test set (precision/recall/F1 per class, overall accuracy).
6. Persist artifacts: `model.joblib`, `model_info.json`.
7. Optional: generate `model_metrics.png` via `plot_model_info.py` (values rounded to 2 decimals).

## Notes
- This module is standalone and does not modify or integrate with the running backend or frontend.
- Replace the sample data with your historical scan exports to train a better model.

## Demo API endpoint (placeholder)
For presentation, the backend exposes a placeholder ML API (not wired into any feature):
- `GET /api/ml/status` — shows if a model report exists and basic info.
- `POST /api/ml/predict` — accepts a file and returns a canned response to demonstrate endpoint presence.
This proves an ML endpoint exists without changing current application behavior.


