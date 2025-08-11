from flask import Blueprint, render_template, request, redirect, session, flash, url_for
import psycopg2
from database.db import get_db_connection
from datetime import date

edit_match_bp = Blueprint('edit_match', __name__)


def user_has_team(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM user_team WHERE user_id = %s", (user_id,))
    has_team = cur.fetchone() is not None
    cur.close()
    conn.close()
    return has_team


def user_has_rights(match_id, user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.team_id, ut.player_type
        FROM matches m
        JOIN user_team ut ON m.team_id = ut.team_id
        WHERE m.id = %s AND ut.user_id = %s
    """, (match_id, user_id))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if not result or result[1] < 2:
        return None
    return result[0]


def get_match(match_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    match = dict(zip(columns, row))
    if isinstance(match['date'], date):
        match['date'] = match['date'].strftime('%Y-%m-%d')
    return match


def get_players_for_match(match_id, team_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.first_name, u.last_name, u.number,
            COALESCE(um.goals, 0), COALESCE(um.assists, 0), COALESCE(um.shoots, 0),
            COALESCE(um.shoots_on_target, 0), COALESCE(um.blocked_shoots, 0),
            COALESCE(um.saved_goals, 0), COALESCE(um.passes, 0), COALESCE(um.falls, 0),
            COALESCE(um.yellow_cards, 0), COALESCE(um.red_cards, 0),
            (um.match_id IS NOT NULL) AS played
        FROM users u
        LEFT JOIN user_match um ON u.id = um.user_id AND um.match_id = %s
        WHERE u.id IN (SELECT user_id FROM user_team WHERE team_id = %s)
        ORDER BY u.last_name
    """, (match_id, team_id))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0], "first_name": r[1], "last_name": r[2], "number": r[3],
            "goals": r[4], "assists": r[5], "shoots": r[6], "shoots_on_target": r[7],
            "blocked_shoots": r[8], "saved_goals": r[9], "passes": r[10], "falls": r[11],
            "yellow_cards": r[12], "red_cards": r[13], "played": r[14]
        } for r in rows
    ]


def save_match_data(match_id, team_id, match_data):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        old_data = fetch_old_user_match_data(cur, match_id)

        played_ids = [int(pid) for pid in match_data.getlist('played[]')]

        update_match_record(cur, match_id, match_data)

        insert_or_update_user_stats(cur, match_data, team_id, match_id)

        delete_unplayed_users(cur, match_id, team_id, played_ids)

        recalculate_user_stats(conn, cur, match_id, old_data)

        conn.commit()
        flash("The match was edited successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash("The match was not edited successfully!", "error")
        print("Error:", str(e))

    finally:
        cur.close()
        conn.close()


def fetch_old_user_match_data(cur, match_id):
    cur.execute("SELECT * FROM user_match WHERE match_id = %s", (match_id,))
    return cur.fetchall()


def fetch_old_result(cur, match_id):
    cur.execute("""
        SELECT home_team_result, away_team_result, home_team_penalty, away_team_penalty
        FROM matches WHERE id = %s
    """, (match_id,))
    return cur.fetchone()



def update_match_record(cur, match_id, match_data):
    cur.execute("""
        UPDATE matches
        SET home_team = %s,
            away_team = %s,
            home_team_result = %s,
            away_team_result = %s,
            location = %s,
            home_team_penalty = %s,
            away_team_penalty = %s
        WHERE id = %s
    """, (
        match_data['home_team'], match_data['away_team'],
        match_data['home_team_result'], match_data['away_team_result'],
        match_data['location'],
        match_data.get('home_team_penalty', 0),
        match_data.get('away_team_penalty', 0),
        match_id
    ))


def fetch_new_result(cur, match_id):
    cur.execute("SELECT home_team_result, away_team_result, home_team_penalty, away_team_penalty FROM matches WHERE id = %s", (match_id,))
    return cur.fetchone()


def get_outcome(home, away, pen_home, pen_away):
    if home > away:
        return 'win'
    elif home < away:
        return 'lose'
    else:
        if pen_home is not None and pen_away is not None and pen_home != pen_away:
            return 'win' if pen_home > pen_away else 'lose'
        return 'draw'


def insert_or_update_user_stats(cur, match_data, team_id, match_id):
    
    ALLOWED_STATS = {"goals","assists","shoots","shoots_on_target","blocked_shoots",
                    "saved_goals","passes","falls","yellow_cards","red_cards"}
    for key, raw in match_data.items():
        if not key.startswith("player_"):
            continue
        # разделяне отдясно: player_<stat>_<uid>, като <stat> може да съдържа "_"
        try:
            stat, uid_s = key[len("player_"):].rsplit("_", 1)
            if stat not in ALLOWED_STATS:
                continue
            uid = int(uid_s)
            value = int(raw) if str(raw).strip() != "" else 0
        except Exception:
            continue
        cur.execute(f"""
            INSERT INTO user_match (user_id, team_id, match_id, {stat})
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, match_id) DO UPDATE SET {stat} = EXCLUDED.{stat}
        """, (uid, team_id, match_id, value))



def delete_unplayed_users(cur, match_id, team_id, played_ids):
    if played_ids:
        placeholders = ','.join(['%s'] * len(played_ids))
        cur.execute(f"""
            DELETE FROM user_match
            WHERE match_id = %s AND team_id = %s AND user_id NOT IN ({placeholders})
        """, [match_id, team_id] + played_ids)
        

def recalculate_user_stats(conn, cur, match_id, old_data):
    # Кои са старите и новите участници?
    old_user_ids = set(row[1] for row in old_data)  # row[1] = user_id от старата снимка
    cur.execute("SELECT DISTINCT user_id FROM user_match WHERE match_id = %s", (match_id,))
    new_user_ids = set(r[0] for r in cur.fetchall())

    affected_user_ids = old_user_ids | new_user_ids

    # 1) Пресметни изхода на мача (ако се е променил, ще го отчетем долу при win/draw/lose)
    cur.execute("""
        SELECT home_team_result, away_team_result, home_team_penalty, away_team_penalty
        FROM matches WHERE id = %s
    """, (match_id,))
    new_result = cur.fetchone()


    # 2) За всеки засегнат потребител преизчисли всички агрегати от user_match
    for uid in affected_user_ids:
        # totals
        cur.execute("""
            SELECT
                COALESCE(SUM(goals),0),
                COALESCE(SUM(assists),0),
                COALESCE(SUM(shoots),0),
                COALESCE(SUM(shoots_on_target),0),
                COALESCE(SUM(blocked_shoots),0),
                COALESCE(SUM(saved_goals),0),
                COALESCE(SUM(passes),0),
                COALESCE(SUM(falls),0)
            FROM user_match
            WHERE user_id = %s
        """, (uid,))
        totals = cur.fetchone()  # 8 стойности

        stats = ['goals','assists','shoots','shoots_on_target','blocked_shoots','saved_goals','passes','falls']
        for i, stat in enumerate(stats):
            cur.execute(f"UPDATE users SET max_{stat} = %s WHERE id = %s", (totals[i], uid))

        # max in one match
        cur.execute("""
            SELECT
                COALESCE(MAX(goals),0),
                COALESCE(MAX(assists),0),
                COALESCE(MAX(shoots),0),
                COALESCE(MAX(shoots_on_target),0),
                COALESCE(MAX(blocked_shoots),0),
                COALESCE(MAX(saved_goals),0),
                COALESCE(MAX(passes),0),
                COALESCE(MAX(falls),0)
            FROM user_match
            WHERE user_id = %s
        """, (uid,))
        maxes = cur.fetchone()
        for i, stat in enumerate(stats):
            cur.execute(f"UPDATE users SET max_{stat}_in_one_match = %s WHERE id = %s", (maxes[i], uid))

        # hat-tricks (общ брой в историята)
        cur.execute("SELECT goals FROM user_match WHERE user_id = %s", (uid,))
        goals_list = [r[0] for r in cur.fetchall()]
        total_hat_tricks = sum(g // 3 for g in goals_list)
        cur.execute("UPDATE users SET max_hat_tricks = %s WHERE id = %s", (total_hat_tricks, uid))

        # played_matches (брой мачове с ред в user_match)
        cur.execute("SELECT COUNT(DISTINCT match_id) FROM user_match WHERE user_id = %s", (uid,))
        played = cur.fetchone()[0] or 0
        cur.execute("UPDATE users SET played_matches = %s WHERE id = %s", (played, uid))

        # win/draw/lose — броим по изхода на всеки мач от таблица matches
        # (ползваме същата логика за penalties)
        cur.execute("""
            SELECT m.home_team_result, m.away_team_result, m.home_team_penalty, m.away_team_penalty
            FROM user_match um
            JOIN matches m ON m.id = um.match_id
            WHERE um.user_id = %s
        """, (uid,))
        wins = draws = loses = 0
        for h, a, ph, pa in cur.fetchall():
            if h > a:
                wins += 1
            elif h < a:
                loses += 1
            else:
                if ph is not None and pa is not None and ph != pa:
                    if ph > pa: wins += 1
                    else: loses += 1
                else:
                    draws += 1

        cur.execute("""
            UPDATE users
            SET win_matches = %s, draw_matches = %s, lose_matches = %s
            WHERE id = %s
        """, (wins, draws, loses, uid))


def get_match_result(match_id, cur):
    cur.execute("SELECT home_team_result, away_team_result FROM matches WHERE id = %s", (match_id,))
    result = cur.fetchone()
    if not result:
        return None

    home, away = result
    if home > away:
        return 'win'
    elif home < away:
        return 'lose'
    else:
        return 'draw'


def get_user_match_rows(match_id, cur):
    cur.execute("SELECT * FROM user_match WHERE match_id = %s", (match_id,))
    return cur.fetchall()


def recompute_user_aggregates(cur, uid):
    stats = ['goals','assists','shoots','shoots_on_target','blocked_shoots','saved_goals','passes','falls']

    # totals
    cur.execute(f"""
        SELECT
            COALESCE(SUM(goals),0), COALESCE(SUM(assists),0), COALESCE(SUM(shoots),0),
            COALESCE(SUM(shoots_on_target),0), COALESCE(SUM(blocked_shoots),0),
            COALESCE(SUM(saved_goals),0), COALESCE(SUM(passes),0), COALESCE(SUM(falls),0)
        FROM user_match WHERE user_id = %s
    """, (uid,))
    totals = cur.fetchone()
    for i, stat in enumerate(stats):
        cur.execute(f"UPDATE users SET max_{stat} = %s WHERE id = %s", (totals[i], uid))

    # max in one match
    cur.execute(f"""
        SELECT
            COALESCE(MAX(goals),0), COALESCE(MAX(assists),0), COALESCE(MAX(shoots),0),
            COALESCE(MAX(shoots_on_target),0), COALESCE(MAX(blocked_shoots),0),
            COALESCE(MAX(saved_goals),0), COALESCE(MAX(passes),0), COALESCE(MAX(falls),0)
        FROM user_match WHERE user_id = %s
    """, (uid,))
    maxes = cur.fetchone()
    for i, stat in enumerate(stats):
        cur.execute(f"UPDATE users SET max_{stat}_in_one_match = %s WHERE id = %s", (maxes[i], uid))

    # hat-tricks
    cur.execute("SELECT goals FROM user_match WHERE user_id = %s", (uid,))
    total_hat_tricks = sum((r[0] or 0)//3 for r in cur.fetchall())
    cur.execute("UPDATE users SET max_hat_tricks = %s WHERE id = %s", (total_hat_tricks, uid))

    # played matches
    cur.execute("SELECT COUNT(DISTINCT match_id) FROM user_match WHERE user_id = %s", (uid,))
    played = cur.fetchone()[0] or 0
    cur.execute("UPDATE users SET played_matches = %s WHERE id = %s", (played, uid))

    # W/D/L – според всички мачове на този потребител
    cur.execute("""
        SELECT m.home_team, m.away_team, m.home_team_result, m.away_team_result,
               m.home_team_penalty, m.away_team_penalty, ut.team_id
        FROM user_match um
        JOIN matches m ON m.id = um.match_id
        JOIN user_team ut ON ut.user_id = um.user_id
        WHERE um.user_id = %s
    """, (uid,))
    wins = draws = loses = 0
    rows = cur.fetchall()

    # !!! ВАЖНО:
    # Ако вашият отбор не е винаги "home", тук трябва да знаем дали
    # нашият отбор е home или away в дадения мач (напр. чрез сравнение с името
    # на отбора или чрез отделна колона). Временно предполагаме, че "home_team"
    # е вашият отбор. Ако това НЕ е вярно, добави проверка кой е нашият отбор
    # и сравнявай съответните резултати.
    for home_team, away_team, h, a, ph, pa, team_id in rows:
        # TODO: ако вашият отбор е away, размени h/a за коректно броене
        if h > a:
            wins += 1
        elif h < a:
            loses += 1
        else:
            if ph is not None and pa is not None and ph != pa:
                if ph > pa: wins += 1
                else: loses += 1
            else:
                draws += 1

    cur.execute("""
        UPDATE users
        SET win_matches = %s, draw_matches = %s, lose_matches = %s
        WHERE id = %s
    """, (wins, draws, loses, uid))


@edit_match_bp.route('/delete-match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please sign in.", "error")
        return redirect(url_for('auth.index'))

    team_id = user_has_rights(match_id, user_id)
    if not team_id:
        flash("You do not have permission to delete this match.", "error")
        return redirect(url_for('home_bp.home'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # кои потребители са засегнати от този мач
        rows = get_user_match_rows(match_id, cur)
        affected_user_ids = set(row[1] for row in rows)

        # изтрий статистиките за този мач
        cur.execute("DELETE FROM user_match WHERE match_id = %s", (match_id,))

        # изтрий самия мач
        cur.execute("DELETE FROM matches WHERE id = %s", (match_id,))

        # преизчисли „от нулата“ за всеки засегнат потребител (по всички останали мачове)
        for uid in affected_user_ids:
            recompute_user_aggregates(cur, uid)  # виж функцията по-долу

        conn.commit()
        flash("Match deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash("Failed to delete match.", "error")
        print("Error:", str(e))
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('match_history_bp.match_history'))


@edit_match_bp.route('/edit-match/<int:match_id>', methods=['GET', 'POST'])
def edit_match(match_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please sign in.", "error")
        return redirect(url_for('auth.index'))

    team_id = user_has_rights(match_id, user_id)
    if not team_id:
        flash("You do not have permission to edit this match.", "error")
        return redirect(url_for('home_bp.home'))

    if not user_has_team(user_id):
        flash("You must have a team to edit a match.", "error")
        return redirect(url_for('home_bp.home'))

    if request.method == 'POST':
        save_match_data(match_id, team_id, request.form)
        return redirect(url_for('match_history_bp.match_history'))

    match = get_match(match_id)
    players = get_players_for_match(match_id, team_id)
    return render_template('edit_match.html', match=match, players=players)
