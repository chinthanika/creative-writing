import os
from firebase_admin import credentials, initialize_app, firestore

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret-key'
    FIREBASE_CREDENTIALS = os.path.join(os.path.dirname(__file__), 'config\creative-writing-52ae6-firebase-adminsdk-yzcmy-425c5aea65.json')

    @staticmethod
    def init_firebase():
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
        initialize_app(cred)
        return firestore.client()

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    FIREBASE_CREDENTIALS = os.path.join(os.path.dirname(__file__), 'config\creative-writing-52ae6-firebase-adminsdk-yzcmy-425c5aea65.json')

    @staticmethod
    def init_firebase():
        cred = credentials.Certificate(TestingConfig.FIREBASE_CREDENTIALS)
        initialize_app(cred)
        return firestore.client()

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}