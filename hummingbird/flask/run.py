from app import app
from flask_restful import Api, Resource

api = Api(app)

if __name__ == '__main__':
    app.run(debug=True)