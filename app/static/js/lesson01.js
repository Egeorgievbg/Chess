document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('gameBoard');
    const boardWrapper = document.querySelector('.board-wrapper');
    const palette = document.getElementById('piecePalette');
    const checkBtn = document.getElementById('checkBtn');
    const resetBtn = document.getElementById('resetBtn');
    const instructionText = document.getElementById('instructionText');
    const feedbackMsg = document.getElementById('feedbackMessage');
    const nextLessonBtn = document.getElementById('nextLessonBtn');

    const targets = window.LESSON_TARGETS || {};
    const lessonMode = window.LESSON_MODE || 'arrange';
    let selectedPieceCode = null;
    let movingFromSquare = null;

    const renderSquare = (square, code) => {
        if (!square) return;
        if (code) {
            square.innerHTML = `<img src="/static/img/pieces/${code}.svg" alt="piece">`;
            square.dataset.placed = code;
        } else {
            square.innerHTML = '';
            delete square.dataset.placed;
        }
    };

    const populateBoard = () => {
        document.querySelectorAll('.square').forEach(square => {
            const code = lessonMode === 'move' ? targets[square.dataset.square] : null;
            renderSquare(square, code);
            square.classList.remove('selected-piece', 'error');
        });
        selectedPieceCode = null;
        movingFromSquare = null;
        document.querySelectorAll('.piece-btn').forEach(btn => btn.classList.remove('active'));
    };

    populateBoard();

    const clearSelection = () => {
        if (movingFromSquare) {
            movingFromSquare.classList.remove('selected-piece');
            movingFromSquare = null;
        }
        selectedPieceCode = null;
        document.querySelectorAll('.piece-btn').forEach(btn => btn.classList.remove('active'));
    };

    palette.addEventListener('click', (event) => {
        const btn = event.target.closest('.piece-btn');
        if (!btn) return;

        document.querySelectorAll('.piece-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedPieceCode = btn.dataset.piece;
        if (movingFromSquare) {
            movingFromSquare.classList.remove('selected-piece');
            movingFromSquare = null;
        }
        const pieceName = btn.querySelector('.piece-name')?.innerText || 'фигура';
        instructionText.innerHTML = `Избра <span style="color:#ef6c00">${pieceName}</span>. Докосни квадрата на дъската.`;
        instructionText.style.color = '#2c1810';
    });

    board.addEventListener('click', (event) => {
        const square = event.target.closest('.square');
        if (!square) return;

        if (!selectedPieceCode) {
            if (lessonMode === 'move' && square.dataset.placed) {
                selectedPieceCode = square.dataset.placed;
                movingFromSquare = square;
                square.classList.add('selected-piece');
                renderSquare(square, null);
                instructionText.innerText = 'Хванахме фигурата – избери къде да отиде.';
                instructionText.style.color = '#1565c0';
                return;
            }
            instructionText.innerText = 'Избери фигура от палитрата или докосни квадрат с вече поставена фигура.';
            instructionText.style.color = '#ef5350';
            return;
        }

        if (movingFromSquare) {
            movingFromSquare.classList.remove('selected-piece');
            movingFromSquare = null;
        }

        renderSquare(square, selectedPieceCode);
        instructionText.innerText = 'Преместването е готово!';
        instructionText.style.color = '#1565c0';
        selectedPieceCode = null;
        document.querySelectorAll('.piece-btn').forEach(btn => btn.classList.remove('active'));
    });

    checkBtn.addEventListener('click', () => {
        let errors = 0;
        let correctCount = 0;
        const totalTargets = Object.keys(targets).length;
        let placedCount = 0;

        document.querySelectorAll('.square').forEach(square => {
            square.classList.remove('error');
            if (square.dataset.placed) placedCount++;
        });

        if (placedCount === 0) {
            feedbackMsg.innerText = 'Дъската е празна – сложи фигурите, за да видим правила!';
            feedbackMsg.style.color = '#ef5350';
            return;
        }

        Object.entries(targets).forEach(([coords, expected]) => {
            const square = document.querySelector(`.square[data-square="${coords}"]`);
            if (!square) return;
            const placed = square.dataset.placed;
            if (placed === expected) {
                correctCount++;
            } else if (placed) {
                square.classList.add('error');
                errors++;
            }
        });

        if (correctCount === totalTargets && errors === 0) {
            handleSuccess();
        } else {
            handleError(errors, totalTargets - correctCount);
        }
    });

    resetBtn.addEventListener('click', () => {
        populateBoard();
        feedbackMsg.innerText = '';
        instructionText.innerText = 'Дъската е готова. Начни пак!';
        instructionText.style.color = '#2c1810';
        checkBtn.style.display = 'flex';
        nextLessonBtn.classList.add('hidden');
    });

    function handleSuccess() {
        feedbackMsg.innerHTML = '🎉 Браво! Всичко е поставено според правилата.';
        feedbackMsg.style.color = '#4caf50';
        instructionText.innerText = 'Урокът е готов!';
        checkBtn.style.display = 'none';
        nextLessonBtn.classList.remove('hidden');
        if (typeof confetti === 'function') {
            confetti({
                particleCount: 120,
                spread: 60,
                origin: { y: 0.5 }
            });
        }
    }

    function handleError(errors, missing) {
        if (errors > 0) {
            feedbackMsg.innerText = 'Виж червените полета и ги оправи!';
        } else {
            feedbackMsg.innerText = 'Някои фигури липсват.';
        }
        feedbackMsg.style.color = '#ef5350';
        board.classList.add('shake');
        boardWrapper?.classList.add('shake');
        setTimeout(() => {
            board.classList.remove('shake');
            boardWrapper?.classList.remove('shake');
        }, 200);
    }
});
