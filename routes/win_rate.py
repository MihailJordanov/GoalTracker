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


# ---- Helpers ----
def _compute_win_rate(played: int, wins: int) -> Optional[float]:
    """Return win rate in percent or None if no matches played."""
    if played and played > 0:
        return (wins / played) * 100.0
    return None

def _row_to_player_dict(row: Tuple[Any, ...]) -> Dict[str, Any]:
    """
    Map a DB row to the public player dictionary used by the templates.
    Row order matches TEAM_PLAYERS_SQL select list.
    """
    (
        uid,
        first_name,
        last_name,
        number,
        image,
        played,
        wins,
        draws,
        losses,
        player_type,
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
    """Execute the query and return raw rows for the given team."""
    with conn.cursor() as cur:
        cur.execute(TEAM_PLAYERS_SQL, (team_id,))
        return cur.fetchall()

# ---- Public API ----
def fetch_team_players(conn, team_id: int) -> List[Dict[str, Any]]:
    """
    Return all players of the team with their stats as a list of dicts.
    Ordering is handled in SQL: by number (numeric, NULLS LAST), then last_name, then first_name.
    """
    rows = _fetch_team_player_rows(conn, team_id)
    return [_row_to_player_dict(r) for r in rows]


@win_rate_team.route("/win_rate_team/<int:team_id>")
def win_rate_team_view(team_id: int):
    """
    Показва общия win rate на отбора + индивидуалния win rate на всеки играч.
    Общият win rate се изчислява като претеглен среден:
        total_wins / total_played * 100
    (Използваме наличните полета в таблица users; ако желаеш истинска отборна метрика
     по мачове, можем да преминем към агрегиране от matches/user_match.)
    """
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

        total_played = sum(p["played_matches"] for p in players)
        total_wins   = sum(p["win_matches"]     for p in players)

        if total_played > 0:
            team_win_rate = total_wins / total_played * 100.0
        else:
            team_win_rate = None

        # Сортиране по индивидуален win rate (най-отгоре са най-високите)
        #players_sorted = sorted(
        #    players,
        #    key=lambda p: (p["win_rate"] if p["win_rate"] is not None else -1),
        #    reverse=True
        #)

        return render_template(
            "win_rate.html",
            team_id=allowed_team_id,
            team_name=team_name,
            team_win_rate=team_win_rate,
            total_played=total_played,
            total_wins=total_wins,
            players=players
        )
    finally:
        conn.close()
