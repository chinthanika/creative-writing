from flask import Flask
from flask_restful import Api
from firebase_admin import credentials, initialize_app, firestore
from config import config

from config import config

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize Firebase using the config
    db = config[config_name].init_firebase()

    # Initialize Flask-RESTful API
    api = Api(app)

    # Import and register blueprints/routes
    from .routes_users import initializeUserRoutes
    from .routes_entities import initializeEntityRoutes
    from .routes_test import test_bp  # Import the test blueprint
    initializeUserRoutes(api, db)
    initializeEntityRoutes(api, db)
    app.register_blueprint(test_bp)  # Register the test blueprint

    return app