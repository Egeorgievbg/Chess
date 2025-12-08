import sqlite3
import os


def ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info('{table}')")
    cols = [row[1] for row in cursor.fetchall()]
    if column in cols:
        print(f"Column '{column}' already exists on '{table}'")
        return False
    print(f"Adding column '{column}' to '{table}'")
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return True


def ensure_table(cursor, table, ddl):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if cursor.fetchone():
        print(f"Table '{table}' already exists")
        return False
    print(f"Creating table '{table}'")
    cursor.execute(ddl)
    return True


def main():
    # Locate DB relative to this script
    here = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(here, 'chess.db')
    if not os.path.exists(db_path):
        # try parent directory
        db_path = os.path.join(here, '..', 'chess.db')
        db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        print('Could not find chess.db at', db_path)
        return

    print('Using database:', db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    changed = False
    try:
        # Add user.board_theme
        changed |= ensure_column(cur, 'user', 'board_theme', "VARCHAR(30) DEFAULT 'classic'")
        changed |= ensure_column(cur, 'user', 'last_seen', "DATETIME")
        changed |= ensure_column(cur, 'user', 'sid', "VARCHAR(120)")

        # Add game.opponent_id
        changed |= ensure_column(cur, 'game', 'opponent_id', 'INTEGER')

        # Add new game fields: time_control, white_moves, black_moves
        changed |= ensure_column(cur, 'game', 'time_control', "VARCHAR(50) DEFAULT 'rapid:15+10'")
        changed |= ensure_column(cur, 'game', 'white_moves', "TEXT DEFAULT ''")
        changed |= ensure_column(cur, 'game', 'black_moves', "TEXT DEFAULT ''")

        # New tracking columns
        changed |= ensure_column(cur, 'game', 'white_time_spent', 'INTEGER DEFAULT 0')
        changed |= ensure_column(cur, 'game', 'black_time_spent', 'INTEGER DEFAULT 0')
        changed |= ensure_column(cur, 'game', 'white_time_left', 'INTEGER')
        changed |= ensure_column(cur, 'game', 'black_time_left', 'INTEGER')
        changed |= ensure_column(cur, 'game', 'game_duration_seconds', 'INTEGER DEFAULT 0')
        changed |= ensure_column(cur, 'game', 'white_score', 'INTEGER DEFAULT 0')
        changed |= ensure_column(cur, 'game', 'black_score', 'INTEGER DEFAULT 0')
        changed |= ensure_column(cur, 'game', 'redo_stack', "TEXT DEFAULT ''")
        changed |= ensure_column(cur, 'game', 'is_multiplayer_online', "BOOLEAN DEFAULT 0")

        # Friend request table
        changed |= ensure_table(cur, 'friend_request', """
        CREATE TABLE friend_request (
            id INTEGER PRIMARY KEY,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            responded_at DATETIME,
            FOREIGN KEY(sender_id) REFERENCES user(id),
            FOREIGN KEY(receiver_id) REFERENCES user(id)
        )
        """)

        changed |= ensure_table(cur, 'notification', """
        CREATE TABLE notification (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            is_read INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )
        """)
        if changed:
            conn.commit()
            print('Database updated successfully.')
        else:
            print('No changes needed.')

        # Ensure last_seen is populated for existing users
        cur.execute("UPDATE user SET last_seen = CURRENT_TIMESTAMP WHERE last_seen IS NULL")
        conn.commit()
    except Exception as e:
        print('Error:', e)
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
