from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name):
    # Initialize application.
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize Python packages
    db.init_app(app)
    migrate.init_app(app, db)

    # Attached CC modules
    from .gather import gather as gather_blueprint
    app.register_blueprint(gather_blueprint, url_prefix='/api/v1/gather')

    from .i18n import i18n as i18n_blueprint
    app.register_blueprint(i18n_blueprint, url_prefix='/api/v1/i18n')

    return app
