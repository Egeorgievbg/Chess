from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    games = db.relationship('Game', backref='player', lazy=True, foreign_keys='Game.player_id')
    board_theme = db.Column(db.String(30), default='classic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    opponent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    opponent = db.relationship('User', foreign_keys=[opponent_id])
    player_color = db.Column(db.String(5), default='white')  # white or black
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    fen = db.Column(db.Text)  # Chess position in FEN notation
    pgn = db.Column(db.Text)  # Chess moves (stored as space-separated UCI list)
    time_control = db.Column(db.String(50), default='rapid:15+10')
    white_moves = db.Column(db.Text, default='')
    black_moves = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='active')  # active, won, lost, draw
    white_time_spent = db.Column(db.Integer, default=0)
    black_time_spent = db.Column(db.Integer, default=0)
    white_time_left = db.Column(db.Integer)
    black_time_left = db.Column(db.Integer)
    game_duration_seconds = db.Column(db.Integer, default=0)
    white_score = db.Column(db.Integer, default=0)
    black_score = db.Column(db.Integer, default=0)
    redo_stack = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    order = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')

