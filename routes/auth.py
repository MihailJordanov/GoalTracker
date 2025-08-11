from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database.db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import logout_user, login_required
from psycopg2 import sql
import re
import psycopg2
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import smtplib
from email.mime.text import MIMEText
from email.utils import parseaddr

auth_bp = Blueprint('auth', __name__)


def _get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset')

def generate_reset_token(user_id: int, password_hash: str) -> str:
    """Солим със хеша на паролата, за да паднат старите токени при смяна на паролата."""
    s = _get_serializer()
    # payload включва user_id и "ph" – текущия хеш, за да бъде част от подписа
    return s.dumps({'uid': user_id, 'ph': password_hash})

def verify_reset_token(token: str, expected_password_hash: str, max_age: int):
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=max_age)
    except SignatureExpired:
        return None  # изтекъл
    except BadSignature:
        return None  # невалиден

    if 'uid' not in data or 'ph' not in data:
        return None
    # Проверяваме дали хешът в токена съвпада с текущия – иначе токенът е остарял
    if data['ph'] != expected_password_hash:
        return None
    return data['uid']



def send_reset_email(to_email: str, reset_link: str):
    from flask import current_app
    subject = "Reset your Football Stats password"
    text = f"""Hello,

We received a request to reset your password.
This link is valid for 1 hour:

{reset_link}

If you didn't request this, you can ignore the email.
– GoalTracker
"""
    msg = MIMEText(text, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = current_app.config['MAIL_FROM']   # например "GoalTracker <goaltrackereu@gmail.com>"
    msg['To'] = to_email

    envelope_from = parseaddr(current_app.config['MAIL_FROM'])[1]  # чист имейл за SMTP
    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        if current_app.config.get('MAIL_USE_TLS', True):
            server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.sendmail(envelope_from, [to_email], msg.as_string())


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
        
        
        if len(last_name) > 16:
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



@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        # Една и съща реакция, за да не издаваме дали има такъв потребител
        generic_msg = 'If that email exists, we have sent a reset link.'
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash(generic_msg, 'info')
            return render_template('forgot_password.html')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE email = %s", (email,))
        row = cur.fetchone()

        if row:
            user_id, password_hash = row
            token = generate_reset_token(user_id, password_hash)
            # Генерираме абсолютен линк
            base = current_app.config['BASE_URL'].rstrip('/')
            reset_link = f"{base}{url_for('auth.reset_password', token=token)}"
            try:
                send_reset_email(email, reset_link)
            except Exception as e:
                # По желание логни грешката
                pass

        cur.close()
        conn.close()
        flash(generic_msg, 'info')
        return render_template('forgot_password.html')

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Първо валидираме токена срещу текущия password hash
    conn = get_db_connection()
    cur = conn.cursor()

    # 1) опитваме да извадим user_id от токена без да знаем hash -> няма как,
    # затова първо питаме потребителя да въведе имейл или ще минем през lookup по всички?
    # По-ефикасно: ще пазим user_id в токена и ще направим lookup по него.
    # Това вече сме го направили (uid е в токена), но трябва hash за проверката.
    # Тук ще го извлечем след малко:

    # Малък трик: десериализираме *без* max_age и *без* да сверяваме ph. Ще вземем uid,
    # после ще сверим ph чрез verify_reset_token, след като имаме текущия password hash.
    from itsdangerous import BadTimeSignature
    try:
        raw = _get_serializer().loads(token, max_age=None)
        uid_from_token = raw.get('uid')
    except Exception:
        uid_from_token = None

    if not uid_from_token:
        cur.close(); conn.close()
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))

    cur.execute("SELECT id, email, password FROM users WHERE id = %s", (uid_from_token,))
    user = cur.fetchone()
    if not user:
        cur.close(); conn.close()
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user_id, email, password_hash = user

    # Сега проверяваме токена с max_age и текущия hash
    uid_verified = verify_reset_token(
        token,
        expected_password_hash=password_hash,
        max_age=current_app.config['PASSWORD_RESET_TOKEN_MAX_AGE']
    )
    if not uid_verified:
        cur.close(); conn.close()
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_password.html', email=email)

        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', email=email)

        # Записваме новата парола
        new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user_id))
        conn.commit()
        cur.close(); conn.close()

        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    cur.close(); conn.close()
    return render_template('reset_password.html', email=email)


