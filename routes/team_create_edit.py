import os
import re
import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import psycopg2
from datetime import datetime, date 
from database.db import get_db_connection 
import cloudinary
import cloudinary.uploader

team_bp = Blueprint('team_bp', __name__)

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

UPLOAD_FOLDER = "static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


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


def check_if_team_name_exists(name):
    conn = get_db_connection()  # Създаваме връзка с базата
    cursor = conn.cursor()

    # Изпълняваме заявка, за да проверим дали има отбор с това име
    cursor.execute("SELECT COUNT(*) FROM teams WHERE name = %s", (name,))
    result = cursor.fetchone()[0]  # Връща броя на намерените отбори

    cursor.close()
    conn.close()

    return result > 0   


# Функция за проверка дали потребителят е логнат и има права да редактира отбора
def check_user_permissions(user_id, team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ut.player_type
        FROM user_team ut
        WHERE ut.user_id = %s AND ut.team_id = %s
    """, (user_id, team_id))

    user_team = cur.fetchone()
    cur.close()
    conn.close()

    if not user_team:
        return False, "You are not associated with this team."
    if user_team[0] < 2:
        return False, "You don't have permission to edit this team."
    return True, ""

# Функция за извличане на информация за отбора от базата данни
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

# Функция за валидиране на данните за отбора
def validate_team_data(name, team_id):
    # Проверка дали името е празно
    if not name:
        return False, "Team name cannot be empty!"
    
    # Проверка за минимална и максимална дължина на името
    if len(name) < 3:
        return False, 'Team name must be at least 3 characters long.'
    
    if len(name) > 12:
        return False, 'Team name must be no more than 12 characters long.'
    
    # Проверка за специални символи (разрешаваме само букви и интервали)
    if not re.match("^[A-Za-zА-Яа-я ]+$", name):
        return False, 'Team name must contain only letters and spaces.'
    
    # Проверка дали името вече съществува в базата (освен ако е същото като предишното)
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM teams WHERE name = %s AND id != %s", (name, team_id))
    existing_team = cur.fetchone()
    cur.close()
    conn.close()

    if existing_team:
        return False, 'A team with this name already exists. Please choose a different name.'
    
    return True, ""

# Функция за обработка на логото
def process_logo(logo, current_logo):
    if logo:
        logo_filename = logo.filename
        logo.save(os.path.join('static/uploads', logo_filename))
        return logo_filename
    else:
        return current_logo

# Функция за актуализиране на отбора в базата данни
def update_team(team_id, name, logo_filename, team_color, team_color_letters, team_image_bg):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE teams
        SET name = %s,
            logo = %s,
            team_color = %s,
            team_color_letters = %s,
            team_image_bg = %s
        WHERE id = %s
    """, (name, logo_filename, team_color, team_color_letters, team_image_bg, team_id))

    conn.commit()
    cur.close()
    conn.close()

# Функция за проверка дали потребителят има вече отбор
def check_if_user_has_team(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM user_team WHERE user_id = %s
    """, (user_id,))
    team = cur.fetchone()
    cur.close()
    conn.close()
    return team is not None

# Функция за проверка дали отбор с дадено име вече съществува
def check_if_team_name_exists(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM teams WHERE name = %s
    """, (name,))
    existing_team = cur.fetchone()
    cur.close()
    conn.close()
    return existing_team is not None

# Функция за валидация на данните за името
def validate_team_name(name):
    if len(name) < 3:
        return False, 'Team name must be at least 3 characters long.'
    if len(name) > 12:
        return False, 'Team name must be no more than 12 characters long.'
    if not re.match("^[A-Za-zА-Яа-я ]+$", name):
        return False, 'Team name must contain only letters and spaces.'
    return True, ""

# Функция за валидация на географските данни
def validate_location_data(country, city):
    # Проверка за страната
    if len(country) < 3:
        return False, 'Country name must be at least 3 characters long.'
    if len(country) > 21:
        return False, 'Country name must be no more than 21 characters long.'
    if not re.match("^[A-Za-zА-Яа-я ]+$", country):
        return False, 'Country name must contain only letters and spaces.'

    # Проверка за града
    if len(city) < 3:
        return False, 'City name must be at least 3 characters long.'
    if len(city) > 21:
        return False, 'City name must be no more than 21 characters long.'
    if not re.match("^[A-Za-zА-Яа-я ]+$", city):
        return False, 'City name must contain only letters and spaces.'

    return True, ""


# Функция за създаване на нов отбор в базата данни
def create_team_in_db(name, country, city, year, logo_filename, team_color):
    conn = get_db_connection()
    cur = conn.cursor()

    current_date = date.today()

    try:
        # Преобразуваме year в int
        year = int(year)

        cur.execute("""
            INSERT INTO teams (name, country, city, year, logo, max_games, max_wins, max_losses, max_draws, create_date, team_color)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, country, city, year, logo_filename, 0, 0, 0, 0, current_date, team_color))

        new_team_id = cur.fetchone()[0]  # Вземаме id на новия отбор

        # Генериране на уникален team_code
        team_code = get_unique_team_code(cur)
        cur.execute("UPDATE teams SET team_code = %s WHERE id = %s", (team_code, new_team_id))

        # Вмъкване в таблица user_team
        cur.execute("""
            INSERT INTO user_team (user_id, team_id, player_type)
            VALUES (%s, %s, %s)
        """, (session['user_id'], new_team_id, 3))

        conn.commit()
        cur.close()
        conn.close()

        return new_team_id

    except psycopg2.IntegrityError:
        cur.close()
        conn.close()
        return None
    
    
def generate_random_team_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def get_unique_team_code(cur):
    while True:
        code = generate_random_team_code()
        cur.execute("SELECT 1 FROM teams WHERE team_code = %s", (code,))
        if not cur.fetchone():
            return code


def update_enemy_teams_by_team_code(team_code, name, image):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE enemy_teams
        SET name = %s, image = %s
        WHERE team_code = %s
    """, (name, image, team_code))
    conn.commit()
    cur.close()
    conn.close()



@team_bp.route('/edit/<int:team_id>', methods=['GET', 'POST'])
def edit(team_id):
    if 'user_id' not in session:
        flash('Please log in to edit a team.', 'error')
        return redirect(url_for('auth.index'))

    user_id = session['user_id']

    has_permission, message = check_user_permissions(user_id, team_id)
    if not has_permission:
        flash(message, 'error')
        return redirect(url_for('home_bp.home'))

    team = get_team_by_id(team_id)
    if not team:
        flash("Team not found!", 'error')
        return redirect(url_for('home_bp.home'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        team_color = request.form['team_color']
        team_color_letters = request.form['team_color_letters']
        logo = request.files.get('logo')
        team_image_bg = request.files.get('team_image_bg')
        enable_bg_image = request.form.get('enable_bg_image')  # None ако не е отметнато

        # Валидация
        is_valid, error_message = validate_team_data(name, team_id)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('team_bp.edit', team_id=team_id))

        # Обработка на логото
        logo_filename = team[2]
        if logo and logo.filename:
            try:
                result = cloudinary.uploader.upload(logo)
                logo_filename = result['secure_url']
            except Exception as e:
                flash(f'Error uploading logo: {e}', 'error')
                return redirect(url_for('team_bp.edit', team_id=team_id))


        # Обработка на background image само ако е включен
        bg_filename = team[5]
        if enable_bg_image and team_image_bg and team_image_bg.filename:
            try:
                result = cloudinary.uploader.upload(team_image_bg)
                bg_filename = result['secure_url']
            except Exception as e:
                flash(f'Error uploading background image: {e}', 'error')
                return redirect(url_for('team_bp.edit', team_id=team_id))
        elif not enable_bg_image:
            bg_filename = None  # Премахваме фоновото изображение


        # Актуализация
        update_team(team_id, name, logo_filename, team_color, team_color_letters, bg_filename)

        team_code = team[6] 
        update_enemy_teams_by_team_code(team_code, name, logo_filename)

        flash('Team updated successfully!', 'success')
        return redirect(url_for('home_bp.home'))

    return render_template('edit_team.html', team=team)

# Основна логика за създаване на отбор
@team_bp.route('/create', methods=['GET', 'POST'])
def create():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))  
    
    user_id = session['user_id']
    existing_team = check_if_user_has_team(user_id)
    if existing_team:
        flash('You already have a team. You cannot create another one.', 'info')
        return redirect(url_for('home_bp.home')) 
    
    if request.method == 'POST':
        name = request.form['name']
        country = request.form['country']
        city = request.form['city']
        year = request.form['year']
        logo = request.files['logo']
        team_color = request.form.get('team_color', '#00FFB7')

        # Валидация на името на отбора
        is_valid, message = validate_team_name(name)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('team_bp.create'))

        # Валидация на географските данни
        is_valid, message = validate_location_data(country, city)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('team_bp.create'))

        # Проверка дали името на отбора вече съществува
        if check_if_team_name_exists(name):
            flash('A team with this name already exists. Please choose a different name.', 'error')
            return redirect(url_for('team_bp.create'))

        # Запазване на логото
        logo_filename = None
        logo_filename = None
        if logo and logo.filename:
            try:
                result = cloudinary.uploader.upload(logo)
                logo_filename = result['secure_url']  # Записваме директен линк към Cloudinary
            except Exception as e:
                flash(f'Error uploading logo: {e}', 'error')
                return redirect(url_for('team_bp.create'))


        new_team_id = create_team_in_db(name, country, city, year, logo_filename, team_color)

        if new_team_id:
            flash('Team successfully created!', 'success')
            return redirect(url_for('home_bp.home'))
        else:
            flash('Error creating team. Please try again.', 'error')
            return redirect(url_for('team_bp.create'))

    return render_template('create_team.html')





