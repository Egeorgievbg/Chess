from datetime import datetime
from math import ceil

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user, login_required

from app import db
from app.models import User, Friend, Game, FriendRequest

main_bp = Blueprint('main', __name__)


def ensure_friendship(user_a_id, user_b_id):
    if not Friend.query.filter_by(user_id=user_a_id, friend_id=user_b_id).first():
        db.session.add(Friend(user_id=user_a_id, friend_id=user_b_id))


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/lessons')
def lessons():
    return render_template('lessons.html')


def format_time_control(value: str) -> str:
    if not value or value == 'unlimited':
        return 'Без ограничение'
    if ':' not in value or '+' not in value:
        return value
    mode, payload = value.split(':', 1)
    minutes, increment = payload.split('+', 1)
    labels = {
        'bullet': 'Куршум',
        'blitz': 'Блиц',
        'rapid': 'Рапид',
        'classical': 'Класически'
    }
    label = labels.get(mode, mode.capitalize())
    return f"{label} ({minutes} мин + {increment} сек)"


def format_duration(seconds: int) -> str:
    if seconds is None or seconds < 0:
        return '--:--'
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def format_color(color: str) -> str:
    return 'Бели' if color == 'white' else 'Черни'
    return 'Р‘РµР»Рё' if color == 'white' else 'Р§РµСЂРЅРё'



@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    filter_options = [
        {'value': 'all', 'label': 'Всички'},
        {'value': 'won', 'label': 'Победи'},
        {'value': 'lost', 'label': 'Загуби'},
        {'value': 'draw', 'label': 'Реми'},
        {'value': 'finished', 'label': 'Запазени'},
        {'value': 'active', 'label': 'В ход'}
    ]
    allowed_filters = {opt['value'] for opt in filter_options}
    result_filter = request.args.get('result', 'all')
    if result_filter not in allowed_filters:
        result_filter = 'all'
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)

    redirect_kwargs = {}
    if result_filter != 'all':
        redirect_kwargs['result'] = result_filter
    if page > 1:
        redirect_kwargs['page'] = page

    if request.method == 'POST':
        action = (request.form.get('action') or '').strip()

        if action == 'send_request':
            friend_name = (request.form.get('friend_username') or '').strip()
            if not friend_name:
                flash('Моля, въведи потребителско име.', 'error')
                return redirect(url_for('main.profile', **redirect_kwargs))
            friend = User.query.filter_by(username=friend_name).first()
            if not friend:
                flash('Такъв потребител не съществува.', 'error')
                return redirect(url_for('main.profile', **redirect_kwargs))
            if friend.id == current_user.id:
                flash('Не можеш да изпратиш покана до себе си.', 'error')
                return redirect(url_for('main.profile', **redirect_kwargs))

            already_friend = Friend.query.filter_by(user_id=current_user.id, friend_id=friend.id).first()
            if already_friend:
                flash('Вече сте приятели.', 'info')
                return redirect(url_for('main.profile', **redirect_kwargs))

            incoming_pending = FriendRequest.query.filter_by(
                sender_id=friend.id,
                receiver_id=current_user.id,
                status='pending'
            ).first()
            if incoming_pending:
                incoming_pending.status = 'accepted'
                incoming_pending.responded_at = datetime.utcnow()
                ensure_friendship(current_user.id, friend.id)
                ensure_friendship(friend.id, current_user.id)
                db.session.commit()
                flash('Поканата от този приятел беше приета.', 'success')
                return redirect(url_for('main.profile', **redirect_kwargs))

            existing_pending = FriendRequest.query.filter(
                FriendRequest.sender_id == current_user.id,
                FriendRequest.receiver_id == friend.id,
                FriendRequest.status == 'pending'
            ).first()
            if existing_pending:
                flash('Поканата вече е изпратена.', 'info')
                return redirect(url_for('main.profile', **redirect_kwargs))

            new_request = FriendRequest(sender_id=current_user.id, receiver_id=friend.id)
            db.session.add(new_request)
            db.session.commit()
            flash('Поканата е изпратена успешно.', 'success')
            return redirect(url_for('main.profile', **redirect_kwargs))

        if action in {'accept_request', 'decline_request', 'cancel_request', 'dismiss_request'}:
            try:
                request_id = int(request.form.get('request_id', 0))
            except (TypeError, ValueError):
                flash('Невалидна заявка.', 'error')
                return redirect(url_for('main.profile', **redirect_kwargs))

            friend_request = FriendRequest.query.get(request_id)
            if not friend_request:
                flash('Поканата не беше намерена.', 'error')
                return redirect(url_for('main.profile', **redirect_kwargs))

            if action == 'accept_request':
                if friend_request.receiver_id != current_user.id or friend_request.status != 'pending':
                    flash('Не можеш да приемеш тази покана.', 'error')
                    return redirect(url_for('main.profile', **redirect_kwargs))
                friend_request.status = 'accepted'
                friend_request.responded_at = datetime.utcnow()
                ensure_friendship(current_user.id, friend_request.sender_id)
                ensure_friendship(friend_request.sender_id, current_user.id)
                db.session.commit()
                flash('Поканата е приета.', 'success')
                return redirect(url_for('main.profile', **redirect_kwargs))

            if action == 'decline_request':
                if friend_request.receiver_id != current_user.id or friend_request.status != 'pending':
                    flash('Не можеш да откажеш тази покана.', 'error')
                    return redirect(url_for('main.profile', **redirect_kwargs))
                friend_request.status = 'declined'
                friend_request.responded_at = datetime.utcnow()
                db.session.commit()
                flash('Поканата е отказана.', 'info')
                return redirect(url_for('main.profile', **redirect_kwargs))

            if action == 'cancel_request':
                if friend_request.sender_id != current_user.id or friend_request.status == 'accepted':
                    flash('Не можеш да отмениш тази покана.', 'error')
                    return redirect(url_for('main.profile', **redirect_kwargs))
                db.session.delete(friend_request)
                db.session.commit()
                flash('Поканата е отменена.', 'success')
                return redirect(url_for('main.profile', **redirect_kwargs))

            if action == 'dismiss_request':
                if friend_request.sender_id != current_user.id or friend_request.status != 'declined':
                    flash('Няма отказана покана за изчистване.', 'error')
                    return redirect(url_for('main.profile', **redirect_kwargs))
                db.session.delete(friend_request)
                db.session.commit()
                flash('Историята е изчистена.', 'success')
                return redirect(url_for('main.profile', **redirect_kwargs))

        if action == 'update_theme':
            theme = request.form.get('board_theme')
            if theme:
                current_user.board_theme = theme
                db.session.commit()
                flash('Темата на дъската е обновена.', 'success')
            return redirect(url_for('main.profile', **redirect_kwargs))

        if action == 'update_email':
            new_email = (request.form.get('new_email') or '').strip()
            if not new_email:
                flash('Моля, въведи нов имейл.', 'error')
            elif new_email == current_user.email:
                flash('Този имейл вече е зададен.', 'info')
            elif User.query.filter_by(email=new_email).first():
                flash('Имейл адресът вече се използва.', 'error')
            else:
                current_user.email = new_email
                db.session.commit()
                flash('Имейл адресът е обновен.', 'success')
            return redirect(url_for('main.profile', **redirect_kwargs))

        if action == 'update_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            if not current_user.check_password(old_password or ''):
                flash('Настоящата парола е грешна.', 'error')
            elif not new_password or not confirm_password:
                flash('Попълни и двете полета за нова парола.', 'error')
            elif new_password != confirm_password:
                flash('Новата парола и потвърждението не съвпадат.', 'error')
            elif len(new_password) < 6:
                flash('Паролата трябва да е поне 6 символа.', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Паролата е сменена успешно.', 'success')
            return redirect(url_for('main.profile', **redirect_kwargs))

    friend_links = Friend.query.filter_by(user_id=current_user.id).order_by(Friend.created_at.desc()).all()
    friend_ids = [link.friend_id for link in friend_links]
    friends_data = []
    if friend_ids:
        friend_map = {f.friend_id: f for f in friend_links}
        users = User.query.filter(User.id.in_(friend_ids)).order_by(User.username.asc()).all()
        for user in users:
            friends_data.append({
                'username': user.username,
                'since': friend_map[user.id].created_at
            })

    games_as_player = Game.query.filter_by(player_id=current_user.id).all()
    games_as_opponent = Game.query.filter_by(opponent_id=current_user.id).all()
    all_games = sorted(games_as_player + games_as_opponent, key=lambda game: game.created_at or datetime.utcnow(), reverse=True)

    wins = losses = draws = 0
    total_duration = 0
    games_list = []

    for game in all_games:
        user_is_player = game.player_id == current_user.id
        user_color = game.player_color if user_is_player else ('black' if game.player_color == 'white' else 'white')

        if game.status == 'draw':
            result_label = 'Реми'
            result_key = 'draw'
            draws += 1
        elif game.status == 'won':
            if user_is_player:
                wins += 1
                result_label = 'Победа'
                result_key = 'won'
            else:
                losses += 1
                result_label = 'Загуба'
                result_key = 'lost'
        elif game.status == 'lost':
            if user_is_player:
                losses += 1
                result_label = 'Загуба'
                result_key = 'lost'
            else:
                wins += 1
                result_label = 'Победа'
                result_key = 'won'
        elif game.status == 'finished':
            result_label = 'Запазена'
            result_key = 'finished'
        else:
            result_label = 'В ход'
            result_key = 'active'

        duration = game.game_duration_seconds or 0
        total_duration += duration
        duration_label = 'В ход' if result_key == 'active' else format_duration(duration)
        score_display = f"{game.white_score or 0}:{game.black_score or 0}"
        can_resume = (game.status == 'finished' and game.player_id == current_user.id and game.opponent_id is None)

        games_list.append({
            'id': game.id,
            'created_at': game.created_at or datetime.utcnow(),
            'result': result_label,
            'result_key': result_key,
            'row_class': f"history-row-{result_key}",
            'time_control_display': format_time_control(game.time_control),
            'player_color_display': format_color(user_color),
            'duration_display': duration_label,
            'score_display': score_display,
            'view_url': url_for('game.view_game', game_id=game.id),
            'can_resume': can_resume,
            'resume_url': url_for('game.view_game', game_id=game.id)
        })

    if result_filter != 'all':
        filtered_games = [g for g in games_list if g['result_key'] == result_filter]
    else:
        filtered_games = games_list

    per_page = 10
    total_games = len(filtered_games)
    total_pages = max(1, ceil(total_games / per_page))
    page = min(page, total_pages)
    start_index = (page - 1) * per_page
    paginated_games = filtered_games[start_index:start_index + per_page]

    stats = {
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'total_time': format_duration(total_duration)
    }

    incoming_requests_data = []
    incoming_requests = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).order_by(FriendRequest.created_at.desc()).all()
    for req in incoming_requests:
        incoming_requests_data.append({
            'id': req.id,
            'username': req.sender.username if req.sender else 'Потребител',
            'created_at': req.created_at
        })

    outgoing_requests_data = []
    outgoing_requests = FriendRequest.query.filter_by(
        sender_id=current_user.id
    ).order_by(FriendRequest.created_at.desc()).all()
    for req in outgoing_requests:
        outgoing_requests_data.append({
            'id': req.id,
            'username': req.receiver.username if req.receiver else 'Потребител',
            'status': req.status,
            'created_at': req.created_at,
            'responded_at': req.responded_at
        })

    pagination = {
        'page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else 1,
        'next_page': page + 1 if page < total_pages else total_pages,
        'result_filter': result_filter,
        'total_games': total_games
    }

    return render_template(
        'profile.html',
        friends=friends_data,
        games=paginated_games,
        stats=stats,
        incoming_requests=incoming_requests_data,
        outgoing_requests=outgoing_requests_data,
        result_filter=result_filter,
        pagination=pagination,
        filter_options=filter_options
    )
