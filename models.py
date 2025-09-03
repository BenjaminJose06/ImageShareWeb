import random
import string
from datetime import datetime
from sqlalchemy import LargeBinary
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

# Initialize database instance
db = SQLAlchemy()

# User Model: Represents registered users
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)  # Identifies admin users
    is_verified = db.Column(db.Boolean, default=False)  # Email verification status

    # Returns the number of followers the user has
    def follower_count(self):
        return Follower.query.filter_by(followed_id=self.id).count()

    # Returns the number of users the current user follows
    def following_count(self):
        return Follower.query.filter_by(follower_id=self.id).count()

    # Hash and set the user's password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Check if a given password matches the stored hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Generate a secure token for password resets
    def get_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.email, salt="password-reset")

    # Verify the reset token and retrieve the associated user
    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = s.loads(token, salt="password-reset", max_age=expires_sec)
        except:
            return None
        return User.query.filter_by(email=email).first()


# Image Model: Represents uploaded images
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Image title
    image_data = db.Column(db.LargeBinary, nullable=False)  # Stores image as binary data
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of upload
    moderation_status = db.Column(db.String(20), default="unmoderated")  # Status: unmoderated, pending, approved
    category = db.Column(db.String(20), default="Nature")  # Image category: Nature, Art, Technology, Memes, Photography
    is_archived = db.Column(db.Boolean, default=False)  # Superuser archive status
    artist_archived = db.Column(db.Boolean, default=False)  # User archive status
    unique_number = db.Column(db.String(10), unique=True, nullable=True)  # Unique identifier for moderated image
    vote_count = db.Column(db.Integer, default=0)  # Stores total votes

    last_reset_date = db.Column(db.DateTime, nullable=True)  # Timestamp of last vote reset
    last_reset_reason = db.Column(db.String(255), nullable=True)  # Reason for vote reset

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key reference to the uploader
    user = db.relationship('User', backref=db.backref('images', lazy=True))  # Relationship with the User model

    votes = db.relationship('Vote', back_populates="image")  # One-to-many relationship with votes

    # Generate a unique 10-digit number for the image
    def generate_unique_number(self):
        return ''.join(random.choices(string.digits, k=10))


# Vote Model: Tracks user votes on images
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Voter's user ID
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)  # Image being voted on
    vote_type = db.Column(db.String(10), nullable=False)  # Vote type: 'upvote' or 'downvote'

    user = db.relationship('User', backref=db.backref('votes', lazy=True))  # Relationship with User model
    image = db.relationship('Image', back_populates="votes")  # Relationship with Image model


# Follower Model: Tracks user-to-user follow relationships
class Follower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User following another user
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User being followed

    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy=True))
    followed = db.relationship('User', foreign_keys=[followed_id], backref=db.backref('followers_list', lazy=True))


# Comment Model: Stores user comments on images
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)  # Comment text
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of comment
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who posted the comment
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)  # Associated image

    user = db.relationship('User', backref=db.backref('comments', lazy=True))  # Relationship with User model
    image = db.relationship('Image', backref=db.backref('comments', lazy=True))  # Relationship with Image model
