"""Compara previsões salvas vs. resultados reais e mantém o log de acurácia.

Procura por data/predictions/serie_b_{season}/round_*.csv, para cada rodada
verifica se já temos resultado real em matches.csv e, se sim, computa:
    - acerto top-1 (classe mais provável == real)
    - probabilidade dada ao resultado real (calibration check)
    - log loss e brier score
    - resumo: acurácia cumulativa rodada a rodada

Output:
    data/predictions/serie_b_{season}/accuracy_log.csv  — uma linha por (round, match)
    data/predictions/serie_b_{season}/accuracy_summary.csv — uma linha por rodada
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _real_result(home_score, away_score) -> str | None:
    if pd.isna(home_score) or pd.isna(away_score):
        return None
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def validate_predictions(base_dir: Path, season: int, logger=None) -> dict:
    """Varre data/predictions/serie_b_{season}/round_*.csv e compara com matches.csv.

    Retorna dict com paths gerados e resumo agregado.
    """
    def _log(msg: str):
        if logger is not None:
            logger.info(msg)

    pred_dir = base_dir / "data" / "predictions" / f"serie_b_{season}"
    if not pred_dir.exists():
        _log(f"[validate-predictions] diretório inexistente: {pred_dir}")
        return {"summary_path": None, "log_path": None, "rounds": []}

    matches_path = base_dir / "data" / "curated" / f"serie_b_{season}" / "matches.csv"
    if not matches_path.exists():
        raise FileNotFoundError(matches_path)

    matches = pd.read_csv(matches_path)
    # Preferir registros 'completed' quando match_code aparece duplicado no curated.
    score_lookup: dict[str, tuple] = {}
    for _, row in matches.iterrows():
        mc = row.get("match_code")
        if pd.isna(mc):
            continue
        status = row.get("status")
        existing = score_lookup.get(mc)
        if existing is not None and existing[2] == "completed" and status != "completed":
            continue
        score_lookup[mc] = (row.get("home_score"), row.get("away_score"), status)

    pattern = re.compile(r"round_(\d+)\.csv$")
    detail_rows: list[dict] = []
    round_summaries: list[dict] = []

    for csv in sorted(pred_dir.glob("round_*.csv")):
        m = pattern.search(csv.name)
        if not m:
            continue
        round_n = int(m.group(1))

        df = pd.read_csv(csv)
        if df.empty:
            continue

        results_known: list[dict] = []
        for _, row in df.iterrows():
            mc = row.get("match_code")
            if pd.isna(mc) or mc not in score_lookup:
                continue
            hs, as_, status = score_lookup[mc]
            if status != "completed":
                continue
            real = _real_result(hs, as_)
            if real is None:
                continue
            probs = {"A": row["prob_away"], "D": row["prob_draw"], "H": row["prob_home"]}
            predicted = row["predicted_result"]
            correct = int(predicted == real)
            real_prob = float(probs[real])
            # Brier multi-classe (simplificado)
            real_onehot = {k: (1.0 if k == real else 0.0) for k in "ADH"}
            brier = float(sum((probs[k] - real_onehot[k]) ** 2 for k in "ADH"))
            results_known.append({
                "season": season,
                "round": round_n,
                "match_code": mc,
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "predicted": predicted,
                "real": real,
                "correct": correct,
                "max_prob": float(row["max_probability"]),
                "prob_real": real_prob,
                "brier": brier,
                "home_score": hs,
                "away_score": as_,
            })

        if not results_known:
            _log(f"[validate-predictions] R{round_n}: sem jogos concluídos ainda")
            continue

        detail_rows.extend(results_known)
        rdf = pd.DataFrame(results_known)
        round_summaries.append({
            "season": season,
            "round": round_n,
            "n_matches_predicted": len(df),
            "n_matches_completed": len(rdf),
            "accuracy": float(rdf["correct"].mean()),
            "mean_prob_real": float(rdf["prob_real"].mean()),
            "mean_brier": float(rdf["brier"].mean()),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        })
        _log(
            f"[validate-predictions] R{round_n}: "
            f"{int(rdf['correct'].sum())}/{len(rdf)} = {rdf['correct'].mean():.1%} acerto"
        )

    if not detail_rows:
        return {"summary_path": None, "log_path": None, "rounds": []}

    log_df = pd.DataFrame(detail_rows)
    summary_df = pd.DataFrame(round_summaries)
    # Acurácia cumulativa
    summary_df = summary_df.sort_values("round").reset_index(drop=True)
    summary_df["cumulative_correct"] = (summary_df["n_matches_completed"] * summary_df["accuracy"]).cumsum()
    summary_df["cumulative_n"] = summary_df["n_matches_completed"].cumsum()
    summary_df["cumulative_accuracy"] = summary_df["cumulative_correct"] / summary_df["cumulative_n"]

    log_path = pred_dir / "accuracy_log.csv"
    summary_path = pred_dir / "accuracy_summary.csv"
    log_df.to_csv(log_path, index=False)
    summary_df.to_csv(summary_path, index=False)

    _log(
        f"[validate-predictions] cumulativo: "
        f"{int(summary_df['cumulative_correct'].iloc[-1])}/{int(summary_df['cumulative_n'].iloc[-1])} = "
        f"{summary_df['cumulative_accuracy'].iloc[-1]:.1%}"
    )

    return {
        "summary_path": summary_path,
        "log_path": log_path,
        "rounds": summary_df.to_dict(orient="records"),
    }
