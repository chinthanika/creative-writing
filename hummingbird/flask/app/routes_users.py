from flask import Blueprint, request, jsonify
from flask_restful import reqparse, Resource
from .components import data_parser

def initializeUserRoutes(api, db):
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
                
    class UpdateUser(Resource):
        def put(self, user_id):
            parser = reqparse.RequestParser()

            parser.add_argument('username', required = False, type = str)
            parser.add_argument('email', required = False, type = str)
            parser.add_argument('bio', required = False, type = str)
            parser.add_argument('is_public', required = False, type = data_parser.parse_bool)
            parser.add_argument('show_email', required = False, type = data_parser.parse_bool)
            parser.add_argument('selected_content', required = False, type = data_parser.parse_json)

            args = parser.parse_args()

            update_data = {}

            if 'username' in args:
                update_data['username'] = args['username']
            if 'email' in args:
                update_data['email'] = args['email']
            if 'bio' in args:
                update_data['bio'] = args['bio']
            if 'is_public' in args:
                update_data['is_public'] = args['is_public']
            if 'show_email' in args:
                update_data['show_email'] = args['show_email']
            if 'selected_content' in args:
                update_data['selected_content'] = args['selected_content']

            try:
                user_ref = db.collection('users').document(user_id)
                user_doc = user_ref.get()

                if not user_doc.exists:
                    return {'message': 'User not found'}, 404

                user_ref.update(update_data)

                return {'message': 'User data updated successfully'}, 200
            
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
            
    class DeleteUser(Resource):
        def delete(self, user_id):
            try:
                user_ref = db.collection('users').document(user_id)
                user_doc = user_ref.get()

                if not user_doc.exists:
                    return {'message': 'User not found'}, 404

                user_ref.delete()
                return {'message': 'User deleted successfully'}, 200
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateUser, '/create_user')
    api.add_resource(UpdateUser, '/update_user/<string:user_id>')
    api.add_resource(GetUserById, '/get_userid/<string:user_id>')
    api.add_resource(DeleteUser, '/delete_user/<string:user_id>')
    api.add_resource(GetUserByAttribute, '/get_user/')
