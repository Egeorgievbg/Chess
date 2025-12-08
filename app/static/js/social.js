(function () {
    if (typeof io === 'undefined') {
        return;
    }

    const socket = io();
    window.socket = socket;

    const statusBadge = document.getElementById('socketStatusBadge');

    const connectionMessages = {
        on: 'Сървърът е свързан',
        connecting: 'Свързване...',
        reconnecting: 'Опитваме се да се свържем...',
        offline: 'Връзката е прекъсната'
    };

    const pendingChallengeButtons = new Map();
    const statusTimers = new Map();

    function getFriendCard(userId) {
        if (userId === undefined || userId === null) return null;
        const normalized = `${userId}`;
        return document.querySelector(`.friend-card[data-user-id="${normalized}"]`);
    }

    function clearCardStatus(card) {
        if (!card) return;
        const statusEl = card.querySelector('.friend-action-status');
        if (!statusEl) return;
        statusEl.textContent = '';
        delete statusEl.dataset.state;
        const key = card.dataset.userId;
        if (!key) return;
        const timer = statusTimers.get(key);
        if (timer) {
            clearTimeout(timer);
            statusTimers.delete(key);
        }
    }

    function showCardStatus(card, state, text, duration = 4000) {
        if (!card) return;
        const statusEl = card.querySelector('.friend-action-status');
        if (!statusEl) return;
        statusEl.textContent = text || '';
        if (state) {
            statusEl.dataset.state = state;
        } else {
            delete statusEl.dataset.state;
        }
        const key = card.dataset.userId;
        if (!key) return;
        const prevTimer = statusTimers.get(key);
        if (prevTimer) {
            clearTimeout(prevTimer);
            statusTimers.delete(key);
        }
        if (duration && duration > 0) {
            const timer = setTimeout(() => clearCardStatus(card), duration);
            statusTimers.set(key, timer);
        }
    }

    function updateConnectionBadge(state) {
        if (!statusBadge) return;
        if (state === 'on') {
            statusBadge.classList.add('hidden');
            return;
        }
        statusBadge.textContent = connectionMessages[state] || connectionMessages.connecting;
        statusBadge.classList.remove('hidden');
    }

    function formatLastSeen(value) {
        if (!value) return 'Няма данни';
        const parsed = Date.parse(value);
        if (Number.isNaN(parsed)) return 'Няма данни';
        const date = new Date(parsed);
        return date.toLocaleString('bg-BG', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function updateFriendStatus(userId, online, lastSeen) {
        const card = document.querySelector(`.friend-card[data-user-id="${userId}"]`);
        if (!card) return;
        const dot = card.querySelector('.status-dot');
        const statusText = card.querySelector('.friend-status-text');
        const button = card.querySelector('.play-online-btn');

        dot?.classList.toggle('status-online', online);
        if (statusText) {
            if (online) {
                statusText.textContent = 'На линия';
            } else {
                statusText.textContent = `Последно: ${formatLastSeen(lastSeen || statusText.dataset.lastSeen)}`;
                statusText.dataset.lastSeen = lastSeen || statusText.dataset.lastSeen;
            }
        }

        if (button) {
            button.disabled = !online;
        }
    }

    function handleNotification(payload) {
        if (!payload) return;
        const message = payload.message || 'Ново съобщение';
        const type = payload.type || 'info';
        const actions = [];

        if (type === 'challenge') {
            actions.push({
                label: 'Приемам',
                className: 'primary',
                callback(button) {
                    button.disabled = true;
                    socket.emit('accept_challenge', { notification_id: payload.id });
                }
            });
            actions.push({
                label: 'Отказвам',
                className: 'secondary',
                callback() {
                    NotificationManager.warning('Поканата беше отменена.');
                },
                dismiss: true
            });
        }

        const duration = actions.length ? null : 4000;
        NotificationManager.info(message, duration, { actions });
    }

    function handleChallengeAccepted(data) {
        if (!data || !data.redirect_url) return;
        NotificationManager.success('Играта започва! Пренасочваме те...');
        setTimeout(() => {
            window.location.href = data.redirect_url;
        }, 800);
    }

    socket.on('connect', () => updateConnectionBadge('on'));
    socket.on('disconnect', () => updateConnectionBadge('offline'));
    socket.on('connect_error', () => updateConnectionBadge('reconnecting'));
    socket.on('reconnect_attempt', () => updateConnectionBadge('reconnecting'));
    socket.on('reconnect', () => updateConnectionBadge('on'));

    socket.on('user_online', (payload) => {
        if (!payload) return;
        updateFriendStatus(payload.user_id, true, payload.last_seen);
    });
    socket.on('user_offline', (payload) => {
        if (!payload) return;
        updateFriendStatus(payload.user_id, false, payload.last_seen);
    });
    socket.on('friend_statuses', (payload) => {
        if (!payload?.friends?.length) return;
        payload.friends.forEach((friend) => {
            updateFriendStatus(friend.user_id, friend.is_online, friend.last_seen);
        });
    });

    socket.on('notification', handleNotification);
    socket.on('notification_error', (payload) => {
        if (!payload) return;
        NotificationManager.error(payload.message || 'Възникна грешка.');
        const recipientId = payload.recipient_id;
        if (recipientId) {
            const card = getFriendCard(recipientId);
            showCardStatus(card, 'error', payload.message || 'Поканата не можа да бъде изпратена.', 4000);
            releaseChallengeButton(recipientId, { keepStatus: true });
        }
    });
    socket.on('challenge_accepted', handleChallengeAccepted);
    socket.on('challenge_sent', (payload) => {
        NotificationManager.success('Поканата беше изпратена.');
        if (payload?.recipient_id) {
            const card = getFriendCard(payload.recipient_id);
            showCardStatus(card, 'success', 'Поканата е изпратена.', 3200);
            releaseChallengeButton(payload.recipient_id, { keepStatus: true });
        }
    });

    function releaseChallengeButton(recipientId, options = {}) {
        if (recipientId === undefined || recipientId === null) return;
        const key = `${recipientId}`;
        const entry = pendingChallengeButtons.get(key);
        if (!entry) return;
        if (entry.timeout) {
            clearTimeout(entry.timeout);
        }
        entry.button.disabled = false;
        pendingChallengeButtons.delete(key);
        const card = getFriendCard(recipientId);
        if (!options.keepStatus) {
            clearCardStatus(card);
        }
    }

    document.addEventListener('click', (event) => {
        const btn = event.target.closest('.play-online-btn');
        if (!btn) return;
        event.preventDefault();
        if (btn.disabled) return;

        const recipientId = btn.dataset.userId;
        const username = btn.dataset.username || 'приятел';
        if (!recipientId) return;

        const numericRecipient = parseInt(recipientId, 10);
        if (Number.isNaN(numericRecipient)) return;

        btn.disabled = true;
        const key = `${numericRecipient}`;
        const timeoutId = setTimeout(() => releaseChallengeButton(key), 2000);
        pendingChallengeButtons.set(key, { button: btn, timeout: timeoutId });
        const friendCard = btn.closest('.friend-card');
        if (friendCard) {
            showCardStatus(friendCard, 'pending', 'Изпращаме поканата...', 0);
        }

        socket.emit('send_challenge', {
            recipient_id: numericRecipient
        });
        NotificationManager.info(`Изпратена покана на ${username}!`);
    });
})();
