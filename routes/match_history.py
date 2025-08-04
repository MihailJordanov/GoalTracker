import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import psycopg2
from datetime import datetime, date 
from database.db import get_db_connection

match_history_bp = Blueprint('match_history_bp', __name__)
    
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
        SELECT m.id, m.team_id, m.type, m.schema, m.home_team,
            et.name AS away_team,
            m.home_team_result, m.away_team_result,
            m.home_team_penalty, m.away_team_penalty,
            m.date, m.location, m.format,
            t.logo AS home_team_logo,
            et.image AS away_team_logo
        FROM matches m
        JOIN teams t ON m.team_id = t.id
        LEFT JOIN enemy_teams et ON m.enemy_team_id = et.id
        WHERE m.team_id = %s
        ORDER BY m.date DESC
        LIMIT 100;
    """, (team_id,))

    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    matches = [dict(zip(columns, row)) for row in rows]

    for match in matches:
        # Форматиране на дата и час
        if isinstance(match['date'], (datetime, date)):
            match_date = match['date']
            match['date_str'] = match_date.strftime('%d-%m-%y')
            match['time_str'] = match_date.strftime('%H:%M')

        # Определяне на изхода
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

        # Преобразуване на логата
        if match.get('home_team_logo'):
            match['home_team_logo'] = url_for('static', filename=f'uploads/{match["home_team_logo"]}')
        
        if match.get('away_team_logo'):
            if not match['away_team_logo'].startswith('http'):
                match['away_team_logo'] = url_for('static', filename=f'uploads/{match["away_team_logo"]}')


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

    cur.execute("""
        SELECT um.*, u.first_name, u.last_name, u.number
        FROM user_match um
        JOIN users u ON u.id = um.user_id
        WHERE um.match_id = %s;
    """, (match_id,))

    user_id = session.get('user_id')
    player_type = get_user_player_type_for_match(user_id, match_id) if user_id else 0   
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    players = [dict(zip(columns, row)) for row in rows]

    cur.close()
    conn.close()

    return render_template('partials/player_stats.html', players=players, match_id=match_id, player_type=player_type)
