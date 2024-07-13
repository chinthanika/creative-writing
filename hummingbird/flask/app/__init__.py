from flask import Flask
from flask_restful import Api

from config import config

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize Firebase using the config
    db = config[config_name].init_firebase()

    # Initialize Flask-RESTful API
    api = Api(app)

    # Import and register blueprints/routes
    from .routes import initialize_routes
    initialize_routes(api, db)

    return app