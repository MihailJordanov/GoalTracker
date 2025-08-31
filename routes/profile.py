from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from database.db import get_db_connection
import os
import hashlib
import random
import string
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


profile_bp = Blueprint('profile_bp', __name__)

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)


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


DEFAULT_AVATAR_PUBLIC_ID = "app/default_player_img"  # от upload-a
DEFAULT_AVATAR_FORMAT = "png"                        # ако ти трябва фиксирано разширение

def get_default_avatar_url():
    url, _ = cloudinary_url(
        DEFAULT_AVATAR_PUBLIC_ID,
        format=DEFAULT_AVATAR_FORMAT,
        secure=True
    )
    return url

def format_user_data(user):
    """Форматира данните за потребителя в речник."""
    if not user:
        return None

    image_path = user[6]

    if not image_path:
        profile_picture = get_default_avatar_url()   # Cloudinary default
    elif image_path.startswith("http"):
        profile_picture = image_path                 # Cloudinary (пълен URL)
    else:
        profile_picture = url_for('static', filename=f'uploads/{image_path}')  # Локално

    return {
        'id': generate_user_id_from_hash(user[0]),
        'first_name': user[1],
        'last_name': user[2],
        'title': user[3],
        'number': user[4],
        'email': user[5],
        'profile_picture': profile_picture,
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
    if 'profile_picture' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)

    file = request.files['profile_picture']

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        try:
            # 👉 Качваме в Cloudinary директно от `file`
            result = cloudinary.uploader.upload(file)
            cloud_url = result['secure_url']

            # 🔄 Обновяваме Cloudinary URL в базата
            user_id = get_current_user_id()
            update_user_picture(user_id, cloud_url)

            flash('Profile picture updated successfully!', 'success')
        except Exception as e:
            flash(f'Cloudinary upload failed: {e}', 'error')

        return redirect(url_for('profile_bp.profile'))

    flash('Invalid file type', 'error')
    return redirect(request.url)










