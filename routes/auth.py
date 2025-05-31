from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import logout_user, login_required
from psycopg2 import sql
import re
import psycopg2

auth_bp = Blueprint('auth', __name__)

# Начална страница
@auth_bp.route('/')
def index():
    return render_template('main.html')


# Страница за регистрация
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Валидация за името
        if len(first_name) < 3 or not re.match("^[A-ZА-Я][a-zа-я]+$", first_name):
            flash('First name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return render_template("register.html")

        if len(first_name) > 16:
            flash('First name must be no more than 16 characters long.')
            return render_template("register.html")


        if len(last_name) < 3 or not re.match("^[A-ZА-Я][a-zа-я]+$", last_name):
            flash('Last name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return render_template("register.html")
        
        
        if len(first_name) > 16:
            flash('Last name must be no more than 16 characters long.')
            return render_template("register.html")


        # Валидация за имейл
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Please enter a valid email address.')
            return render_template("register.html")
        
        # Валидация на паролата
        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return render_template("register.html")

        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template("register.html")
        

        # Връзка с базата данни
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверка дали имейлът вече съществува в базата данни
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
        count = cur.fetchone()[0]

        if count > 0:
            flash('The email address is already registered.')
            return render_template("register.html")
 

        try:
            # Подготвяне на данните за вмъкване
            user_data = (
                first_name,                                                         #1
                last_name,                                                          #2      
                "",  # title                                                        #3   
                0,   # number                                                       #4
                email,                                                              #5
                generate_password_hash(password, method='pbkdf2:sha256'),           #6
                "",  # image                                                        #7
                0,   # type                                                         #8
                0,   # max_goals                                                    #9
                0,   # max_goals_in_one_match                                       #10
                0,   # max_assists                                                  #11
                0,   # max_assists_in_one_match                                     #12
                0,   # max_shoots                                                   #13
                0,   # max_shoots_in_one_match                                      #14
                0,   # max_shoots_on_target                                         #15
                0,   # max_shoots_on_target_in_one_match                            #16
                0,   # max_blocked_shoots                                           #17
                0,   # max_blocked_shoots_in_one_match                              #18
                0,   # max_saved_goals                                              #19
                0,   # max_saved_goals_in_one_match                                 #20
                0,   # max_passes                                                   #21
                0,   # max_passes_in_one_match                                      #22
                0,   # max_falls                                                    #23
                0,   # max_falls_in_one_match                                       #24
                0,   # max_hat_tricks                                               #25
                0,   # played_matches                                               #26
                0,   # win_matches                                                  #27
                0,   # draw_matches                                                 #28
                0,   # lose_matches                                                 #29
                0,   # max_ball_game_score                                          #30
                0    # max_keeper_game_score                                        #31
            )

            # Добавяне на потребител в базата данни
            cur.execute(
                sql.SQL("""
                    INSERT INTO users (
                        first_name, last_name, title, number, email, password, image, type,
                        max_goals, max_goals_in_one_match, max_assists, max_assists_in_one_match,
                        max_shoots, max_shoots_in_one_match, max_shoots_on_target, max_shoots_on_target_in_one_match,
                        max_blocked_shoots, max_blocked_shoots_in_one_match, max_saved_goals, max_saved_goals_in_one_match,
                        max_passes, max_passes_in_one_match, max_falls, max_falls_in_one_match, max_hat_tricks,
                        played_matches, win_matches, draw_matches, lose_matches,
                        max_ball_game_score, max_keeper_game_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """),
                user_data
            )

            conn.commit()
            cur.execute("SELECT id, first_name FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            if user:
                user_id, first_name = user
                # Добави потребителя в сесията
                session['user_id'] = user_id
                session['first_name'] = first_name
                flash('Registration successful! You are now logged in.', 'success')
                return redirect(url_for('home_bp.home')) 
        except psycopg2.IntegrityError:
            flash('The email already exists!', 'error')
        finally:
            cur.close()
            conn.close()

        return render_template("register.html")

    return render_template('register.html')



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Връзка с базата данни
        conn = get_db_connection()
        cur = conn.cursor()

        # Търсене на потребител с този имейл
        cur.execute("SELECT id, first_name, password FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            # Ако потребителят съществува, проверяваме паролата
            user_id, first_name, stored_password = user
            if check_password_hash(stored_password, password):
                # Паролата съвпада, записваме в сесията потребителския id   
                session['user_id'] = user_id
                session['first_name'] = first_name
                flash(f'Welcome, {first_name}!', 'success')
                return redirect(url_for('home_bp.home'))  # Пренасочваме към началната страница
            else:
                flash('Invalid password!', 'error')
        else:
            flash('The user with this email does not exist!', 'error')

        # Затваряме връзката
        cur.close()
        conn.close()

    return render_template('login.html')  # Връщаме страницата за логин


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():   
    session.clear()
    logout_user()  # Излизане от акаунта
    flash('You have been successfully logged out.', 'info')  # Можеш да добавиш флаш съобщение
    return redirect(url_for('auth.index'))  # Ако auth.index е защитена с @login_required, използвай входния маршрут


@auth_bp.route('/start')
def start():
    return redirect(url_for('auth.login'))

