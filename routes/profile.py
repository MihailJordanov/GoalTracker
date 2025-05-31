from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from database.db import get_db_connection
import os
import hashlib
import random
import string

profile_bp = Blueprint('profile_bp', __name__)

def get_user_from_db(user_id):
    """Извлича информация за потребителя от базата данни."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, title, number, email, image, type, max_goals, max_assists, played_matches, win_matches 
        FROM users WHERE id = %s
    """, (user_id,))
    
    user = cur.fetchone()
    cur.close()
    conn.close()

    return user


def generate_user_id_from_hash(user_id):
    # Генерираме хеш от оригиналното ID
    hash_object = hashlib.md5(str(user_id).encode())
    hex_hash = hash_object.hexdigest()
    
    # Използваме само букви и цифри (главни букви)
    valid_chars = string.ascii_uppercase + string.digits  # Главни букви и цифри
    user_id_str = ''.join([c.upper() for c in hex_hash if c.upper() in valid_chars])  # Преобразуваме в главни букви
    
    # Съкращаваме до 6 символа
    return user_id_str[:6]


def format_user_data(user):
    """Форматира данните за потребителя в речник."""
    if not user:
        return None

    return {
        'id': generate_user_id_from_hash(user[0]),
        'first_name': user[1],
        'last_name': user[2],
        'title': user[3],
        'number': user[4],
        'email': user[5],
        'profile_picture': user[6] if user[6] else 'buttons/default_player_img_2.png',
        'type': user[7],
        'max_goals': user[8],
        'max_assists': user[9],
        'played_matches': user[10],
        'win_matches': user[11]
    }

@profile_bp.route('/profile')
def profile():
    """Показва страницата на профила."""
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))

    user_id = session['user_id']
    user = get_user_from_db(user_id)

    if not user:
        flash("Потребителят не е намерен.", "danger")
        return redirect(url_for('auth.index'))

    user_data = format_user_data(user)

    return render_template('profile.html', user=user_data)


UPLOAD_FOLDER = "static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# Папка, в която ще се съхраняват изображенията
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Функция за проверка на разширението на файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user_id():
    """Връща ID-то на текущия потребител от сесията, ако е логнат."""
    return session.get('user_id')


def update_user_picture(user_id, filename):
    """Обновява профилната снимка на потребителя в базата данни."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET image = %s
        WHERE id = %s
    """, (filename, user_id))
    conn.commit()
    cur.close()
    conn.close()


@profile_bp.route('/update-profile-picture', methods=['POST'])
def update_profile_picture():
    # Проверяваме дали потребителят е избрал файл
    if 'profile_picture' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        # Актуализираме потребителското изображение в базата данни
        user_id = get_current_user_id()  # Това трябва да е начинът да получиш текущия потребител
        update_user_picture(user_id, filename)
        
        flash('Profile picture updated successfully!', 'success')
        return redirect(url_for('profile_bp.profile'))  # Пренасочваме към страницата с профила

    else:
        flash('Invalid file type', 'error')
        return redirect(request.url)











