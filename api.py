from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort
from flask_bcrypt import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re
from collections import OrderedDict
app = Flask(__name__) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app) 
api = Api(app)

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/user/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name:
        return jsonify({"message": "Name cannot be left blank", "data": {}}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"message": "Email is not valid", "data": {}}), 400
    if not password:
        return jsonify({"message": "Password cannot be left blank", "data": {}}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"message": "Email already registered", "data": {}}), 400

    new_user = User(name=name, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    return jsonify(OrderedDict([
        ("message", "User signup complete"),
        ("data", {
            "access_token": access_token,
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email
            }
        })
    ])), 200

@user_bp.route('/user/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"message": "Email is not valid", "data": {}}), 400
    if not password:
        return jsonify({"message": "Password cannot be left blank", "data": {}}), 400

    user = User.query.filter_by(email=email).first()

    if user is None:
        return jsonify(OrderedDict([
            ("message", "Email not registered"),
            ("data", {})
        ])), 404

    if not user.check_password(password):
        return jsonify(OrderedDict([
            ("message", "Invalid password"),
            ("data", {})
        ])), 401

    access_token = create_access_token(identity=user.id)
    return jsonify(OrderedDict([
        ("message", "Login successful"),
        ("data", {
            "access_token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        })
    ])), 200

@user_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_details():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user:
        return jsonify(OrderedDict([
            ("message", "User detail"),
            ("data", {
                "id": user.id,
                "name": user.name,
                "email": user.email
            })
        ])), 200
    return jsonify(OrderedDict([
        ("message", "User not found"),
        ("data", {})
    ])), 404


contact_bp = Blueprint('contact_bp', __name__)

@contact_bp.route('/contact', methods=['POST'])
@jwt_required()
def create_contact():
    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')

    if not name:
        return jsonify({"message": "Name is required", "data": {}}), 400
    if not phone:
        return jsonify({"message": "Phone is required", "data": {}}), 400

    new_contact = Contact(
        name=name,
        email=data.get('email'),
        phone=phone,
        address=data.get('address'),
        country=data.get('country'),
        user_id=user_id
    )
    db.session.add(new_contact)
    db.session.commit()

    return jsonify({"message": "Contact added", "data": {
        "id": new_contact.id,
        "name": new_contact.name,
        "email": new_contact.email,
        "phone": new_contact.phone,
        "country": new_contact.country,
        "address": new_contact.address
    }}), 200

@contact_bp.route('/contact', methods=['GET'])
@jwt_required()
def list_contacts():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 10, type=int)
    sort_by = request.args.get('sort_by', 'latest')
    name = request.args.get('name')
    email = request.args.get('email')
    phone = request.args.get('phone')

    query = Contact.query.filter_by(user_id=user_id)

    if name:
        query = query.filter(Contact.name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Contact.email.ilike(f"%{email}%"))
    if phone:
        query = query.filter(Contact.phone.ilike(f"%{phone}%"))

    if sort_by == 'latest':
        query = query.order_by(Contact.id.desc())
    elif sort_by == 'oldest':
        query = query.order_by(Contact.id.asc())
    elif sort_by == 'alphabetically_a_to_z':
        query = query.order_by(Contact.name.asc())
    elif sort_by == 'alphabetically_z_to_a':
        query = query.order_by(Contact.name.desc())

    contacts = query.paginate(page=page, per_page=per_page)

    return jsonify({
        "message": "Contact list",
        "data": {
            "list": [{"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "address": c.address, "country": c.country} for c in contacts.items],
            "has_next": contacts.has_next,
            "has_prev": contacts.has_prev,
            "page": contacts.page,
            "pages": contacts.pages,
            "per_page": contacts.per_page,
            "total": contacts.total
        }
    }), 200

class UserModel(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self): 
        return f"User(name = {self.name}, email = {self.email})"

user_args = reqparse.RequestParser()
user_args.add_argument('name', type=str, required=True, help="Name cannot be blank")
user_args.add_argument('email', type=str, required=True, help="Email cannot be blank")

userFields = {
    'id':fields.Integer,
    'name':fields.String,
    'email':fields.String,
}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True,  nullable=False)
    password = db.Column(db.String(60), nullable=False)
    contact = db.relationship('Contact',backref='owner', lazy=True)

    def set_password(self,password):
        self.password=bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self,password):
        return bcrypt.check_password_hash(self.password,password)
    

class Contact(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    email=db.Column(db.String(120))
    phone=db.Column(db.String(20),nullable=False)
    address=db.Column(db.String(200))
    country=db.Column(db.String(50))
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

class Users(Resource):
    @marshal_with(userFields)
    def get(self):
        users = UserModel.query.all() 
        return users 
    
    @marshal_with(userFields)
    def post(self):
        args = user_args.parse_args()
        user = UserModel(name=args["name"], email=args["email"])
        db.session.add(user) 
        db.session.commit()
        users = UserModel.query.all()
        return users, 201
    
class User(Resource):
    @marshal_with(userFields)
    def get(self, id):
        user = UserModel.query.filter_by(id=id).first() 
        if not user: 
            abort(404, message="User not found")
        return user 
    
    @marshal_with(userFields)
    def patch(self, id):
        args = user_args.parse_args()
        user = UserModel.query.filter_by(id=id).first() 
        if not user: 
            abort(404, message="User not found")
        user.name = args["name"]
        user.email = args["email"]
        db.session.commit()
        return user 
    
    @marshal_with(userFields)
    def delete(self, id):
        user = UserModel.query.filter_by(id=id).first() 
        if not user: 
            abort(404, message="User not found")
        db.session.delete(user)
        db.session.commit()
        users = UserModel.query.all()
        return users

    
api.add_resource(Users, '/api/users/')
api.add_resource(User, '/api/users/<int:id>')

@app.route('/')
def home():
    return '<h1>Hello</h1>'

if __name__ == '__main__':
    app.run(debug=True) 
