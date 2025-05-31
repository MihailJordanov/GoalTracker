import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import psycopg2
from datetime import datetime
from database.db import get_db_connection
import traceback

add_match_bp = Blueprint('add_match_bp', __name__)

@add_match_bp.route('/add_match')
def go_to_add_match():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Check if user has player_type > 0
    cur.execute("SELECT player_type FROM user_team WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    if not result or result[0] <= 0:
        flash("You do not have permission to access this page.", "error")
        cur.close()
        conn.close()
        return redirect(url_for('home_bp.home'))

    cur.close()
    conn.close()
    return render_template('add_match.html')


# 1. Get team and player type
def get_user_team(cur, user_id):
    cur.execute("SELECT player_type, team_id FROM user_team WHERE user_id = %s", (user_id,))
    return cur.fetchone()

# 2. Insert new match and return match_id
def insert_match(cur, team_id, match_type, schema, home_team, away_team,
                 home_result, away_result, match_date, location, match_format,
                 home_penalty, away_penalty, enemy_team_id):
    cur.execute("""
        INSERT INTO matches (
            team_id, type, schema, home_team, away_team,
            home_team_result, away_team_result,
            date, location, format,
            home_team_penalty, away_team_penalty, enemy_team_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        team_id, match_type, schema, home_team, away_team,
        home_result, away_result, match_date, location, match_format,
        home_penalty, away_penalty, enemy_team_id
    ))
    return cur.fetchone()[0]


# 3. Get players from team
def get_team_players(cur, team_id):
    cur.execute("""
        SELECT u.id FROM users u
        JOIN user_team ut ON ut.user_id = u.id
        WHERE ut.team_id = %s
    """, (team_id,))
    return [row[0] for row in cur.fetchall()]

# 4. Extract player stats from form
def get_user_stats_from_form(request, uid):
    return {
        'goals': int(request.form.get(f'goals_{uid}', 0)),
        'assists': int(request.form.get(f'assists_{uid}', 0)),
        'shoots': int(request.form.get(f'shoots_{uid}', 0)),
        'shoots_on_target': int(request.form.get(f'shoots_on_target_{uid}', 0)),
        'blocked_shoots': int(request.form.get(f'blocked_shoots_{uid}', 0)),
        'saved_goals': int(request.form.get(f'saved_goals_{uid}', 0)),
        'passes': int(request.form.get(f'passes_{uid}', 0)),
        'falles': int(request.form.get(f'falles_{uid}', 0)),
        'yellow_cards': int(request.form.get(f'yellow_cards_{uid}', 0)),
        'red_cards': int(request.form.get(f'red_cards_{uid}', 0)),
    }

# 5. Insert player stats
def insert_user_match(cur, uid, team_id, match_id, stats):
    cur.execute("""
        INSERT INTO user_match (
            user_id, team_id, match_id, goals, assists, shoots, shoots_on_target, blocked_shoots,
            saved_goals, passes, falls, yellow_cards, red_cards
        ) VALUES (
            %(user_id)s, %(team_id)s, %(match_id)s, %(goals)s, %(assists)s, %(shoots)s, %(shoots_on_target)s, %(blocked_shoots)s,
            %(saved_goals)s, %(passes)s, %(falles)s, %(yellow_cards)s, %(red_cards)s
        )
    """, {**stats, 'user_id': uid, 'team_id': team_id, 'match_id': match_id})

# 6. Update totals
def update_user_totals(cur, uid, stats, home_result, away_result, home_penalty, away_penalty):
    # Определяме изход от мача
    if home_result > away_result:
        outcome = 'win'
    elif home_result < away_result:
        outcome = 'loss'
    else:
        # Ако има дузпи с различен резултат
        if home_penalty != away_penalty:
            outcome = 'win' if home_penalty > away_penalty else 'loss'
        else:
            outcome = 'draw'

    # Построяваме SQL по изхода
    cur.execute(f"""
        UPDATE users SET
            max_goals = max_goals + %(goals)s,
            max_assists = max_assists + %(assists)s,
            played_matches = played_matches + 1,
            max_passes = max_passes + %(passes)s,
            max_hat_tricks = max_hat_tricks + (%(goals)s / 3)::int,
            win_matches = win_matches + {1 if outcome == 'win' else 0},
            draw_matches = draw_matches + {1 if outcome == 'draw' else 0},
            lose_matches = lose_matches + {1 if outcome == 'loss' else 0}
        WHERE id = %(user_id)s
    """, {**stats, 'user_id': uid})


# 7. Update max per match (if not training)
def update_user_max_per_match(cur, uid, stats):
    cur.execute("""
        UPDATE users SET
            max_goals_in_one_match = GREATEST(max_goals_in_one_match, %(goals)s),
            max_assists_in_one_match = GREATEST(max_assists_in_one_match, %(assists)s),
            max_passes_in_one_match = GREATEST(max_passes_in_one_match, %(passes)s)
        WHERE id = %(user_id)s
    """, {**stats, 'user_id': uid})



def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default
    

    
@add_match_bp.route('/addMatches', methods=['POST'])
def add_matches():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        user_info = get_user_team(cur, user_id)
        if not user_info or user_info[0] <= 0:
            flash("You do not have permission to add matches.", "error")
            return redirect(url_for('home_bp.home'))

        team_id = user_info[1]

        # Взимане на данни от формата
        match_type = request.form.get('type')
        schema = request.form.get('schema')
        match_format = int(request.form.get('format'))
        home_team = request.form.get('team_one')
        home_result = int(request.form.get('team_one_result'))
        away_result = int(request.form.get('team_two_result'))
        home_penalty = safe_int(request.form.get('home_team_penalty'))
        away_penalty = safe_int(request.form.get('away_team_penalty'))
        date = request.form.get('date')
        location = request.form.get('location')
        match_date = datetime.fromisoformat(date)

        # Взимаме enemy_team_id (ID от селекцията)
        raw_enemy_team_id = request.form.get('enemy_team_id')
        enemy_team_id = int(raw_enemy_team_id) if raw_enemy_team_id and raw_enemy_team_id.strip().isdigit() else None

        # Взимаме името на отбора (away_team) по ID
        away_team = None
        if enemy_team_id is not None:
            cur.execute("SELECT name FROM enemy_teams WHERE id = %s", (enemy_team_id,))
            result = cur.fetchone()
            if result:
                away_team = result[0]

        # Вмъкваме мача
        match_id = insert_match(cur, team_id, match_type, schema, home_team, away_team,
                                home_result, away_result, match_date, location, match_format,
                                home_penalty, away_penalty, enemy_team_id)

        players = get_team_players(cur, team_id)

        for uid in players:
            if not request.form.get(f'played_{uid}'):
                continue

            stats = get_user_stats_from_form(request, uid)
            insert_user_match(cur, uid, team_id, match_id, stats)
            update_user_totals(cur, uid, stats, home_result, away_result, home_penalty, away_penalty)

            if match_type != 'Training':
                update_user_max_per_match(cur, uid, stats)

        conn.commit()
        flash("Match and player statistics were successfully saved.", "success")
        return redirect(url_for('home_bp.home'))

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        error_message = str(e).encode('utf-8', errors='replace').decode()
        print("! DB ERROR:", error_message)
        import traceback
        traceback.print_exc()
        flash(f"Database error: {error_message}", "error")
        return redirect(url_for('add_match_bp.go_to_add_match'))

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Returns all teams (example)
@add_match_bp.route('/getTeams')
def get_teams():
    if 'user_id' not in session:
        return jsonify([])

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Вземаме team_id на текущия потребител
        cur.execute("SELECT team_id FROM user_team WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return jsonify([])

        team_id = result[0]

        # Вземаме enemy teams, които са свързани с този team_id
        cur.execute("""
            SELECT id, name, difficulty, image, team_code
            FROM enemy_teams
            WHERE team_id = %s
        """, (team_id,))
        rows = cur.fetchall()

        enemy_teams = []
        for row in rows:
            enemy_teams.append({
                "id": row[0],
                "name": row[1],
                "difficulty": row[2],
                "image": row[3],
                "team_code": row[4]
            })

        cur.close()
        conn.close()
        return jsonify(enemy_teams)

    except Exception as e:
        error_message = str(e).encode('utf-8', errors='replace').decode()
        print("Error while fetching enemy teams:", error_message)
        return jsonify([])

# Returns all locations (example)
@add_match_bp.route('/getLocations')
def get_locations():
    return jsonify(["Stadium A", "Stadium B", "City Park", "Training Center"])


# Returns all users from the current user's team
@add_match_bp.route('/getUsers')
def get_users():
    if 'user_id' not in session:
        return jsonify([])

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get team of the current user
        cur.execute("SELECT team_id FROM user_team WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return jsonify([])

        team_id = result[0]

        # Get all users in that team
        cur.execute("""
            SELECT u.id, u.last_name, ut.player_type
            FROM users u
            JOIN user_team ut ON u.id = ut.user_id
            WHERE ut.team_id = %s
        """, (team_id,))
        rows = cur.fetchall()

        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "last_name": row[1],
                "type": row[2]
            })

        cur.close()
        conn.close()
        return jsonify(users)

    except Exception as e:
        error_message = str(e).encode('utf-8', errors='replace').decode()
        print("Error while fetching users:", error_message)
        return jsonify([])
