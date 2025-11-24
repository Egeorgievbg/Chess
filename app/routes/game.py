from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Game
import chess
import random
import time
import math
import json

game_bp = Blueprint('game', __name__)

# Simple AI logic for chess moves
class SimpleChessAI:
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 20000,
    }
    CENTER_SQUARES = {
        chess.D4, chess.E4, chess.D5, chess.E5
    }
    EXTENDED_CENTER = CENTER_SQUARES.union({
        chess.C3, chess.C4, chess.C5, chess.C6,
        chess.D3, chess.E3, chess.D6, chess.E6,
        chess.F3, chess.F4, chess.F5, chess.F6
    })
    DEVELOPMENT_SQUARES = {
        chess.WHITE: {chess.B1, chess.G1, chess.C1, chess.F1},
        chess.BLACK: {chess.B8, chess.G8, chess.C8, chess.F8},
    }

    def __init__(self, board, difficulty='medium'):
        self.board = board
        self.difficulty = difficulty
        self.ai_color = board.turn
    
    def get_best_move(self):
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            return None
        
        if self.difficulty == 'easy':
            return random.choice(legal_moves)
        if self.difficulty == 'medium':
            return self.choose_with_heuristics(legal_moves)
        return self.minimax_root(legal_moves, depth=3)
    
    def choose_with_heuristics(self, legal_moves):
        best_score = -math.inf
        best_moves = []
        for move in legal_moves:
            score = self.score_move(move)
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif math.isclose(score, best_score, rel_tol=1e-9, abs_tol=1e-9):
                best_moves.append(move)
        return random.choice(best_moves) if best_moves else random.choice(legal_moves)
    
    def minimax_root(self, legal_moves, depth=3):
        best_score = -math.inf
        best_moves = []
        alpha = -math.inf
        beta = math.inf
        ordered_moves = sorted(legal_moves, key=self.move_order_score, reverse=True)
        for move in ordered_moves:
            self.board.push(move)
            score = -self.negamax(depth - 1, -beta, -alpha, -1)
            self.board.pop()
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif math.isclose(score, best_score, rel_tol=1e-9, abs_tol=1e-9):
                best_moves.append(move)
            alpha = max(alpha, score)
        return random.choice(best_moves) if best_moves else random.choice(legal_moves)
    
    def negamax(self, depth, alpha, beta, color):
        if depth == 0 or self.board.is_game_over():
            return color * self.evaluate_board()
        
        best_value = -math.inf
        ordered_moves = sorted(list(self.board.legal_moves), key=self.move_order_score, reverse=True)
        for move in ordered_moves:
            self.board.push(move)
            value = -self.negamax(depth - 1, -beta, -alpha, -color)
            self.board.pop()
            if value > best_value:
                best_value = value
            if best_value > alpha:
                alpha = best_value
            if alpha >= beta:
                break
        return best_value
    
    def move_order_score(self, move):
        capture_bonus = 0
        captured = self.board.piece_at(move.to_square)
        if captured:
            capture_bonus = self.PIECE_VALUES.get(captured.piece_type, 0)
        center_bonus = 40 if move.to_square in self.CENTER_SQUARES else 15 if move.to_square in self.EXTENDED_CENTER else 0
        check_bonus = 30 if self.board.gives_check(move) else 0
        return capture_bonus + center_bonus + check_bonus
    
    def score_move(self, move):
        score = 0
        mover = self.board.piece_at(move.from_square)
        captured = self.board.piece_at(move.to_square)
        
        if captured:
            score += self.PIECE_VALUES.get(captured.piece_type, 0)
            if mover:
                score -= self.PIECE_VALUES.get(mover.piece_type, 0) * 0.2
        if mover and mover.piece_type in (chess.KNIGHT, chess.BISHOP):
            if move.from_square in self.DEVELOPMENT_SQUARES.get(mover.color, set()):
                score += 30
        if mover and mover.piece_type == chess.PAWN:
            rank = chess.square_rank(move.to_square)
            score += (rank if mover.color == chess.WHITE else (7 - rank)) * 4
        if move.to_square in self.CENTER_SQUARES:
            score += 35
        elif move.to_square in self.EXTENDED_CENTER:
            score += 15
        if self.board.gives_check(move):
            score += 40
        if mover and mover.piece_type == chess.PAWN and chess.square_rank(move.to_square) in (0, 7):
            score += 80
        
        self.board.push(move)
        score += self.evaluate_board() * 0.1
        self.board.pop()
        
        score += random.uniform(0, 0.01)  # small noise to avoid deterministic ties
        return score
    
    def evaluate_board(self):
        return self.evaluate_material() + self.evaluate_center_control() + self.evaluate_king_safety()
    
    def evaluate_material(self):
        score = 0
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if not piece:
                continue
            value = self.PIECE_VALUES.get(piece.piece_type, 0)
            score += value if piece.color == self.ai_color else -value
        return score
    
    def evaluate_center_control(self):
        score = 0
        for square in self.CENTER_SQUARES:
            piece = self.board.piece_at(square)
            if not piece:
                continue
            if piece.color == self.ai_color:
                score += 20
            else:
                score -= 20
        for square in self.EXTENDED_CENTER:
            piece = self.board.piece_at(square)
            if not piece:
                continue
            if piece.color == self.ai_color:
                score += 10
            else:
                score -= 10
        return score
    
    def evaluate_king_safety(self):
        score = 0
        ai_king = self.board.king(self.ai_color)
        opp_king = self.board.king(not self.ai_color)
        if ai_king is not None:
            file_ai = chess.square_file(ai_king)
            if file_ai in (1, 2, 5, 6):
                score += 15
            if self.board.has_castling_rights(self.ai_color):
                score += 10
        if opp_king is not None:
            file_opp = chess.square_file(opp_king)
            if file_opp in (1, 2, 5, 6):
                score -= 10
            if self.board.has_castling_rights(not self.ai_color):
                score -= 8
        return score


def parse_time_control(value):
    if not value or value == 'unlimited':
        return {'mode': 'unlimited', 'initial_seconds': None, 'increment': 0}
    try:
        mode, payload = value.split(':', 1)
        minutes, increment = payload.split('+')
        return {
            'mode': mode,
            'initial_seconds': int(minutes) * 60,
            'increment': int(increment)
        }
    except ValueError:
        return {'mode': 'unlimited', 'initial_seconds': None, 'increment': 0}


def get_time_payload(game):
    return {
        'white_left': game.white_time_left,
        'black_left': game.black_time_left,
        'white_spent': game.white_time_spent,
        'black_spent': game.black_time_spent,
        'duration': game.game_duration_seconds
    }


def build_san_list(pgn_text):
    san_moves = []
    temp_board = chess.Board()
    if not pgn_text:
        return san_moves
    for uci in pgn_text.strip().split():
        try:
            move = chess.Move.from_uci(uci)
            san_moves.append(temp_board.san(move))
            temp_board.push(move)
        except Exception:
            san_moves.append(uci)
    return san_moves


def calculate_captured_data(board):
    captured_pieces = {'white': [], 'black': []}
    initial_white = {'P': 8, 'N': 2, 'B': 2, 'R': 2, 'Q': 1, 'K': 1}
    initial_black = {'p': 8, 'n': 2, 'b': 2, 'r': 2, 'q': 1, 'k': 1}

    current_counts = {}
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            current_counts[piece.symbol()] = current_counts.get(piece.symbol(), 0) + 1

    for symbol, initial_count in initial_white.items():
        current_count = current_counts.get(symbol, 0)
        deficit = initial_count - current_count
        for _ in range(deficit):
            captured_pieces['black'].append(symbol.lower())

    for symbol, initial_count in initial_black.items():
        current_count = current_counts.get(symbol, 0)
        deficit = initial_count - current_count
        for _ in range(deficit):
            captured_pieces['white'].append(symbol.upper())

    piece_values = {
        'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0,
        'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0
    }
    white_score = sum(piece_values.get(p, 0) for p in captured_pieces['white'])
    black_score = sum(piece_values.get(p, 0) for p in captured_pieces['black'])
    return captured_pieces, white_score, black_score


def build_state_payload(game, board=None, captured_info=None):
    board_obj = board or chess.Board(game.fen)
    if captured_info:
        captured_pieces, white_score, black_score = captured_info
    else:
        captured_pieces, white_score, black_score = calculate_captured_data(board_obj)
    return {
        'fen': game.fen,
        'pgn': game.pgn,
        'legal_moves': [move.uci() for move in board_obj.legal_moves],
        'moves_san': build_san_list(game.pgn),
        'white_moves': game.white_moves.split() if game.white_moves else [],
        'black_moves': game.black_moves.split() if game.black_moves else [],
        'time_control': game.time_control,
        'is_game_over': board_obj.is_game_over(),
        'status': game.status,
        'captured_pieces': captured_pieces,
        'white_score': white_score,
        'black_score': black_score,
        'time_tracking': get_time_payload(game),
        'redo_available': len(load_redo_stack(game)) > 0
    }


def load_redo_stack(game):
    if not game.redo_stack:
        return []
    try:
        return json.loads(game.redo_stack)
    except json.JSONDecodeError:
        return []


def save_redo_stack(game, stack):
    game.redo_stack = json.dumps(stack)


def apply_time_snapshot(game, snapshot):
    if not snapshot:
        return

    def to_int(value):
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    player_is_white = game.player_color == 'white'

    player_spent = to_int(snapshot.get('player_spent'))
    opponent_spent = to_int(snapshot.get('opponent_spent'))
    player_left = to_int(snapshot.get('player_left'))
    opponent_left = to_int(snapshot.get('opponent_left'))
    duration = to_int(snapshot.get('duration'))

    if player_is_white:
        if player_spent is not None:
            game.white_time_spent = max(0, player_spent)
        if player_left is not None:
            game.white_time_left = player_left
        if opponent_spent is not None:
            game.black_time_spent = max(0, opponent_spent)
        if opponent_left is not None:
            game.black_time_left = opponent_left
    else:
        if player_spent is not None:
            game.black_time_spent = max(0, player_spent)
        if player_left is not None:
            game.black_time_left = player_left
        if opponent_spent is not None:
            game.white_time_spent = max(0, opponent_spent)
        if opponent_left is not None:
            game.white_time_left = opponent_left

    if duration is not None and duration > (game.game_duration_seconds or 0):
        game.game_duration_seconds = duration

@game_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_game():
    if request.method == 'POST':
        difficulty = request.form.get('difficulty', 'medium')
        player_color = request.form.get('color', 'white')
        time_control = request.form.get('time_control', 'rapid:15+10')
        time_setup = parse_time_control(time_control)
        opponent_username = request.form.get('opponent')
        opponent = None
        opponent_id = None
        if opponent_username:
            from app.models import User
            opponent = User.query.filter_by(username=opponent_username).first()
            if opponent:
                opponent_id = opponent.id
        
        game = Game(
            player_id=current_user.id,
            opponent_id=opponent_id,
            difficulty=difficulty,
            player_color=player_color,
            fen=chess.STARTING_FEN,
            pgn='',
            time_control=time_control,
            white_moves='',
            black_moves='',
            white_time_left=time_setup['initial_seconds'],
            black_time_left=time_setup['initial_seconds'],
            white_time_spent=0,
            black_time_spent=0,
            game_duration_seconds=0,
            white_score=0,
            black_score=0,
            redo_stack='[]'
        )
        db.session.add(game)
        db.session.commit()
        
        # Redirect to view the game
        return redirect(url_for('game.view_game', game_id=game.id))
    
    # GET request - show game setup form
    return render_template('game/new.html')

@game_bp.route('/<int:game_id>/board')
@login_required
def get_board(game_id):
    game = Game.query.get_or_404(game_id)
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    return jsonify(build_state_payload(game))

@game_bp.route('/<int:game_id>/move', methods=['POST'])
@login_required
def make_move(game_id):
    game = Game.query.get_or_404(game_id)
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    if game.status != 'active':
        return {'error': 'Game is not active'}, 400
    
    data = request.get_json() or {}
    move_uci = data.get('move')
    time_snapshot = data.get('time_snapshot')
    time_info = parse_time_control(game.time_control)
    
    board = chess.Board(game.fen)

    if time_snapshot:
        apply_time_snapshot(game, time_snapshot)
    
    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            # record which side is moving now
            side_before = board.turn
            # push player's move
            board.push(move)

            # record player's move into white/black lists
            moves_white = (game.white_moves or '').strip().split() if game.white_moves else []
            moves_black = (game.black_moves or '').strip().split() if game.black_moves else []
            if side_before == chess.WHITE:
                moves_white.append(move_uci)
            else:
                moves_black.append(move_uci)

            # If this is a single-player game (no opponent), let AI reply
            ai_move = None
            ai_delay_ms = 0
            if not board.is_game_over() and not game.opponent_id:
                ai = SimpleChessAI(board, game.difficulty)
                ai_move = ai.get_best_move()
                if ai_move:
                    if game.difficulty == 'easy':
                        ai_delay_ms = int(random.uniform(0.4, 0.9) * 1000)
                    elif game.difficulty == 'medium':
                        ai_delay_ms = int(random.uniform(0.8, 1.4) * 1000)
                    else:
                        ai_delay_ms = int(random.uniform(1.2, 1.8) * 1000)

                    elapsed = ai_delay_ms // 1000
                    if elapsed > 0:
                        if game.player_color == 'white':
                            game.black_time_spent = (game.black_time_spent or 0) + elapsed
                            if game.black_time_left is not None:
                                game.black_time_left = max(0, (game.black_time_left or 0) - elapsed)
                                if time_info['increment']:
                                    game.black_time_left += time_info['increment']
                        else:
                            game.white_time_spent = (game.white_time_spent or 0) + elapsed
                            if game.white_time_left is not None:
                                game.white_time_left = max(0, (game.white_time_left or 0) - elapsed)
                                if time_info['increment']:
                                    game.white_time_left += time_info['increment']
                    # record side for AI move
                    side_before_ai = board.turn
                    board.push(ai_move)
                    # append AI move
                    if side_before_ai == chess.WHITE:
                        moves_white.append(ai_move.uci())
                    else:
                        moves_black.append(ai_move.uci())

            # Clear redo stack because we branched forward
            save_redo_stack(game, [])

            # update stored moves and pgn
            game.white_moves = ' '.join(moves_white)
            game.black_moves = ' '.join(moves_black)
            game.pgn = (game.pgn or '').strip()
            game.pgn = (game.pgn + ' ' + move_uci).strip()
            if ai_move:
                game.pgn = (game.pgn + ' ' + ai_move.uci()).strip()

            game.fen = board.fen()

            # Check game status - determine winner correctly
            if board.is_checkmate():
                # After a checkmate, it's the checkmated player's turn (board.turn)
                # So if it's white's turn now, white was checkmated (black won)
                # If it's black's turn now, black was checkmated (white won)
                if board.turn == chess.WHITE:
                    # White was checkmated, so if player is white, player lost
                    if game.player_color == 'white':
                        game.status = 'lost'
                    else:
                        game.status = 'won'
                else:
                    # Black was checkmated, so if player is white, player won
                    if game.player_color == 'white':
                        game.status = 'won'
                    else:
                        game.status = 'lost'
            elif board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
                game.status = 'draw'
            else:
                game.status = 'active'

            db.session.commit()

            captured_pieces, white_score, black_score = calculate_captured_data(board)
            game.white_score = white_score
            game.black_score = black_score
            db.session.commit()

            payload = build_state_payload(game, board, (captured_pieces, white_score, black_score))
            payload.update({
                'ai_move': ai_move.uci() if ai_move else None,
                'ai_delay_ms': ai_delay_ms,
                'last_move': move_uci
            })
            return jsonify(payload)
        else:
            return {'error': 'Invalid move'}, 400
    except Exception as e:
        return {'error': str(e)}, 400

@game_bp.route('/<int:game_id>')
@login_required
def view_game(game_id):
    game = Game.query.get_or_404(game_id)
    # Allow owner or invited opponent to view the game
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    return render_template('game/play.html', game=game)


@game_bp.route('/<int:game_id>/undo', methods=['POST'])
@login_required
def undo_move(game_id):
    game = Game.query.get_or_404(game_id)
    # Only allow undo in single-player (vs AI)
    if game.opponent_id:
        return {'error': 'Undo allowed only against AI'}, 403

    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403

    payload = request.get_json(silent=True) or {}
    time_snapshot = payload.get('time_snapshot')
    if time_snapshot:
        apply_time_snapshot(game, time_snapshot)

    # pgn is space-separated UCI moves
    moves = (game.pgn or '').strip().split()
    original_moves = moves[:]
    if not moves:
        return {'error': 'No moves to undo'}, 400

    # If player wants to undo, remove last two plies (player+AI) if possible
    # If only one ply exists, remove it
    if len(moves) >= 2:
        moves = moves[:-2]
    else:
        moves = []
    removed = original_moves[len(moves):]
    redo_stack = load_redo_stack(game)
    if removed:
        redo_stack.append(removed)
        save_redo_stack(game, redo_stack)

    # Rebuild board from remaining moves and recompute per-player lists
    board = chess.Board()
    white_moves = []
    black_moves = []
    for u in moves:
        try:
            m = chess.Move.from_uci(u)
            if board.turn == chess.WHITE:
                white_moves.append(u)
            else:
                black_moves.append(u)
            board.push(m)
        except Exception:
            pass

    game.pgn = ' '.join(moves)
    game.white_moves = ' '.join(white_moves)
    game.black_moves = ' '.join(black_moves)
    game.fen = board.fen()
    game.status = 'active'
    db.session.commit()

    captured_info = calculate_captured_data(board)
    game.white_score = captured_info[1]
    game.black_score = captured_info[2]
    db.session.commit()

    return jsonify(build_state_payload(game, board, captured_info))


@game_bp.route('/<int:game_id>/redo', methods=['POST'])
@login_required
def redo_move(game_id):
    game = Game.query.get_or_404(game_id)
    if game.opponent_id:
        return {'error': 'Redo allowed only against AI'}, 403
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403

    payload = request.get_json(silent=True) or {}
    time_snapshot = payload.get('time_snapshot')
    if time_snapshot:
        apply_time_snapshot(game, time_snapshot)

    stack = load_redo_stack(game)
    if not stack:
        return {'error': 'No moves to redo'}, 400

    moves_to_apply = stack.pop()
    current_moves = (game.pgn or '').strip().split()
    current_moves.extend(moves_to_apply)

    board = chess.Board()
    white_moves = []
    black_moves = []
    for u in current_moves:
        try:
            m = chess.Move.from_uci(u)
            if board.turn == chess.WHITE:
                white_moves.append(u)
            else:
                black_moves.append(u)
            board.push(m)
        except Exception:
            pass

    game.pgn = ' '.join(current_moves)
    game.white_moves = ' '.join(white_moves)
    game.black_moves = ' '.join(black_moves)
    game.fen = board.fen()
    game.status = 'active'
    save_redo_stack(game, stack)
    db.session.commit()

    captured_info = calculate_captured_data(board)
    game.white_score = captured_info[1]
    game.black_score = captured_info[2]
    db.session.commit()

    payload = build_state_payload(game, board, captured_info)
    payload['redo_available'] = len(stack) > 0
    return jsonify(payload)

@game_bp.route('/<int:game_id>/leave', methods=['POST'])
@login_required
def leave_game(game_id):
    game = Game.query.get_or_404(game_id)
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    payload = request.get_json(silent=True) or {}
    snapshot = payload.get('time_snapshot')
    if snapshot:
        apply_time_snapshot(game, snapshot)
    if game.status not in ('won', 'lost', 'draw'):
        game.status = 'finished'
    db.session.commit()
    return jsonify({'status': 'ok', 'game_status': game.status})


@game_bp.route('/<int:game_id>/resume', methods=['POST'])
@login_required
def resume_game(game_id):
    game = Game.query.get_or_404(game_id)
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    if game.status != 'finished':
        return {'error': 'Game is not paused'}, 400

    payload = request.get_json(silent=True) or {}
    snapshot = payload.get('time_snapshot')
    if snapshot:
        apply_time_snapshot(game, snapshot)

    game.status = 'active'
    db.session.commit()
    return jsonify(build_state_payload(game))


@game_bp.route('/<int:game_id>/resign', methods=['POST'])
@login_required
def resign(game_id):
    game = Game.query.get_or_404(game_id)
    if game.player_id != current_user.id and game.opponent_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    payload = request.get_json(silent=True) or {}
    snapshot = payload.get('time_snapshot')
    if snapshot:
        apply_time_snapshot(game, snapshot)
    
    # Mark game as lost for the player who resigned
    if game.player_id == current_user.id:
        game.status = 'lost'
    else:
        game.status = 'won'
    
    db.session.commit()
    
    return jsonify({'status': 'ok', 'game_status': game.status})
