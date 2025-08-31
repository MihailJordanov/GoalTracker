import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import psycopg2
from datetime import datetime, date 
from database.db import get_db_connection
from cloudinary.utils import cloudinary_url

match_history_bp = Blueprint('match_history_bp', __name__)
    

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}

def resolve_logo(value: str | None, *, cloudinary_folder: str | None = None):
    """
    Връща URL към лого:
    - ако е пълен http(s) URL -> връща го;
    - ако е Cloudinary public_id -> връща Cloudinary URL (f_auto,q_auto);
    - иначе приема, че е локален файл в static/uploads.
    """
    if not value:
        return None

    val = str(value).strip()

    # 1) Вече е пълен URL (вкл. Cloudinary)
    if val.startswith('http://') or val.startswith('https://'):
        return val

    # 2) Изглежда като локално файлово име? (има разширение и няма папки вътре)
    _, ext = os.path.splitext(val.lower())
    looks_like_local_file = (ext in IMAGE_EXTS) and ('/' not in val and '\\' not in val)

    if looks_like_local_file:
        return url_for('static', filename=f'uploads/{val}')

    # 3) Иначе третираме като Cloudinary public_id
    public_id = f'{cloudinary_folder}/{val}' if cloudinary_folder else val
    url, _ = cloudinary_url(
        public_id,
        secure=True,
        fetch_format="auto",   # f_auto
        quality="auto",        # q_auto
        # Може да добавите трансформации (size, crop, dpr), ако искате:
        # width=256, height=256, crop="limit"
    )
    return url



def get_user_team_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT team_id FROM user_team WHERE user_id = %s;', (user_id,))
    teams = cur.fetchall()

    cur.close()
    conn.close()

    if not teams:
        return None, "Нямате създаден или присъединен отбор."
    if len(teams) > 1:
        return None, "Невъзможно е да се зареди история на мачовете, защото сте в повече от един отбор."

    return teams[0][0], None


def check_if_user_has_team(user_id):
    # Връзка с базата данни
    conn = get_db_connection()
    cur = conn.cursor()

    # Проверка дали потребителят има отбор
    cur.execute("SELECT * FROM user_team WHERE user_id = %s", (user_id,))
    existing_team = cur.fetchone()

    # Затваряне на връзката
    cur.close()
    conn.close()

    return existing_team  # Връща True, ако има отбор, или False ако няма

# Функция за проверка дали потребителят има отбор
def check_user_team(user_id):
    existing_team = check_if_user_has_team(user_id)
    if not existing_team:
        flash('You must have a team to see match history.', 'info')
        return False
    return True


def get_team_matches(team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            m.id, m.team_id, m.type, m.schema, m.home_team,
            et.name AS away_team,
            m.home_team_result, m.away_team_result,
            m.home_team_penalty, m.away_team_penalty,
            m.date,
            m.location,
            l.name   AS location_name,
            l.city   AS location_city,
            l.country AS location_country,
            m.format,
            t.logo   AS home_team_logo,   -- очакваме: public_id ИЛИ пълен URL ИЛИ локален файл
            et.image AS away_team_logo    -- очакваме: public_id ИЛИ пълен URL ИЛИ локален файл
        FROM matches m
        JOIN teams t ON m.team_id = t.id
        LEFT JOIN enemy_teams et ON m.enemy_team_id = et.id
        LEFT JOIN locations l ON l.id::text = m.location::text
        WHERE m.team_id = %s
        ORDER BY m.date DESC
        LIMIT 100;
    """, (team_id,))

    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    matches = [dict(zip(columns, row)) for row in rows]

    for match in matches:
        # Форматиране дата/час
        if isinstance(match['date'], (datetime, date)):
            match_date = match['date']
            match['date_str'] = match_date.strftime('%d-%m-%y')
            match['time_str'] = match_date.strftime('%H:%M')

        # Изход от мача
        if match['home_team_result'] > match['away_team_result']:
            match['outcome'] = 'win'
        elif match['home_team_result'] < match['away_team_result']:
            match['outcome'] = 'loss'
        else:
            home_pen = match.get('home_team_penalty')
            away_pen = match.get('away_team_penalty')
            if home_pen is not None and away_pen is not None and home_pen != away_pen:
                match['outcome'] = 'win' if home_pen > away_pen else 'loss'
            else:
                match['outcome'] = 'draw'

        # Лога (Cloudinary-first; fallback към static/uploads)
        match['home_team_logo'] = resolve_logo(match.get('home_team_logo'), cloudinary_folder=None)
        match['away_team_logo'] = resolve_logo(match.get('away_team_logo'), cloudinary_folder=None)

    cur.close()
    conn.close()
    return matches

@match_history_bp.route('/match-history')
def match_history():
    if 'user_id' not in session:
        flash('Моля, влезте в профила си.', 'error')
        return redirect(url_for('auth.index'))

    user_id = session['user_id']
    team_id, error = get_user_team_id(user_id)
    
    # Проверяваме дали потребителят има отбор
    if not check_user_team(user_id):
        return redirect(url_for('home_bp.home')) 

    if error:
        flash(error, 'error')
        return redirect(url_for('home.index'))


    matches = get_team_matches(team_id)

    return render_template('match_history.html', matches=matches)



def get_user_player_type_for_match(user_id, match_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ut.player_type
        FROM user_team ut
        JOIN matches m ON ut.team_id = m.team_id
        WHERE ut.user_id = %s AND m.id = %s
    """, (user_id, match_id))
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    return row[0] if row else 0


@match_history_bp.route('/match/<int:match_id>/players')
def match_players(match_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1) Инфо за мача: отбори, резултат, дузпи
        cur.execute("""
            SELECT 
                home_team, 
                away_team, 
                home_team_result, 
                away_team_result,
                home_team_penalty, 
                away_team_penalty
            FROM matches
            WHERE id = %s
        """, (match_id,))
        row = cur.fetchone()
        if row:
            home_team, away_team, home_res, away_res, home_pen, away_pen = row
        else:
            home_team = away_team = ""
            home_res = away_res = None
            home_pen = away_pen = None

        # 2) Статистики за играчите – сортирани по голове, после асистенции
        cur.execute("""
            SELECT um.*, u.first_name, u.last_name, u.number
            FROM user_match um
            JOIN users u ON u.id = um.user_id
            WHERE um.match_id = %s
            ORDER BY um.goals DESC, um.assists DESC, u.last_name ASC, u.first_name ASC, u.number ASC
        """, (match_id,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        players = [dict(zip(columns, r)) for r in rows]

    finally:
        cur.close()
        conn.close()

    # 3) Правата на потребителя (за бутона Edit)
    user_id = session.get('user_id')
    player_type = get_user_player_type_for_match(user_id, match_id) if user_id else 0

    # 4) Рендер към темплейта – подаваме отделните полета
    return render_template(
        'partials/player_stats.html',
        players=players,
        match_id=match_id,
        player_type=player_type,
        home_team=home_team,
        away_team=away_team,
        home_res=home_res,
        away_res=away_res,
        home_pen=home_pen,
        away_pen=away_pen
    )
