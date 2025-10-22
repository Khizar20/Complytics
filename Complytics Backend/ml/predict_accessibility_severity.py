import argparse
import json
import os
from typing import List

import pandas as pd
from joblib import load


def get_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Predict accessibility severity using a saved model")
    p.add_argument("--model-path", required=True, help="Path to model.joblib")
    p.add_argument("--input", required=True, help="CSV file with features (no severity column required)")
    p.add_argument("--output", required=True, help="CSV path to save predictions")
    return p


def main() -> None:
    args = get_arg_parser().parse_args()
    if not os.path.exists(args.model_path):
        raise FileNotFoundError(args.model_path)

    model = load(args.model_path)
    df = pd.read_csv(args.input)

    # Expected feature columns (must match the training schema)
    cat_cols: List[str] = ["rule_id", "impact"]
    num_cols: List[str] = ["nodes", "target_text_len"]
    bool_cols: List[str] = ["has_help_url", "has_aria", "is_interactive"]

    for c in cat_cols + num_cols + bool_cols:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    X = df[cat_cols + num_cols + bool_cols]
    preds = model.predict(X)
    proba = None
    try:
        proba = model.predict_proba(X)
    except Exception:
        pass

    out = df.copy()
    out["predicted_severity"] = preds
    if proba is not None:
        # Attach max probability for quick confidence view
        import numpy as np
        out["confidence"] = np.max(proba, axis=1)

    out.to_csv(args.output, index=False)
    print(f"Saved predictions to {args.output}")


if __name__ == "__main__":
    main()


