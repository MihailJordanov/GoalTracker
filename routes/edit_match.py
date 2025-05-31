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
        all_played_before = set(row[1] for row in old_data)

        played_ids = [int(pid) for pid in match_data.getlist('played[]')]
        played_now = set(played_ids)
        removed_ids = list(all_played_before - played_now)
        added_ids = list(played_now - all_played_before)

        old_result = fetch_old_result(cur, match_id)

        reduce_old_stats(cur, old_data, removed_ids)

        update_match_record(cur, match_id, match_data)


        new_result = fetch_new_result(cur, match_id)
        outcome = get_outcome(*new_result)

        insert_or_update_user_stats(cur, match_data, team_id, match_id)

        delete_unplayed_users(cur, match_id, team_id, played_ids)

        recalculate_user_stats(conn, cur, match_id, old_result, old_data)

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


def reduce_old_stats(cur, old_data, removed_ids):
    for row in old_data:
        user_id = row[1]
        if user_id not in removed_ids:
            continue  # Само за премахнати

        stats = {
            'goals': row[4], 'assists': row[5], 'shoots': row[6],
            'shoots_on_target': row[7], 'blocked_shoots': row[8],
            'saved_goals': row[9], 'passes': row[10], 'falls': row[11]
        }
        for stat, value in stats.items():
            cur.execute(f"UPDATE users SET max_{stat} = GREATEST(0, max_{stat} - %s) WHERE id = %s", (value, user_id))

        # Намаляване на изиграни мачове – само ако е премахнат
        cur.execute("UPDATE users SET played_matches = GREATEST(0, played_matches - 1) WHERE id = %s", (user_id,))


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


def update_user_match_outcome(cur, user_ids, old_outcome, new_outcome):
    for user_id in user_ids:
        if old_outcome:
            if old_outcome == 'win':
                cur.execute("UPDATE users SET win_matches = GREATEST(0, win_matches - 1) WHERE id = %s", (user_id,))
            elif old_outcome == 'draw':
                cur.execute("UPDATE users SET draw_matches = GREATEST(0, draw_matches - 1) WHERE id = %s", (user_id,))
            elif old_outcome == 'lose':
                cur.execute("UPDATE users SET lose_matches = GREATEST(0, lose_matches - 1) WHERE id = %s", (user_id,))
        if new_outcome:
            if new_outcome == 'win':
                cur.execute("UPDATE users SET win_matches = win_matches + 1 WHERE id = %s", (user_id,))
            elif new_outcome == 'draw':
                cur.execute("UPDATE users SET draw_matches = draw_matches + 1 WHERE id = %s", (user_id,))
            elif new_outcome == 'lose':
                cur.execute("UPDATE users SET lose_matches = lose_matches + 1 WHERE id = %s", (user_id,))



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
    for key in match_data:
        if key.startswith('player_'):
            parts = key.split('_')
            if len(parts) >= 3 and parts[0] == 'player':
                stat = '_'.join(parts[1:-1])
                uid = int(parts[-1])
                value = int(match_data[key])
                cur.execute(f"""
                    INSERT INTO user_match (user_id, team_id, match_id, {stat})
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, match_id) DO UPDATE
                    SET {stat} = EXCLUDED.{stat}
                """, (uid, team_id, match_id, value))


def delete_unplayed_users(cur, match_id, team_id, played_ids):
    if played_ids:
        placeholders = ','.join(['%s'] * len(played_ids))
        cur.execute(f"""
            DELETE FROM user_match
            WHERE match_id = %s AND team_id = %s AND user_id NOT IN ({placeholders})
        """, [match_id, team_id] + played_ids)
        

def recalculate_user_stats(conn, cur, match_id, old_result, old_data):
    cur.execute("SELECT * FROM user_match WHERE match_id = %s", (match_id,))
    rows = cur.fetchall()
    user_stats = {}

    for row in rows:
        user_id = row[1]
        stats = {
            'goals': row[4], 'assists': row[5], 'shoots': row[6],
            'shoots_on_target': row[7], 'blocked_shoots': row[8],
            'saved_goals': row[9], 'passes': row[10], 'falls': row[11]
        }
        for stat, value in stats.items():
            cur.execute(f"UPDATE users SET max_{stat} = max_{stat} + %s WHERE id = %s", (value, user_id))
            cur.execute(f"SELECT max_{stat}_in_one_match FROM users WHERE id = %s", (user_id,))
            max_val = cur.fetchone()[0]
            if value > max_val:
                cur.execute(f"UPDATE users SET max_{stat}_in_one_match = %s WHERE id = %s", (value, user_id))

        # hat-trick
        hat_tricks = stats['goals'] // 3
        if hat_tricks > 0:
            cur.execute("UPDATE users SET max_hat_tricks = max_hat_tricks + %s WHERE id = %s", (hat_tricks, user_id))

        # played matches
        cur.execute("UPDATE users SET played_matches = played_matches + 1 WHERE id = %s", (user_id,))

    # Вземаме новия резултат (след ъпдейта)
    cur.execute("""
        SELECT home_team_result, away_team_result, home_team_penalty, away_team_penalty
        FROM matches
        WHERE id = %s
    """, (match_id,))
    new_result = cur.fetchone()


    if old_result and new_result:
        old_outcome = get_outcome(*old_result)
        new_outcome = get_outcome(*new_result)

        cur.execute("SELECT user_id FROM user_match WHERE match_id = %s", (match_id,))
        new_user_ids = set(row[0] for row in cur.fetchall())

        # Вземи user_ids, които са били в стария мач (old_data)
        cur.execute("SELECT user_id FROM user_match WHERE match_id = %s", (match_id,))
        cur.execute("SELECT DISTINCT user_id FROM user_match WHERE match_id = %s", (match_id,))
        new_user_ids = set(r[0] for r in cur.fetchall())

        cur.execute("SELECT DISTINCT user_id FROM user_match WHERE match_id = %s", (match_id,))
        cur.execute("SELECT DISTINCT user_id FROM user_match WHERE match_id = %s", (match_id,))
        cur.execute("SELECT user_id FROM user_match WHERE match_id = %s", (match_id,))
        new_user_ids = set([row[0] for row in cur.fetchall()])

        old_user_ids = set(row[1] for row in old_data)  # row[1] = user_id

        kept_users = old_user_ids & new_user_ids
        removed_users = old_user_ids - new_user_ids
        added_users = new_user_ids - old_user_ids

        # Намаляване на win/draw/lose за тези, които са били в мача, ако има промяна
        update_user_match_outcome(cur, kept_users, old_outcome, new_outcome) if old_outcome != new_outcome else None

        # Премахване само на изтрити
        update_user_match_outcome(cur, removed_users, old_outcome, None)

        # Добавяне само на нови
        update_user_match_outcome(cur, added_users, None, new_outcome)


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


def recalculate_max_stats_for_user(user_id, cur):
    stats = ['goals', 'assists', 'shoots', 'shoots_on_target', 'blocked_shoots',
             'saved_goals', 'passes', 'falls']

    for stat in stats:
        # Общо
        cur.execute(f"SELECT SUM({stat}) FROM user_match WHERE user_id = %s", (user_id,))
        total = cur.fetchone()[0] or 0
        cur.execute(f"UPDATE users SET max_{stat} = %s WHERE id = %s", (total, user_id))

        # Най-много в един мач
        cur.execute(f"SELECT MAX({stat}) FROM user_match WHERE user_id = %s", (user_id,))
        max_one = cur.fetchone()[0] or 0
        cur.execute(f"UPDATE users SET max_{stat}_in_one_match = %s WHERE id = %s", (max_one, user_id))

    # Hat-tricks
    cur.execute("SELECT goals FROM user_match WHERE user_id = %s", (user_id,))
    goals_list = [r[0] for r in cur.fetchall()]
    total_hat_tricks = sum(g // 3 for g in goals_list)
    cur.execute("UPDATE users SET max_hat_tricks = %s WHERE id = %s", (total_hat_tricks, user_id))


def apply_stat_reductions(user_id, goals, outcome, cur):
    # Намаляване на hat-tricks
    hat_tricks = goals // 3
    if hat_tricks > 0:
        cur.execute("""
            UPDATE users
            SET max_hat_tricks = GREATEST(0, max_hat_tricks - %s)
            WHERE id = %s
        """, (hat_tricks, user_id))

    # Намаляване на изиграни мачове
    cur.execute("UPDATE users SET played_matches = GREATEST(0, played_matches - 1) WHERE id = %s", (user_id,))

    # Намаляване на резултат (win/draw/lose)
    if outcome == 'win':
        cur.execute("UPDATE users SET win_matches = GREATEST(0, win_matches - 1) WHERE id = %s", (user_id,))
    elif outcome == 'draw':
        cur.execute("UPDATE users SET draw_matches = GREATEST(0, draw_matches - 1) WHERE id = %s", (user_id,))
    elif outcome == 'lose':
        cur.execute("UPDATE users SET lose_matches = GREATEST(0, lose_matches - 1) WHERE id = %s", (user_id,))



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
        outcome = get_match_result(match_id, cur)
        rows = get_user_match_rows(match_id, cur)

        # Намаляваме сборните броячи
        for row in rows:
            user_id = row[1]
            apply_stat_reductions(user_id, row[4], outcome, cur)

        # Изтриваме статистиките от user_match
        cur.execute("DELETE FROM user_match WHERE match_id = %s", (match_id,))

        # Пресмятаме новите max_*, *_in_one_match, hat-tricks
        user_ids = set(row[1] for row in rows)
        for uid in user_ids:
            recalculate_max_stats_for_user(uid, cur)

        # Изтриваме самия мач
        cur.execute("DELETE FROM matches WHERE id = %s", (match_id,))

        conn.commit()
        flash("Match deleted successfully.", "success")

    except Exception as e:
        conn.rollback()
        flash("Failed to delete match.", "error")

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
