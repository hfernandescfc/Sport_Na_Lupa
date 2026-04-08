from __future__ import annotations

import pandas as pd

from src.config import Settings
from src.utils.io import write_csv


def sync_teams_stub(settings: Settings, season: int) -> None:
    mapping_path = settings.processed_dir / str(season) / "clubs" / "club_mapping.csv"
    clubs_path = settings.processed_dir / str(season) / "clubs" / "clubs.csv"
    players_path = settings.processed_dir / str(season) / "clubs" / "players.csv"
    mapping_df = pd.read_csv(mapping_path)

    clubs_rows = []
    for row in mapping_df.to_dict(orient="records"):
        clubs_rows.append(
            {
                "season": season,
                "competition": "serie_b",
                "cbf_name": row["cbf_name"],
                "canonical_name": row["canonical_name"],
                "sofascore_team_id": row["sofascore_team_id"],
                "sofascore_slug": row["sofascore_slug"],
                "source_url": row["sofascore_url"],
                "mapping_status": row["mapping_status"],
                "ingested_at": "",
            }
        )

    write_csv(clubs_path, clubs_rows)
    write_csv(players_path, [])
