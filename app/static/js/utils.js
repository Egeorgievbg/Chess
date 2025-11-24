class AudioManager {
    constructor() {
        this.enabled = localStorage.getItem('soundEnabled') !== 'false';
        this.audioContext = null;
        this.masterVolume = parseFloat(localStorage.getItem('masterVolume') || '0.5');
        this.timerInterval = null;
    }

    beep(frequency = 880, duration = 100, type = 'sine') {
        if (!this.enabled) return;
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.frequency.value = frequency;
            osc.type = type;
            gain.gain.setValueAtTime(this.masterVolume * 0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration / 1000);

            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + duration / 1000);
        } catch (e) {
            console.warn('Audio not available in this browser.');
        }
    }

    tickTack(isTick = true) {
        if (!this.enabled) return;
        const freq = isTick ? 800 : 700;
        this.beep(freq, 50, 'sine');
    }

    startTickTimer(secondsRemaining) {
        this.stopTickTimer();
        if (secondsRemaining <= 0) return;
        let isTickPhase = true;
        this.timerInterval = setInterval(() => {
            this.tickTack(isTickPhase);
            isTickPhase = !isTickPhase;
        }, 500);
    }

    stopTickTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    moveSound() {
        this.beep(600, 50, 'sine');
    }

    captureSound() {
        this.beep(900, 80, 'sine');
    }

    checkSound() {
        this.beep(1200, 100, 'sine');
    }

    endGameSound() {
        this.beep(400, 300);
    }

    illegalMoveSound() {
        this.beep(300, 100);
    }

    timeWarningSound() {
        this.beep(1500, 100);
    }

    toggleSound() {
        this.enabled = !this.enabled;
        localStorage.setItem('soundEnabled', this.enabled);
        return this.enabled;
    }

    setVolume(volume) {
        this.masterVolume = Math.max(0, Math.min(1, volume));
        localStorage.setItem('masterVolume', this.masterVolume);
    }
}

class GameReplay {
    constructor(movesList) {
        this.moves = movesList;
        this.currentIndex = -1;
        this.isPlaying = false;
        this.speed = 1000;
    }

    play() {
        this.isPlaying = true;
        this.playNext();
    }

    pause() {
        this.isPlaying = false;
    }

    stop() {
        this.isPlaying = false;
        this.currentIndex = -1;
    }

    playNext() {
        if (!this.isPlaying || this.currentIndex >= this.moves.length - 1) return;
        this.currentIndex += 1;
        setTimeout(() => this.playNext(), this.speed);
    }

    playPrevious() {
        this.currentIndex = Math.max(-1, this.currentIndex - 1);
    }

    setSpeed(milliseconds) {
        this.speed = Math.max(200, milliseconds);
    }
}

class NotificationManager {
    static show(message, type = 'info', duration = 3000) {
        if (!this.container) {
            this.container = this.createContainer();
        }
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        this.container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    static createContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 999;
            pointer-events: none;
        `;
        document.body.appendChild(container);
        return container;
    }

    static success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    static error(message, duration = 3000) {
        return this.show(message, 'error', duration);
    }

    static warning(message, duration = 3000) {
        return this.show(message, 'warning', duration);
    }

    static info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }
}

class CapturedPiecesTracker {
    constructor() {
        this.PIECE_VALUES = {
            P: 1,
            N: 3,
            B: 3,
            R: 5,
            Q: 9
        };
        this.whiteCaptured = [];
        this.blackCaptured = [];
    }

    addCapturedPiece(piece, capturedBy) {
        const normalized = piece.toLowerCase();
        if (capturedBy === 'white') {
            this.whiteCaptured.push(normalized);
        } else {
            this.blackCaptured.push(normalized);
        }
    }

    getScore(list) {
        return list.reduce((sum, p) => sum + (this.PIECE_VALUES[p.toUpperCase()] || 0), 0);
    }

    renderCaptured() {
        const symbols = { p: '♙', n: '♘', b: '♗', r: '♖', q: '♕' };
        const renderList = (pieces) => pieces.map((p) => symbols[p] || p).join(' ');
        return {
            white: `${renderList(this.whiteCaptured)} (+${this.getScore(this.whiteCaptured)})`,
            black: `${renderList(this.blackCaptured)} (+${this.getScore(this.blackCaptured)})`
        };
    }
}

class MoveAnalyzer {
    static getMoveQuality(moveData) {
        if (moveData.isMate) {
            return { quality: 'excellent', message: 'Мат! Перфектен финал.', score: 100 };
        }
        if (moveData.isCheck) {
            return { quality: 'good', message: 'Шах – противникът е под напрежение.', score: 80 };
        }
        if (moveData.isCapture) {
            return { quality: 'good', message: 'Спечелен материал. Отлична размяна.', score: 70 };
        }
        if (moveData.isPawnPromotion) {
            return { quality: 'excellent', message: 'Пешката стана силна фигура!', score: 90 };
        }
        if (moveData.isCastling) {
            return { quality: 'good', message: 'Рокада – кралят е защитен.', score: 75 };
        }
        return { quality: 'neutral', message: 'Спокоен ход за подобряване на позицията.', score: 50 };
    }

    static getMoveCategory(moveData) {
        if (moveData.isCapture) return 'capture';
        if (moveData.isCheck) return 'check';
        if (moveData.isCastling) return 'castling';
        if (moveData.isPawnPromotion) return 'promotion';
        return 'normal';
    }
}

window.AudioManager = AudioManager;
window.GameReplay = GameReplay;
window.NotificationManager = NotificationManager;
window.MoveAnalyzer = MoveAnalyzer;
