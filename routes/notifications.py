from flask import Blueprint, request, jsonify, session, flash, redirect, url_for
from database.db import get_db_connection
import hashlib
import string
import psycopg2

notifications_bp = Blueprint('notifications_bp', __name__)


@notifications_bp.route('/get-notifications', methods=['GET'])
def get_notifications():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401  

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, type, is_read FROM notifications WHERE user_id = %s", (user_id,))
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()

    notifications_list = [
        {"id": row[0], "title": row[1], "description": row[2], "type": row[3], "is_read": row[4]}
        for row in notifications
    ]

    return jsonify(notifications_list)


@notifications_bp.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401  

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s", (notification_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True})


@notifications_bp.route('/accept-invite', methods=['POST'])
def accept_invite():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401  

    user_id = session['user_id']
    data = request.get_json()
    notification_id = data.get("notification_id")

    team_id = get_invite_details(notification_id, user_id)
    if team_id is None:
        flash("Invitation not found", "error")
        return jsonify({"error": "Invitation not found"}), 404

    if is_player_in_team(user_id):
        flash("You are already in a team!", "error")
        return jsonify({"error": "You are already in a team!"}), 400

    add_player_to_team(user_id, team_id, notification_id)

    flash("You have joined the team!", "success")
    return jsonify({"success": True})



@notifications_bp.route('/decline-invite', methods=['POST'])
def decline_invite():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401  

    user_id = session['user_id']
    data = request.get_json()
    notification_id = data.get("notification_id")  # <- Взимаме ID-то от заявката

    if not notification_id:
        print("ERROR: Missing notification_id in request!")  # Отпечатваме грешката
        return jsonify({"error": "Invalid notification ID"}), 400  

    print(f"Declining invite for notification_id: {notification_id}")  # Debug log

    delete_invite(notification_id)  # Тук беше проблемът - може би е извиквано без параметър

    flash("You declined the invitation.", "info")
    return jsonify({"success": True})

# Основна функция за поканата на играча
@notifications_bp.route('/invite-player', methods=['POST'])
def invite_player():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))  
    
    user_id = session['user_id']

    # Проверяваме дали потребителят има отбор
    if not check_user_team(user_id):
        return redirect(url_for('home_bp.home')) 

    player_hash_id = request.form.get('player_id')
    description = request.form.get('description')
    team_id = request.form.get('team_id')

    if not player_hash_id:
        flash("Player ID is required", "error")
        return redirect(url_for('home_bp.home'))

    # Намиране на реалното user_id по 6-символното ID
    matched_user_id = get_user_id_from_hash(player_hash_id)
    if not matched_user_id:
        return redirect(url_for('home_bp.home'))


    # Проверка за дължината на описанието
    if description and (len(description) > 200):
        flash("Description must be no more than 200 characters long.", "error")
        return redirect(url_for('home_bp.home'))


    # Вмъкване на нотификация
    insert_notification(matched_user_id, description, team_id)

    return redirect(url_for('home_bp.home'))




def get_user_team(user_id):
    """Функция за проверка дали потребителят има отбор"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_team WHERE user_id = %s", (user_id,))
    user_team = cur.fetchone()  # Ако няма отбор, ще бъде None
    cur.close()
    conn.close()
    return user_team


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
        flash('You must have a team to invite players.', 'info')
        return False
    return True



# Функция за намиране на user_id от 6-символното ID
def get_user_id_from_hash(player_hash_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        
        for user in users:
            if generate_user_id_from_hash(user[0]) == player_hash_id:
                return user[0]
        
        flash("No user found with this Player ID.", "error")
        return None
    except Exception as e:
        flash(f"Error while fetching user: {str(e)}", "error")
        return None
    finally:
        cursor.close()
        conn.close()

def generate_user_id_from_hash(user_id):
    """Генерира 6-символно ID от числовото user_id"""
    hash_object = hashlib.md5(str(user_id).encode())
    hex_hash = hash_object.hexdigest()
    valid_chars = string.ascii_uppercase + string.digits  
    user_id_str = ''.join([c.upper() for c in hex_hash if c.upper() in valid_chars])
    return user_id_str[:6]


# Функция за вмъкване на нотификация в базата данни
def insert_notification(matched_user_id, description, team_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO notifications (title, description, type, user_id, team_id) VALUES (%s, %s, %s, %s, %s)",
            ("Request to Join", description, 1, matched_user_id, team_id)
        )
        conn.commit()
        flash("Invitation sent successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error sending invitation: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()



def get_invite_details(notification_id, user_id):
    """Взема team_id от поканата, ако съществува."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Търсим team_id в таблицата invitations (или друга правилна таблица)
    cursor.execute("""
        SELECT team_id 
        FROM notifications 
        WHERE id = %s AND user_id = %s
    """, (notification_id, user_id))

    invite = cursor.fetchone()
    
    cursor.close()
    conn.close()

    return int(invite[0]) if invite else None


def is_player_in_team(user_id):
    """Проверява дали играчът вече е в отбор."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_id FROM user_team WHERE user_id = %s", (user_id,))
    current_team = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(current_team and current_team[0])


def add_player_to_team(user_id, team_id, notification_id):
    """Добавя играча към отбора и изтрива поканата."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Добавяне на играча в отбора с player_type = 1 (по подразбиране)
    cursor.execute("""
        INSERT INTO user_team (user_id, team_id, player_type)
        VALUES (%s, %s, 1)
    """, (user_id, team_id))
    cursor.execute("DELETE FROM notifications WHERE id = %s", (notification_id,))
    conn.commit()
    cursor.close()
    conn.close()


def delete_invite(notification_id):
    """Изтрива поканата от таблицата notifications"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM notifications WHERE id = %s AND type = 1", (notification_id,))
        conn.commit()
    except psycopg2.Error as e:
        print("Error deleting invite:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()




