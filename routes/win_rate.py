# win_rate.py
from flask import Blueprint, render_template
from database.db import get_db_connection  
from routes.stats_all_players import get_logged_in_user_id, require_login_redirect 
from routes.stats_all_players import user_has_rights, no_rights_redirect     
from typing import Any, Dict, List, Optional, Tuple

win_rate_team = Blueprint("win_rate_team", __name__)

def _fetch_team_name(conn, team_id: int) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM teams WHERE id = %s", (team_id,))
        row = cur.fetchone()
        return row[0] if row else "Unknown Team"

def _fetch_team_totals(conn, team_id: int) -> Dict[str, Optional[int]]:
    """
    Чете агрегатите директно от teams:
    max_games, max_wins, max_losses, max_draws
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              COALESCE(max_games, 0),
              COALESCE(max_wins, 0),
              COALESCE(max_losses, 0),
              COALESCE(max_draws, 0)
            FROM teams
            WHERE id = %s
        """, (team_id,))
        row = cur.fetchone() or (0, 0, 0, 0)

    max_games, max_wins, max_losses, max_draws = row
    return {
        "max_games": max_games,
        "max_wins": max_wins,
        "max_losses": max_losses,
        "max_draws": max_draws,
    }

TEAM_PLAYERS_SQL = """
    SELECT
        u.id,
        u.first_name,
        u.last_name,
        u.number,
        u.image,
        COALESCE(u.played_matches, 0) AS played_matches,
        COALESCE(u.win_matches, 0)    AS win_matches,
        COALESCE(u.draw_matches, 0)   AS draw_matches,
        COALESCE(u.lose_matches, 0)   AS lose_matches,
        ut.player_type
    FROM users u
    JOIN user_team ut ON ut.user_id = u.id
    WHERE ut.team_id = %s
    ORDER BY u.number NULLS LAST, u.last_name ASC, u.first_name ASC;
"""

def _compute_win_rate(played: int, wins: int) -> Optional[float]:
    return (wins / played * 100.0) if played and played > 0 else None

def _row_to_player_dict(row: Tuple[Any, ...]) -> Dict[str, Any]:
    (
        uid, first_name, last_name, number, image,
        played, wins, draws, losses, player_type,
    ) = row
    return {
        "id": uid,
        "first_name": first_name,
        "last_name": last_name,
        "number": number,
        "image": image,
        "played_matches": played,
        "win_matches": wins,
        "draw_matches": draws,
        "lose_matches": losses,
        "player_type": player_type,
        "win_rate": _compute_win_rate(played, wins),
    }

def _fetch_team_player_rows(conn, team_id: int) -> List[Tuple[Any, ...]]:
    with conn.cursor() as cur:
        cur.execute(TEAM_PLAYERS_SQL, (team_id,))
        return cur.fetchall()

def fetch_team_players(conn, team_id: int) -> List[Dict[str, Any]]:
    rows = _fetch_team_player_rows(conn, team_id)
    return [_row_to_player_dict(r) for r in rows]

@win_rate_team.route("/win_rate_team/<int:team_id>")
def win_rate_team_view(team_id: int):
    user_id = get_logged_in_user_id()
    if not user_id:
        return require_login_redirect()

    allowed_team_id = user_has_rights(team_id, user_id)
    if not allowed_team_id:
        return no_rights_redirect()

    conn = get_db_connection()
    try:
        team_name = _fetch_team_name(conn, allowed_team_id)
        players = fetch_team_players(conn, allowed_team_id)

        # ✅ ВЗИМА СЕ ОТ teams
        t = _fetch_team_totals(conn, allowed_team_id)
        total_played = t["max_games"]
        total_wins   = t["max_wins"]
        team_win_rate = _compute_win_rate(total_played, total_wins)

        return render_template(
            "win_rate.html",
            team_id=allowed_team_id,
            team_name=team_name,
            team_win_rate=team_win_rate,
            total_played=total_played,
            total_wins=total_wins,
            players=players  # оставяме реда от SQL (по номер → last → first)
        )
    finally:
        conn.close()
