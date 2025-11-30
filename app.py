# backend/app.py
from flask import Flask, request, session
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from extensions import db, bcrypt, limiter
from models import Host, Event, Attendee
from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH"))

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
bcrypt.init_app(app)
limiter.init_app(app)
CORS(app)

# Swagger API
api = Api(
    app,
    version="1.0",
    title="Invitations API",
    description="API for creating and managing event invitations with RSVP functionality",
    doc="/api/docs",
)

# Namespaces
auth_ns = api.namespace("auth", description="Authentication", path="/api/auth")
events_ns = api.namespace("events", description="Events", path="/api/events")
attendees_ns = api.namespace("attendees", description="RSVPs", path="/api/attendees")

# Models
signup_model = api.model(
    "Signup",
    {
        "email": fields.String(required=True, example="host@example.com"),
        "password": fields.String(required=True, example="securepass123"),
        "name": fields.String(required=True, example="John Doe"),
        "whatsapp_number": fields.String(required=True, example="5521999999999"),
    },
)

login_model = api.model(
    "Login",
    {
        "email": fields.String(required=True, example="host@example.com"),
        "password": fields.String(required=True, example="securepass123"),
    },
)

rsvp_model = api.model(
    "RSVP",
    {
        "event_slug": fields.String(required=True, example="abc123"),
        "whatsapp_number": fields.String(required=True, example="5521988888888"),
        "name": fields.String(required=True, example="Maria Silva"),
        "num_adults": fields.Integer(required=True, example=2),
        "num_children": fields.Integer(example=1),
        "comments": fields.String(example="Vegetarian meal"),
    },
)


# AUTH ROUTES
@auth_ns.route("/signup")
class Signup(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        """Create new host account"""
        data = request.get_json()
        required = ["email", "password", "name", "whatsapp_number"]
        if not all(field in data for field in required):
            api.abort(400, "Missing required fields")

        try:
            email_info = validate_email(data["email"], check_deliverability=False)
            email = email_info.normalized
        except EmailNotValidError as e:
            api.abort(400, f"Invalid email: {str(e)}")

        if Host.query.filter_by(email=email).first():
            api.abort(409, "Email already registered")

        password_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        host = Host(
            email=email,
            password_hash=password_hash,
            name=data["name"],
            whatsapp_number=data["whatsapp_number"],
        )
        db.session.add(host)
        db.session.commit()
        session["host_id"] = host.id

        return {
            "message": "Account created",
            "host": {"id": host.id, "email": host.email, "name": host.name},
        }, 201


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login as host"""
        data = request.get_json()
        if not data.get("email") or not data.get("password"):
            api.abort(400, "Email and password required")

        host = Host.query.filter_by(email=data["email"]).first()
        if not host or not bcrypt.check_password_hash(
            host.password_hash, data["password"]
        ):
            api.abort(401, "Invalid credentials")

        session["host_id"] = host.id
        return {
            "message": "Login successful",
            "host": {"id": host.id, "email": host.email, "name": host.name},
        }, 200


# ATTENDEE ROUTES
@attendees_ns.route("/rsvp")
class RSVPResource(Resource):
    @attendees_ns.expect(rsvp_model)
    def post(self):
        """Create RSVP"""
        data = request.get_json()
        required = ["event_slug", "whatsapp_number", "name", "num_adults"]
        if not all(field in data for field in required):
            api.abort(400, "Missing required fields")

        event = Event.query.filter_by(slug=data["event_slug"]).first()
        if not event:
            api.abort(404, "Event not found")

        existing = Attendee.query.filter_by(
            event_id=event.id, whatsapp_number=data["whatsapp_number"]
        ).first()
        if existing:
            api.abort(400, "Already RSVP'd")

        attendee = Attendee(
            event_id=event.id,
            whatsapp_number=data["whatsapp_number"],
            name=data["name"],
            num_adults=data["num_adults"],
            num_children=data.get("num_children", 0),
            comments=data.get("comments", ""),
        )
        db.session.add(attendee)
        db.session.commit()

        from services.email_service import send_rsvp_notification

        send_rsvp_notification(event, attendee)

        return {"message": "RSVP successful", "attendee_id": attendee.id}, 201


# EVENT ROUTES
@events_ns.route("/<string:slug>")
class EventBySlug(Resource):
    def get(self, slug):
        """Get event by slug"""
        event = Event.query.filter_by(slug=slug).first()
        if not event:
            api.abort(404, "Event not found")

        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "description": event.description,
                "event_date": event.event_date.isoformat(),
                "start_time": event.start_time.strftime("%H:%M"),
                "address_full": event.address_full,
            }
        }, 200


# Keep original blueprints for other routes
from routes import auth, events, attendees

app.register_blueprint(auth.bp)
app.register_blueprint(events.bp)
app.register_blueprint(attendees.bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
