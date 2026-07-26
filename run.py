from __future__ import annotations

import os

from app import create_app, socketio


app = create_app(os.getenv("APP_ENV", "development"))


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    socketio.run(
        app,
        host=host,
        port=port,
        debug=bool(app.debug),
        use_reloader=bool(app.debug),
    )
