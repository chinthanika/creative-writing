from flask import Blueprint, request, jsonify
from firebase_admin import firestore

test_bp = Blueprint('test_bp', __name__)

@test_bp.route('/test', methods=['POST'])
def create_document():
    db = firestore.client()
    data = request.get_json()
    db.collection('test_collection').add(data)
    return jsonify({"message": "Document added successfully"}), 201

@test_bp.route('/test', methods=['GET'])
def get_documents():
    db = firestore.client()
    docs = db.collection('test_collection').stream()
    results = [doc.to_dict() for doc in docs]
    return jsonify(results), 200