from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.match_history import get_team_matches
from routes.profile import get_user_from_db, format_user_data
from database.db import get_db_connection


home_bp = Blueprint('home_bp', __name__)


def fetch_user_team(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.id, t.name, t.logo, t.team_color, t.team_color_letters, t.team_image_bg, t.team_code
        FROM user_team ut
        JOIN teams t ON ut.team_id = t.id
        WHERE ut.user_id = %s
    """, (user_id,))
    team = cur.fetchone()

    cur.close()
    conn.close()
    return team


def fetch_user_teams_list(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.id, t.name
        FROM user_team ut
        JOIN teams t ON ut.team_id = t.id
        WHERE ut.user_id = %s
    """, (user_id,))
    teams = cur.fetchall()

    cur.close()
    conn.close()
    return teams


@home_bp.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))

    user_id = session['user_id']

    user_team = fetch_user_team(user_id)
    teams = fetch_user_teams_list(user_id)

    # Зареждаме последните 5 мача на отбора (ако има)
    matches = get_team_matches(user_team[0])[:5] if user_team else []

    # Зареждаме статистика за потребителя
    user_raw = get_user_from_db(user_id)
    user = format_user_data(user_raw)

    return render_template(
        'home.html',
        user_team=user_team,
        teams=teams,
        matches=matches,
        user=user  # добавяме го за статистиките
    )

