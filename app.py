import os
from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager, UserMixin
from routes.auth import auth_bp
from routes.home import home_bp
from routes.team_create_edit import team_bp
from routes.add_match import add_match_bp
from routes.profile import profile_bp
from routes.match_history import match_history_bp
from routes.notifications import notifications_bp
from routes.edit_match import edit_match_bp
from routes.enemy_team_list import enemy_team_bp
from routes.location_list import location_bp
from routes.manage_players import manage_players_bp
from database.db import get_db_connection  # Импортираме връзката към базатаfrom routes.home import home_bp

app = Flask(__name__)

load_dotenv()

app.secret_key = os.environ.get('SECRET_KEY')
    
# Flask-Login setup
login_manager = LoginManager()  
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Регистриране на Blueprint-ите
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(team_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(add_match_bp)
app.register_blueprint(match_history_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(edit_match_bp)
app.register_blueprint(enemy_team_bp)
app.register_blueprint(location_bp)
app.register_blueprint(manage_players_bp)

# Дефиниране на клас User
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Функция за зареждане на потребител по ID
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1])
    return None

# Стартиране на приложението
if __name__ == '__main__':
    app.run(debug=True)
