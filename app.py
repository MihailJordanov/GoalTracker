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
from routes.stats_all_players import stats_all_players_bp
from werkzeug.middleware.proxy_fix import ProxyFix 
from database.db import get_db_connection
from config import DevelopmentConfig, ProductionConfig

load_dotenv()

def create_app():
    app = Flask(__name__)
    # Избери конфигурация по среда
    if os.getenv("FLASK_ENV") == "production":
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # ✅ ВАЖНО: ProxyFix след като app е създаден
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1, x_proto=1, x_host=1, x_port=1
    )

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    class User(UserMixin):
        def __init__(self, id, username):
            self.id = id
            self.username = username

    @login_manager.user_loader
    def load_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        # ⚠️ Увери се, че колоната username съществува. Ако нямаш username, ползвай email или first_name.
        cursor.execute("SELECT id, COALESCE(username, email) FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if user_data:
            return User(user_data[0], user_data[1])
        return None

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
    app.register_blueprint(stats_all_players_bp)

    return app

app = create_app()

if __name__ == '__main__':
    # В dev среда BASE_URL по подразбиране е http://127.0.0.1:5000
    app.run(debug=app.config.get("DEBUG", False))
