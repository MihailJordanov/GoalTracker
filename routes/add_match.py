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

    # Проверка за права
    cur.execute("SELECT player_type FROM user_team WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    
    if result is None or result[0] is None:
        has_permission = False
    else:
        player_type = result[0]
        has_permission = player_type > 0

    if not has_permission:
        flash("You do not have permission to access this page.", "error")
        cur.close()
        conn.close()
        return redirect(url_for('home_bp.home'))



    # 🟢 Взимаме user_team
    cur.execute("""
        SELECT t.id, t.name
        FROM user_team ut
        JOIN teams t ON ut.team_id = t.id
        WHERE ut.user_id = %s
    """, (user_id,))
    user_team = cur.fetchone()

    if not user_team:
        flash("You must be part of a team to add a match.", "error")
        cur.close()
        conn.close()
        return redirect(url_for('home_bp.home'))

    cur.close()
    conn.close()

    # 🟢 Подаваме user_team към шаблона
    return render_template('add_match.html', user_team=user_team)


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
        'falls': int(request.form.get(f'falls_{uid}', 0)), 
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
            %(saved_goals)s, %(passes)s, %(falls)s, %(yellow_cards)s, %(red_cards)s
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
    

def recompute_user_aggregates_fast(cur, uid: int):
    cur.execute("""
    WITH
    totals AS (
      SELECT
        COALESCE(SUM(goals),0) g,
        COALESCE(SUM(assists),0) a,
        COALESCE(SUM(shoots),0) s,
        COALESCE(SUM(shoots_on_target),0) sot,
        COALESCE(SUM(blocked_shoots),0) bs,
        COALESCE(SUM(saved_goals),0) sg,
        COALESCE(SUM(passes),0) p,
        COALESCE(SUM(falls),0) f
      FROM user_match WHERE user_id = %s
    ),
    maxes AS (
      SELECT
        COALESCE(MAX(goals),0) g,
        COALESCE(MAX(assists),0) a,
        COALESCE(MAX(shoots),0) s,
        COALESCE(MAX(shoots_on_target),0) sot,
        COALESCE(MAX(blocked_shoots),0) bs,
        COALESCE(MAX(saved_goals),0) sg,
        COALESCE(MAX(passes),0) p,
        COALESCE(MAX(falls),0) f
      FROM user_match WHERE user_id = %s
    ),
    hts AS (
      SELECT COALESCE(SUM((goals/3)::int),0) hat FROM user_match WHERE user_id = %s
    ),
    played AS (
      SELECT COALESCE(COUNT(DISTINCT match_id),0) pm FROM user_match WHERE user_id = %s
    ),
    wdl AS (
      SELECT
        SUM(CASE 
              WHEN m.home_team_result > m.away_team_result THEN 1
              WHEN m.home_team_result < m.away_team_result THEN 0
              WHEN m.home_team_penalty IS NOT NULL AND m.away_team_penalty IS NOT NULL AND m.home_team_penalty <> m.away_team_penalty
                   THEN CASE WHEN m.home_team_penalty > m.away_team_penalty THEN 1 ELSE 0 END
              ELSE 0
            END) AS wins,
        SUM(CASE 
              WHEN m.home_team_result < m.away_team_result THEN 1
              WHEN m.home_team_result > m.away_team_result THEN 0
              WHEN m.home_team_penalty IS NOT NULL AND m.away_team_penalty IS NOT NULL AND m.home_team_penalty <> m.away_team_penalty
                   THEN CASE WHEN m.home_team_penalty < m.away_team_penalty THEN 1 ELSE 0 END
              ELSE 0
            END) AS loses,
        SUM(CASE 
              WHEN m.home_team_result = m.away_team_result AND 
                   (m.home_team_penalty IS NULL OR m.away_team_penalty IS NULL OR m.home_team_penalty = m.away_team_penalty)
                 THEN 1 ELSE 0 END) AS draws
      FROM user_match um
      JOIN matches m ON m.id = um.match_id
      WHERE um.user_id = %s
    )
    UPDATE users u
    SET
      max_goals = t.g,
      max_assists = t.a,
      max_shoots = t.s,
      max_shoots_on_target = t.sot,
      max_blocked_shoots = t.bs,
      max_saved_goals = t.sg,
      max_passes = t.p,
      max_falls = t.f,
      max_goals_in_one_match = m.g,
      max_assists_in_one_match = m.a,
      max_passes_in_one_match = m.p,
      max_hat_tricks = h.hat,
      played_matches = pl.pm,
      win_matches = w.wins,
      draw_matches = w.draws,
      lose_matches = w.loses
    FROM totals t, maxes m, hts h, played pl, wdl w
    WHERE u.id = %s
    """, (uid, uid, uid, uid, uid, uid))


    
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

        # Данни от форма
        match_type = request.form.get('type')
        schema = request.form.get('schema')
        match_format = int(request.form.get('format'))
        home_result = int(request.form.get('team_one_result'))
        away_result = int(request.form.get('team_two_result'))
        home_penalty = safe_int(request.form.get('home_team_penalty'))
        away_penalty = safe_int(request.form.get('away_team_penalty'))
        date = request.form.get('date')
        location = request.form.get('location')
        match_date = datetime.fromisoformat(date)

        # Взимаме името на нашия (home) отбор от БД по team_id
        cur.execute("SELECT name FROM teams WHERE id = %s", (team_id,))
        row = cur.fetchone()
        if row and row[0]:
            home_team_name = row[0]
        else:
            # fallback – ако по някаква причина няма запис, пробваме стойността от формата (която е име)
            home_team_name = request.form.get('team_one') or "Unknown Team"

        # Изчисляваме away team име, ако е подаден enemy_team_id
        raw_enemy_team_id = request.form.get('enemy_team_id')
        enemy_team_id = int(raw_enemy_team_id) if raw_enemy_team_id and raw_enemy_team_id.strip().isdigit() else None

        away_team_name = None
        if enemy_team_id is not None:
            cur.execute("SELECT name FROM enemy_teams WHERE id = %s", (enemy_team_id,))
            r = cur.fetchone()
            if r:
                away_team_name = r[0]

        # Вмъкваме мача – подаваме home_team_name вместо ID
        match_id = insert_match(
            cur, team_id, match_type, schema, home_team_name, away_team_name,
            home_result, away_result, match_date, location, match_format,
            home_penalty, away_penalty, enemy_team_id
        )

        # Играчите от отбора и запис на статистики
        players = get_team_players(cur, team_id)
        played_user_ids = []

        for uid in players:
            if not request.form.get(f'played_{uid}'):
                continue

            stats = get_user_stats_from_form(request, uid)
            insert_user_match(cur, uid, team_id, match_id, stats)
            played_user_ids.append(uid)

        # Преизчисляване на агрегатите за изигралите
        for uid in played_user_ids:
            recompute_user_aggregates_fast(cur, uid)

        conn.commit()
        flash("Match and player statistics were successfully saved.", "success")
        return redirect(url_for('home_bp.home'))

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        error_message = str(e).encode('utf-8', errors='replace').decode()
        print("! DB ERROR:", error_message)
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

# Returns all locations 
@add_match_bp.route('/getLocations')
def get_locations():
    if 'user_id' not in session:
        return jsonify([])

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get team_id of current user
        cur.execute("SELECT team_id FROM user_team WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return jsonify([])

        team_id = result[0]

        # Get all locations for this team
        cur.execute("""
            SELECT id, name, city, country
            FROM locations
            WHERE team_id = %s
            ORDER BY name ASC
        """, (team_id,))
        rows = cur.fetchall()

        locations = []
        for row in rows:
            loc = {
                "id": row[0],
                "name": row[1],
                "city": row[2],
                "country": row[3]
            }
            locations.append(loc)

        cur.close()
        conn.close()
        return jsonify(locations)

    except Exception as e:
        error_message = str(e).encode('utf-8', errors='replace').decode()
        print("Error while fetching locations:", error_message)
        return jsonify([])

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
            SELECT u.id, u.number, u.last_name, ut.player_type
            FROM users u
            JOIN user_team ut ON u.id = ut.user_id
            WHERE ut.team_id = %s
            ORDER BY u.number
        """, (team_id,))
        rows = cur.fetchall()

        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "number" : row[1],
                "last_name": row[2],
                "type": row[3]
            })

        cur.close()
        conn.close()
        return jsonify(users)

    except Exception as e:
        error_message = str(e).encode('utf-8', errors='replace').decode()
        print("Error while fetching users:", error_message)
        return jsonify([])
