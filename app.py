from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import smtplib
from email.mime.text import MIMEText
from models import db, User
import os
from dotenv import load_dotenv

load_dotenv()
# Initialise Flask app
app = Flask(__name__)

# Application configuration
app.config["SECRET_KEY"] = "thisdoesntmeananything"  
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"  
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False 

db = SQLAlchemy(app)
# Gmail SMTP email sending function
def send_email(recipient_email, subject, body):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = os.environ.get("GMAIL_USER")
    smtp_password = os.environ.get("GMAIL_APP_PASSWORD")
    sender_email = smtp_username

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

from routes import app, db  

# Create database tables and setup default users
with app.app_context():
    db.create_all()

    # List of default users 
    # I've created a superuser
    # Plus 6 other users just for testing and for the video
    default_users = [
        {
            "username": "admin",
            "email": "admin1test@gmail.com",
            "is_superuser": True,
            "is_verified": True,
            "password": "123456#",
        },
        {
            "username": "artist1",
            "email": "artist1@gmail.com",
            "is_superuser": False,
            "is_verified": True,
            "password": "123456#",
        },
        {
            "username": "artist2",
            "email": "artist2@gmail.com",
            "is_superuser": False,
            "is_verified": True,
            "password": "123456#",
        },
        {
            "username": "artist3",
            "email": "artist3@gmail.com",
            "is_superuser": False,
            "is_verified": True,
            "password": "123456#",
        },
        {
            "username": "artist4",
            "email": "artist4@gmail.com",
            "is_superuser": False,
            "is_verified": True,
            "password": "123456#",
        },
        {
            "username": "artist5",
            "email": "artist5@gmail.com",
            "is_superuser": False,
            "is_verified": True,
            "password": "123456#",
        }
    ]


    # Check if users exist in the database; if not, create them
    for user_data in default_users:
        user = User.query.filter_by(email=user_data["email"]).first()
        if not user:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                is_superuser=user_data["is_superuser"],
                is_verified=user_data["is_verified"]
            )
            user.set_password(user_data["password"])  
            db.session.add(user)
            print(f"User created: {user_data['email']}")

    # Commit changes to the database
    db.session.commit()

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
