
def initialize_routes(api, db):
    from flask_restful import Resource

    class HelloWorld(Resource):
        def get(self):
            return {'hello': 'world'}

    api.add_resource(HelloWorld, '/')