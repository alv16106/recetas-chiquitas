import os

from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor inicia sesión para acceder a esta página."

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth import bp as auth_bp
    from app.recipes import bp as recipes_bp
    from app.shopping import bp as shopping_bp
    from app.mealplans import bp as mealplans_bp
    from app.api import bp as api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(recipes_bp, url_prefix="/recipes")
    app.register_blueprint(shopping_bp, url_prefix="/shopping")
    app.register_blueprint(mealplans_bp, url_prefix="/mealplans")
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    @app.route("/health")
    def health():
        return "", 200

    @app.route("/")
    def index():
        return redirect(url_for("recipes.list"))

    return app
