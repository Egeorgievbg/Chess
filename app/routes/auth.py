from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from app.models import User

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        board_theme = request.form.get('board_theme', 'classic')
        
        # Validation
        if not username or len(username) < 3:
            flash('Потребителското име трябва да бъде поне 3 символа', 'error')
            return redirect(url_for('auth.register'))
        
        if not email or '@' not in email:
            flash('Невалиден email адрес', 'error')
            return redirect(url_for('auth.register'))
        
        if password != password_confirm:
            flash('Паролите не съвпадат', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Паролата трябва да бъде поне 6 символа', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Потребителското име вече съществува', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Този email вече е регистриран', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        user.board_theme = board_theme
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрацията е успешна! Влезте с вашите данни', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Добре дошли, {username}!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Невалидно потребителско име или парола', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вие се отписахте успешно', 'info')
    return redirect(url_for('main.index'))
