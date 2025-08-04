from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import get_db_connection
import os
import cloudinary
import cloudinary.uploader

manage_players_bp = Blueprint('manage_players_bp', __name__, template_folder='templates')

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

def get_team_players(team_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.first_name, u.last_name, u.number, u.image, um.player_type
        FROM users u
        JOIN user_team um ON u.id = um.user_id
        WHERE um.team_id = %s
        ORDER BY u.number ASC
    """, (team_id,))
    
    players = {}
    for row in cur.fetchall():
        user_id, first_name, last_name, number, image, player_type = row

        # 🔁 Обработка на пътя към изображението
        if image:
            if image.startswith("http"):
                image_url = image  # Cloudinary линк
            else:
                image_url = url_for("static", filename=f"uploads/{image}")
        else:
            image_url = None

        players[user_id] = {
            "first_name": first_name,
            "last_name": last_name,
            "number": number,
            "image": image_url,
            "player_type": player_type
        }

    cur.close()
    conn.close()
    return players

# 🔁 Рендира списъка с играчи като partial (HTML фрагмент)
@manage_players_bp.route('/team/<int:team_id>/players')
def render_players_partial(team_id):
    players = get_team_players(team_id)
    return render_template('partials/team_players_list.html', players=players, team_id=team_id)

# 🔄 POST заявка за промяна на данни на играч
@manage_players_bp.route('/team/<int:team_id>/update_player', methods=['POST'])
def update_player(team_id):
    user_id = request.form.get('user_id')
    new_number = request.form.get('number')
    new_type = request.form.get('player_type')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Вземаме текущия player_type
        cur.execute("""
            SELECT player_type FROM user_team
            WHERE user_id = %s AND team_id = %s
        """, (user_id, team_id))
        current_type = cur.fetchone()[0]

        # Обновяваме номера (винаги)
        cur.execute("UPDATE users SET number = %s WHERE id = %s", (new_number, user_id))

        # Обновяваме player_type само ако не е Creator
        if current_type != 3:
            cur.execute("""
                UPDATE user_team SET player_type = %s
                WHERE user_id = %s AND team_id = %s
            """, (new_type, user_id, team_id))

        conn.commit()
        flash("Player updated successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error updating player: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('manage_players_bp.render_players_partial', team_id=team_id))
