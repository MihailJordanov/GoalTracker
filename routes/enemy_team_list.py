import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from database.db import get_db_connection
import psycopg2.extras 
import cloudinary
import cloudinary.uploader

enemy_team_bp = Blueprint('enemy_team_bp', __name__)
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'enemy_teams')


cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# === Проверки и валидации ===

def user_logged_in():
    return 'user_id' in session

def check_access(user_id, team_id):
    has_permission, message = check_user_permissions(user_id, team_id)
    if not has_permission:
        flash(message, 'error')
        return False
    return True

def validate_enemy_team_data(name, difficulty, image):
    if not name.strip():
        return False, "Enemy team name is required."

    try:
        difficulty = int(difficulty)
        if not (1 <= difficulty <= 10):
            return False, "Difficulty must be between 1 and 10."
    except ValueError:
        return False, "Invalid difficulty format. Must be a number."

    if not image:
        return False, "Image is required."

    return True, ""

def validate_team_code_data(team_code, difficulty, user_team_code, team_id):
    if not team_code or len(team_code) != 6:
        return False, "Team code must be 6 characters."
    if team_code == user_team_code:
        return False, "You cannot add your own team as an enemy."
    if enemy_team_code_exists(team_id, team_code):
        return False, "This enemy team has already been added."
    try:
        difficulty = int(difficulty)
        if not (1 <= difficulty <= 10):
            return False, "Difficulty must be between 1 and 10."
    except ValueError:
        return False, "Invalid difficulty format."
    return True, ""

# === Основна логика ===

def handle_add_enemy_team(team_id):
    form_type = request.form.get('form_type')

    if form_type == 'manual':
        name = request.form['name']
        difficulty = request.form['difficulty']
        image = request.files['image']

        is_valid, message = validate_enemy_team_data(name, difficulty, image)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('enemy_team_bp.enemy_team_list', team_id=team_id))

        image_filename = save_image(image)
        if not image_filename:
            flash("Failed to save image.", 'error')
            return redirect(url_for('enemy_team_bp.enemy_team_list', team_id=team_id))

        save_enemy_team_to_db(team_id, name, difficulty, image_filename, '000000')
        flash('Enemy team successfully added!', 'success')

    elif form_type == 'team_code':
        team_code = request.form['team_code']
        difficulty = request.form['difficulty']

        user_team_code = get_user_team_code(team_id)

        is_valid, message = validate_team_code_data(team_code, difficulty, user_team_code, team_id)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('enemy_team_bp.enemy_team_list', team_id=team_id))

        existing_team = get_team_by_code(team_code)
        if not existing_team:
            flash("No team found with the provided code.", 'error')
            return redirect(url_for('enemy_team_bp.enemy_team_list', team_id=team_id))

        name = existing_team['name']
        image = existing_team['logo'] or ''

        save_enemy_team_to_db(team_id, name, difficulty, image, team_code)
        flash('Enemy team added from existing team!', 'success')

    return redirect(url_for('enemy_team_bp.enemy_team_list', team_id=team_id))


def save_image(image_file):
    if image_file:
        upload_result = cloudinary.uploader.upload(image_file)
        return upload_result['secure_url']  # ще запазим директния линк
    return None


def save_enemy_team_to_db(team_id, name, difficulty, image_filename, team_code):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO enemy_teams (team_id, name, difficulty, image, team_code)
        VALUES (%s, %s, %s, %s, %s)
    """, (team_id, name, difficulty, image_filename, team_code))
    conn.commit()
    cur.close()
    conn.close()

def get_team_by_code(team_code):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT name, logo FROM teams WHERE team_code = %s
    """, (team_code,))
    team = cur.fetchone()
    cur.close()
    conn.close()
    return dict(team) if team else None

def get_user_team_code(team_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT team_code FROM teams WHERE id = %s
    """, (team_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def enemy_team_code_exists(team_id, team_code):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM enemy_teams
        WHERE team_id = %s AND team_code = %s
    """, (team_id, team_code))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def get_enemy_teams(team_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT id, name, difficulty, image, team_code FROM enemy_teams
        WHERE team_id = %s
        ORDER BY id DESC
    """, (team_id,))
    teams = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in teams]

# === Методи за достъп и права ===

def check_user_permissions(user_id, team_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ut.player_type
        FROM user_team ut
        WHERE ut.user_id = %s AND ut.team_id = %s
    """, (user_id, team_id))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if not result:
        return False, "You are not associated with this team."
    if result[0] < 2:
        return False, "You don't have permission to edit this team."
    return True, ""

def get_team_by_id(team_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, logo, team_color, team_color_letters, team_image_bg, team_code
        FROM teams
        WHERE id = %s
    """, (team_id,))
    team = cur.fetchone()
    cur.close()
    conn.close()
    return team

@enemy_team_bp.route('/team/<int:team_id>/enemy_teams', methods=['GET', 'POST'])
def enemy_team_list(team_id):
    if not user_logged_in():
        flash('Please log in to manage enemy teams.', 'error')
        return redirect(url_for('auth.index'))

    user_id = session['user_id']

    if not check_access(user_id, team_id):
        return redirect(url_for('home_bp.home'))

    team = get_team_by_id(team_id)
    if not team:
        flash("Team not found!", 'error')
        return redirect(url_for('home_bp.home'))

    if request.method == 'POST':
        return handle_add_enemy_team(team_id)

    enemy_teams = get_enemy_teams(team_id)
    return render_template('enemy_team_list.html', team=team, enemy_teams=enemy_teams)
