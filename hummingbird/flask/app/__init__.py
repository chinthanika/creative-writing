from flask import Flask
from flask_restful import Api
from firebase_admin import firestore, storage
from config import config

from config import config

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize Firebase using the config
    firestore_client, storage_bucket = config[config_name].init_firebase()

    # Initialize Flask-RESTful API
    api = Api(app)

    # Import and register blueprints/routes
    from .routes.routes_users import initializeUserRoutes
    from .routes.routes_entities import initializeEntityRoutes
    from .routes.routes_relations import initializeRelationRoutes
    from .routes.routes_content import initializeContentRoutes

    from .routes.routes_test import test_bp  # Import the test blueprint
    initializeUserRoutes(api, firestore_client)
    initializeEntityRoutes(api, firestore_client)
    initializeRelationRoutes(api, firestore_client)
    initializeContentRoutes(api, firestore_client, storage_bucket)

    app.register_blueprint(test_bp)  # Register the test blueprint

    return app