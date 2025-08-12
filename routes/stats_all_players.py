from flask import Blueprint, render_template, session, flash, url_for, redirect
from typing import Optional, List, Dict, Tuple
from database.db import get_db_connection

stats_all_players_bp = Blueprint("stats_all_players", __name__, template_folder="templates")

# -----------------------
# Guard / auth helpers
# -----------------------



def get_team_name(team_id: int) -> str:
    """Връща името на отбора по team_id."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM teams WHERE id = %s", (team_id,))
        row = cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    return row[0] if row else f"Team #{team_id}"



def get_logged_in_user_id() -> Optional[int]:
    """Върни user_id от сесията (или None)."""
    return session.get("user_id")

def user_has_rights(team_id: int, user_id: int) -> Optional[int]:
    """
    Връща team_id ако потребителят има права (player_type >= 1) в този отбор, иначе None.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ut.team_id, ut.player_type
            FROM user_team ut
            WHERE ut.team_id = %s AND ut.user_id = %s
            LIMIT 1
        """, (team_id, user_id))
        row = cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    if not row:
        return None

    _team_id, player_type = row
    if player_type is None or player_type < 1:
        return None
    return _team_id

def require_login_redirect():
    """Флашва съобщение и връща redirect към login."""
    flash("Please sign in.", "error")
    return redirect(url_for("auth.index"))

def no_rights_redirect():
    """Флашва съобщение и връща redirect към началната страница."""
    flash("Нямаш права да преглеждаш статистиките на този отбор.", "error")
    return redirect(url_for("home_bp.home"))

# -----------------------
# Data access helpers
# -----------------------
PLAYERS_SQL = """
    SELECT
        u.id,
        u.first_name,
        u.last_name,
        u.number,
        u.image,
        u.max_goals,
        u.max_assists,
        u.max_shoots,
        u.max_shoots_on_target,
        u.max_blocked_shoots,
        u.max_saved_goals,
        u.max_passes,
        u.max_falls,
        u.played_matches,
        ut.player_type
    FROM users u
    JOIN user_team ut ON ut.user_id = u.id
    WHERE ut.team_id = %s
    ORDER BY u.number NULLS LAST, u.last_name ASC, u.first_name ASC;
"""

def fetch_players_for_team(team_id: int) -> List[Tuple]:
    """Дръпни суровите редове за играчи от отбор."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(PLAYERS_SQL, (team_id,))
        rows = cur.fetchall()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()
    return rows

def map_player_row(row: Tuple) -> Dict:
    """Превърни ред от БД в речник за шаблона."""
    (
        _id, first_name, last_name, number, image,
        max_goals, max_assists, max_shoots, max_shoots_on_target,
        max_blocked_shoots, max_saved_goals, max_passes, max_falls,
        played_matches, player_type
    ) = row

    return {
        "id": _id,
        "first_name": first_name,
        "last_name": last_name,
        "number": number,
        "image": image or "",
        "max_goals": max_goals or 0,
        "max_assists": max_assists or 0,
        "max_shoots": max_shoots or 0,
        "max_shoots_on_target": max_shoots_on_target or 0,
        "max_blocked_shoots": max_blocked_shoots or 0,
        "max_saved_goals": max_saved_goals or 0,
        "max_passes": max_passes or 0,
        "max_falls": max_falls or 0,
        "played_matches": played_matches or 0,
        "player_type": player_type
    }

def load_team_players(team_id: int) -> List[Dict]:
    """Комбинира fetch + map в удобен списък от речници."""
    return [map_player_row(r) for r in fetch_players_for_team(team_id)]

# -----------------------
# Route
# -----------------------

@stats_all_players_bp.route("/stats_all_players/<int:team_id>")
def stats_all_players(team_id: int):
    user_id = get_logged_in_user_id()
    if not user_id:
        return require_login_redirect()

    allowed_team_id = user_has_rights(team_id, user_id)
    if not allowed_team_id:
        return no_rights_redirect()

    players = load_team_players(allowed_team_id)
    team_name = get_team_name(allowed_team_id)

    return render_template(
        "stats_all_players.html",
        team_id=allowed_team_id,
        team_name=team_name,
        players=players
    )
