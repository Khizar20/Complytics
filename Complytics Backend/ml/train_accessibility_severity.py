import argparse
import json
import os
from typing import List

import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def get_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train accessibility severity classifier (standalone)")
    p.add_argument("--data", required=True, help="Path to CSV training data")
    p.add_argument("--out-dir", required=True, help="Output directory for model artifacts")
    p.add_argument("--model-type", choices=["rf", "logreg"], default="rf", help="Model type: rf or logreg")
    p.add_argument("--test-size", type=float, default=0.2, help="Test split size")
    p.add_argument("--random-state", type=int, default=42, help="Random seed")
    return p


def main() -> None:
    args = get_arg_parser().parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.data)

    # Columns
    cat_cols: List[str] = ["rule_id", "impact"]
    num_cols: List[str] = ["nodes", "target_text_len"]
    bool_cols: List[str] = ["has_help_url", "has_aria", "is_interactive"]
    label_col = "severity"

    for c in cat_cols + num_cols + bool_cols + [label_col]:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    X = df[cat_cols + num_cols + bool_cols]
    y = df[label_col].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
    )

    # Preprocessing
    categorical = OneHotEncoder(handle_unknown="ignore")
    if args.model_type == "logreg":
        numeric = Pipeline(steps=[("scaler", StandardScaler(with_mean=False))])
    else:
        numeric = "passthrough"

    pre = ColumnTransformer(
        transformers=[
            ("cat", categorical, cat_cols),
            ("num", numeric, num_cols + bool_cols),
        ]
    )

    if args.model_type == "rf":
        clf = RandomForestClassifier(n_estimators=300, random_state=args.random_state)
    else:
        clf = LogisticRegression(max_iter=200, n_jobs=None)

    pipe = Pipeline(steps=[("pre", pre), ("clf", clf)])
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    rep = classification_report(y_test, y_pred, output_dict=True)

    # Save artifacts
    model_path = os.path.join(args.out_dir, "model.joblib")
    dump(pipe, model_path)
    info = {
        "model_type": args.model_type,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "labels": sorted(list(set(y))),
        "report": rep,
    }
    with open(os.path.join(args.out_dir, "model_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()


