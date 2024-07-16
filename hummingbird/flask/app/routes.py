from flask import Blueprint, request, jsonify
from flask_restful import reqparse
from firebase_admin import firestore

def initialize_routes(api, db):
    from flask_restful import Resource

    class HelloWorld(Resource):
        def get(self):
            return {'hello': 'world'}
        
    class CreateUser(Resource):
        def post(self):
            parser = reqparse.RequestParser()
            parser.add_argument('username', required = True, type = str, help = 'Username cannot be blank')
            parser.add_argument('email', required = True, type = str, help = 'Email address cannot be blank')
            args = parser.parse_args()

            username = args['username']
            email = args['email']

            try:
                user_ref = db.collection('users').add({
                    'username': username,
                    'email': email
                })
                return {'message': 'User data added successfully', 'id': user_ref[1].id}, 201
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            

    class GetUserById(Resource):
        def get(self, user_id):
            try:
                users_ref = db.collection('users').document(user_id)
                user_doc = users_ref.get()

                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data['id'] = user_id
                    return user_data, 200
                
                else:
                    return {'message': 'User not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    class GetUserByAttribute(Resource):
        def get(self):

            # Get query parameters
            args = request.args
            attribute = args.get('attribute')
            value = args.get('value')

            if not attribute or not value:
                return {'message': 'Attribute and value query parameters are required'}, 400

            try:
                users_ref = db.collection('users')
                query = users_ref.where(attribute, '==', value).stream()
                
                user_data = None
                for user in query:
                    user_data = user.to_dict()
                    user_data['id'] = user.id
                    break
                
                if user_data:
                    return user_data, 200
                else:
                    return {'message': 'User not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            

    api.add_resource(HelloWorld, '/')
    api.add_resource(CreateUser, '/create_user')
    api.add_resource(GetUserById, '/get_userid/<string:user_id>')
    api.add_resource(GetUserByAttribute, '/get_user/')
