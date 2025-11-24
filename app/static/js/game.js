document.addEventListener('DOMContentLoaded', () => {
    if (typeof gameId === 'undefined' || typeof playerColor === 'undefined') {
        console.error('Липсва мета информация за играта.');
        return;
    }

    window.chessGame = new ChessGame({
        gameId,
        playerColor,
        boardTheme: typeof boardTheme === 'string' ? boardTheme : 'classic',
        isMultiplayer: Boolean(isMultiplayer),
        initialStatus: typeof initialGameStatus === 'string' ? initialGameStatus : 'active'
    });

    bindUiControls();
    setupLeaveModal();
    attachBeforeUnload();
});

function bindUiControls() {
    const btnResign = document.getElementById('resignBtn');
    const btnNew = document.getElementById('newGameBtn');
    const btnUndo = document.getElementById('undoBtn');
    const btnRedo = document.getElementById('redoBtn');
    const btnResume = document.getElementById('resumeBtn');
    const toggleMoves = document.getElementById('toggleMoves');
    const toggleSound = document.getElementById('soundToggle');
    const toggleSoundLabel = document.getElementById('soundStatus');
    const toggleMovesLabel = document.getElementById('toggleStatus');

    if (btnResign) btnResign.addEventListener('click', () => window.chessGame?.resign());
    if (btnNew) btnNew.addEventListener('click', () => window.chessGame?.startNewGame());
    if (btnUndo) btnUndo.addEventListener('click', () => window.chessGame?.requestUndo());
    if (btnRedo) btnRedo.addEventListener('click', () => window.chessGame?.requestRedo());
    if (btnResume) {
        btnResume.addEventListener('click', () => {
            btnResume.disabled = true;
            window.chessGame?.resumeGame()
                .finally(() => {
                    btnResume.disabled = false;
                });
        });
    }

    if (toggleMoves) {
        const syncMoveLabel = (checked) => {
            if (toggleMovesLabel) {
                toggleMovesLabel.textContent = checked
                    ? 'Показвай възможните ходове'
                    : 'Скрий възможните ходове';
            }
        };
        syncMoveLabel(toggleMoves.checked);
        window.chessGame?.toggleMoveHints(toggleMoves.checked);
        toggleMoves.addEventListener('change', (e) => {
            window.chessGame?.toggleMoveHints(e.target.checked);
            syncMoveLabel(e.target.checked);
        });
    }

    if (toggleSound) {
        const syncSoundLabel = (checked) => {
            if (toggleSoundLabel) {
                toggleSoundLabel.textContent = checked ? 'Звук: включен' : 'Звук: изключен';
            }
        };
        const enabled = window.chessGame?.audio?.enabled !== false;
        toggleSound.checked = enabled;
        syncSoundLabel(enabled);
        toggleSound.addEventListener('change', (e) => {
            window.chessGame?.toggleSound(e.target.checked);
            syncSoundLabel(e.target.checked);
        });
    }
}

function setupLeaveModal() {
    const modal = document.getElementById('leaveModal');
    if (!modal) return;

    const confirmBtn = document.getElementById('confirmLeave');
    const cancelBtn = document.getElementById('cancelLeave');
    const closeBtn = modal.querySelector('.modal-close');

    const hideModal = () => modal.classList.remove('show');
    const openModalFor = (href) => {
        modal.dataset.targetHref = href;
        modal.classList.add('show');
    };

    const shouldIntercept = (link) => {
        if (!window.chessGame?.isGameActive()) return false;
        if (!link || !link.href) return false;
        if (link.dataset.ignoreLeave === 'true') return false;
        if (link.getAttribute('href').startsWith('#')) return false;
        if (link.href.includes(`/game/${gameId}`)) return false;
        return true;
    };

    document.querySelectorAll('a[href]').forEach((link) => {
        link.addEventListener('click', (event) => {
            if (!shouldIntercept(link)) return;
            event.preventDefault();
            openModalFor(link.href);
        });
    });

    confirmBtn?.addEventListener('click', () => {
        const target = modal.dataset.targetHref || '/';
        confirmBtn.disabled = true;
        window.chessGame?.leaveGame()
            .finally(() => {
                window.location.href = target;
            });
    });

    [cancelBtn, closeBtn].forEach((btn) => {
        btn?.addEventListener('click', () => {
            confirmBtn.disabled = false;
            hideModal();
        });
    });
}

function attachBeforeUnload() {
    window.addEventListener('beforeunload', () => {
        if (window.chessGame && window.chessGame.isGameActive()) {
            const snapshot = window.chessGame.buildTimeSnapshot?.();
            const payload = JSON.stringify({ time_snapshot: snapshot });
            if (navigator.sendBeacon) {
                const blob = new Blob([payload], { type: 'application/json' });
                navigator.sendBeacon(`/game/${gameId}/leave`, blob);
            } else {
                fetch(`/game/${gameId}/leave`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: payload,
                    keepalive: true
                });
            }
        }
    });
}
