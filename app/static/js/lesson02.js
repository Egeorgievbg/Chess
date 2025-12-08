document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('gameBoard');
    const palette = document.getElementById('piecePalette');
    const checkBtn = document.getElementById('checkBtn');
    const resetBtn = document.getElementById('resetBtn');
    const instructionText = document.getElementById('instructionText');
    const feedbackMsg = document.getElementById('feedbackMessage');
    const nextBtn = document.getElementById('nextLessonBtn');

    const targets = window.LESSON_TARGETS || {};
    const examples = window.LESSON_EXAMPLES || [];
    const exampleMap = {};
    examples.forEach(example => { exampleMap[example.piece_code] = example; });
    let selectedPieceCode = null;
    let movingFrom = null;

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
            const code = targets[square.dataset.square] || null;
            renderSquare(square, code);
            square.classList.remove('allowed', 'selected-piece', 'error');
        });
    };

    const clearHighlights = () => {
        document.querySelectorAll('.square').forEach(square => square.classList.remove('allowed'));
    };

    const highlightSquares = (code) => {
        clearHighlights();
        const example = exampleMap[code];
        if (!example) return;
        example.squares.forEach(coord => {
            const square = document.querySelector(`.square[data-square="${coord}"]`);
            if (square) square.classList.add('allowed');
        });
    };

    const selectPiece = (code) => {
        selectedPieceCode = code;
        movingFrom?.classList.remove('selected-piece');
        movingFrom = null;
        document.querySelectorAll('.piece-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.piece === code);
        });
        highlightSquares(code);
        const example = exampleMap[code];
        instructionText.innerText = example
            ? `Премести ${example.title.toLowerCase()} на едно от: ${example.squares.join(', ')}`
            : 'Избери фигура и натисни валидно поле.';
        instructionText.style.color = '#2c1810';
    };

    palette.addEventListener('click', (event) => {
        const btn = event.target.closest('.piece-btn');
        if (!btn) return;
        selectPiece(btn.dataset.piece);
    });

    board.addEventListener('click', (event) => {
        const square = event.target.closest('.square');
        if (!square) return;
        if (!selectedPieceCode) {
            const code = square.dataset.placed;
            if (code && exampleMap[code]) {
                selectPiece(code);
                movingFrom = square;
                square.classList.add('selected-piece');
                renderSquare(square, null);
            } else {
                instructionText.innerText = 'Избери фигура от палитрата.';
                instructionText.style.color = '#ef5350';
            }
            return;
        }
        const example = exampleMap[selectedPieceCode];
        if (!example || !example.squares.includes(square.dataset.square)) {
            feedbackMsg.innerText = 'Това поле не е позволено за тази фигура.';
            feedbackMsg.style.color = '#ef5350';
            board.classList.add('shake');
            setTimeout(() => board.classList.remove('shake'), 200);
            return;
        }
        renderSquare(square, selectedPieceCode);
        highlightSquares(selectedPieceCode);
        instructionText.innerText = 'Добре! Остава само да ги сравниш.';
        feedbackMsg.innerText = '';
        if (movingFrom) {
            movingFrom.classList.remove('selected-piece');
            movingFrom = null;
        }
        selectedPieceCode = null;
        document.querySelectorAll('.piece-btn').forEach(btn => btn.classList.remove('active'));
        clearHighlights();
    });

    checkBtn.addEventListener('click', () => {
        let errors = 0;
        let correct = 0;
        document.querySelectorAll('.square').forEach(square => {
            square.classList.remove('error');
        });
        Object.entries(targets).forEach(([coord, expected]) => {
            const square = document.querySelector(`.square[data-square="${coord}"]`);
            if (!square) return;
            if (square.dataset.placed === expected) {
                correct++;
            } else {
                square.classList.add('error');
                errors++;
            }
        });
        if (errors === 0) {
            feedbackMsg.innerText = '✔️ Всички фигури са на места!';
            feedbackMsg.style.color = '#4caf50';
        } else {
            feedbackMsg.innerText = '⚠️ Някои фигури не са на началните позиции.';
            feedbackMsg.style.color = '#ef5350';
        }
    });

    resetBtn.addEventListener('click', () => {
        populateBoard();
        feedbackMsg.innerText = '';
        instructionText.innerText = 'Прегледай позициите и избери задача.';
        selectedPieceCode = null;
        movingFrom = null;
        document.querySelectorAll('.piece-btn').forEach(btn => btn.classList.remove('active'));
        clearHighlights();
    });

    populateBoard();
});
