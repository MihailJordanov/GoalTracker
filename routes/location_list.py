from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from database.db import get_db_connection

location_bp = Blueprint('location', __name__)

def user_logged_in():
    return 'user_id' in session

def check_access(user_id, team_id):
    has_permission, message = check_user_permissions(user_id, team_id)
    if not has_permission:
        flash(message, 'error')
        return False
    return True

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

def get_team_or_redirect(team_id):
    team = get_team_by_id(team_id)
    if not team:
        flash("Team not found!", 'error')
        return None
    return team

def handle_add_location(team_id):
    country = request.form.get('country') or None
    city = request.form.get('city') or None
    name = request.form.get('name')

    if not name:
        return "Name is required.", False

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO locations (team_id, country, city, name)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (team_id, country, city, name))
    location_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return f"Location '{name}' added successfully!", True

def get_team_locations(team_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, country, city, name FROM locations WHERE team_id = %s ORDER BY id DESC;", (team_id,))
    locations = cur.fetchall()
    cur.close()
    conn.close()
    return locations


@location_bp.route('/team/<int:team_id>/locations', methods=['GET', 'POST'])
def location_list(team_id):
    if not user_logged_in():
        flash('Please log in to manage locations.', 'error')
        return redirect(url_for('auth.index'))

    user_id = session['user_id']

    if not check_access(user_id, team_id):
        flash("You don't have access to this team.", 'error')
        return redirect(url_for('home_bp.home'))

    team = get_team_or_redirect(team_id)
    if not team:
        return redirect(url_for('home_bp.home'))

    if request.method == 'POST':
        message, success = handle_add_location(team_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        return redirect(url_for('location.location_list', team_id=team_id)) 

    locations = get_team_locations(team_id)

    return render_template(
        'location_list.html',
        team=team,
        locations=locations
    )
