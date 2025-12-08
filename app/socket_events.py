import random
from datetime import datetime

import chess
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from app import db, socketio
from app.models import User, Game, Friend, Notification
from app.routes.game import (
    apply_time_snapshot,
    build_state_payload,
    calculate_captured_data,
    parse_time_control,
    save_redo_stack,
)


def _friend_ids(user_id):
    return [friend.friend_id for friend in Friend.query.filter_by(user_id=user_id).all()]


def _broadcast_to_friends(user_id, event, payload):
    for friend_id in set(_friend_ids(user_id)):
        socketio.emit(event, payload, room=f"user_{friend_id}")


def _join_user_room(user_id):
    join_room(f"user_{user_id}")


def _emit_initial_friend_statuses(user):
    friend_ids = _friend_ids(user.id)
    if not friend_ids:
        return

    friends = User.query.filter(User.id.in_(friend_ids)).all()
    payload = []
    for friend in friends:
        last_seen = friend.last_seen or friend.created_at
        payload.append({
            'user_id': friend.id,
            'is_online': bool(friend.sid),
            'last_seen': last_seen.isoformat() if last_seen else ''
        })
    emit('friend_statuses', {'friends': payload}, to=request.sid)


@socketio.on('connect')
def on_connect():
    if not current_user.is_authenticated:
        return False

    current_user.sid = request.sid
    current_user.last_seen = datetime.utcnow()
    db.session.commit()
    _join_user_room(current_user.id)

    _emit_initial_friend_statuses(current_user)

    _broadcast_to_friends(
        current_user.id,
        'user_online',
        {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_online': True,
            'last_seen': current_user.last_seen.isoformat()
        }
    )
    emit('connected', {'user_id': current_user.id})


@socketio.on('disconnect')
def on_disconnect():
    user = User.query.filter_by(sid=request.sid).first()
    if not user:
        return

    leave_room(f"user_{user.id}")
    user.sid = None
    user.last_seen = datetime.utcnow()
    db.session.commit()

    _broadcast_to_friends(
        user.id,
        'user_offline',
        {
            'user_id': user.id,
            'username': user.username,
            'is_online': False,
            'last_seen': user.last_seen.isoformat()
        }
    )


@socketio.on('join_game')
def on_join_game(data):
    if not current_user.is_authenticated:
        emit('join_error', {'message': 'Authentication required.'}, to=request.sid)
        return

    game_id = data.get('game_id')
    if not game_id:
        emit('join_error', {'message': 'Missing game id.'}, to=request.sid)
        return

    game = Game.query.get(game_id)
    if not game or current_user.id not in {game.player_id, game.opponent_id}:
        emit('join_error', {'message': 'Unauthorized to join.'}, to=request.sid)
        return

    join_room(f"game_{game_id}")
    emit('joined_game', {'game_id': game_id}, to=request.sid)


@socketio.on('make_move')
def on_make_move(payload):
    if not current_user.is_authenticated:
        emit('move_error', {'message': 'Authentication required.'}, to=request.sid)
        return

    game_id = payload.get('game_id')
    move_uci = payload.get('move_uci')
    time_snapshot = payload.get('time_snapshot')

    game = Game.query.get(game_id)
    if not game or current_user.id not in {game.player_id, game.opponent_id}:
        emit('move_error', {'message': 'Unauthorized move.'}, to=request.sid)
        return

    if game.status != 'active':
        emit('move_error', {'message': 'Game is not active.'}, to=request.sid)
        return

    board = chess.Board(game.fen)
    if time_snapshot:
        apply_time_snapshot(game, time_snapshot)

    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError:
        emit('move_error', {'message': 'Invalid move format.'}, to=request.sid)
        return

    if move not in board.legal_moves:
        emit('move_error', {'message': 'Move is not legal.'}, to=request.sid)
        return

    side_before = board.turn
    board.push(move)

    white_moves = (game.white_moves or '').strip().split()
    black_moves = (game.black_moves or '').strip().split()
    if side_before == chess.WHITE:
        white_moves.append(move_uci)
    else:
        black_moves.append(move_uci)

    save_redo_stack(game, [])
    game.white_moves = ' '.join(white_moves)
    game.black_moves = ' '.join(black_moves)
    game.pgn = ((game.pgn or '').strip() + ' ' + move_uci).strip()
    game.fen = board.fen()
    game.is_multiplayer_online = True

    if board.is_checkmate():
        if board.turn == chess.WHITE:
            game.status = 'lost' if game.player_color == 'white' else 'won'
        else:
            game.status = 'won' if game.player_color == 'white' else 'lost'
    elif board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
        game.status = 'draw'
    else:
        game.status = 'active'

    db.session.commit()

    captured_pieces, white_score, black_score = calculate_captured_data(board)
    game.white_score = white_score
    game.black_score = black_score
    db.session.commit()

    state = build_state_payload(game, board, (captured_pieces, white_score, black_score))
    state.update({'last_move': move_uci, 'game_id': game.id})
    socketio.emit('move_made', state, room=f"game_{game.id}")


@socketio.on('send_challenge')
def on_send_challenge(data):
    if not current_user.is_authenticated:
        emit('notification_error', {'message': 'Authentication required.'}, to=request.sid)
        return

    target_id = data.get('recipient_id')
    if not target_id:
        emit('notification_error', {'message': 'No recipient provided.', 'recipient_id': target_id}, to=request.sid)
        return

    recipient = User.query.get(target_id)
    if not recipient:
        emit('notification_error', {'message': 'Recipient not found.', 'recipient_id': target_id}, to=request.sid)
        return

    if not Friend.query.filter_by(user_id=current_user.id, friend_id=recipient.id).first():
        emit('notification_error', {'message': 'You can only challenge friends.', 'recipient_id': target_id}, to=request.sid)
        return

    message = data.get('message') or f"{current_user.username} иска да играе онлайн."
    notification = Notification(
        user_id=recipient.id,
        type='challenge',
        message=message,
        data={'challenger_id': current_user.id}
    )
    db.session.add(notification)
    db.session.commit()

    payload = {
        'id': notification.id,
        'type': notification.type,
        'message': notification.message,
        'data': notification.data,
        'sender': {
            'id': current_user.id,
            'username': current_user.username
        }
    }
    socketio.emit('notification', payload, room=f"user_{recipient.id}")
    emit('challenge_sent', {'recipient_id': recipient.id}, to=request.sid)


@socketio.on('accept_challenge')
def on_accept_challenge(data):
    if not current_user.is_authenticated:
        emit('notification_error', {'message': 'Authentication required.'}, to=request.sid)
        return

    notification_id = data.get('notification_id')
    notification = Notification.query.get(notification_id)
    if not notification or notification.user_id != current_user.id:
        emit('notification_error', {'message': 'Invalid notification.'}, to=request.sid)
        return

    if notification.type != 'challenge':
        emit('notification_error', {'message': 'Notification is not a challenge.'}, to=request.sid)
        return

    challenger_id = (notification.data or {}).get('challenger_id')
    challenger = User.query.get(challenger_id)
    if not challenger:
        emit('notification_error', {'message': 'Challenger is no longer available.'}, to=request.sid)
        return

    player_color = random.choice(['white', 'black'])
    time_setup = parse_time_control('online:10+5')
    initial_seconds = time_setup['initial_seconds']
    game = Game(
        player_id=challenger.id,
        opponent_id=current_user.id,
        player_color=player_color,
        difficulty='online',
        fen=chess.STARTING_FEN,
        pgn='',
        time_control='online:10+5',
        white_moves='',
        black_moves='',
        white_time_spent=0,
        black_time_spent=0,
        white_score=0,
        black_score=0,
        white_time_left=initial_seconds,
        black_time_left=initial_seconds,
        game_duration_seconds=0,
        redo_stack='[]',
        is_multiplayer_online=True
    )
    db.session.add(game)
    notification.is_read = True
    db.session.commit()

    payload = {'game_id': game.id, 'redirect_url': f"/game/{game.id}"}
    socketio.emit('challenge_accepted', payload, room=f"user_{challenger.id}")
    socketio.emit('challenge_accepted', payload, room=f"user_{current_user.id}")
