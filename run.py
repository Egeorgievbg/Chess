import socket

from app import create_app, socketio


def get_local_ips():
    """Връща списък с локални IP адреси на текущата машина."""
    ips = set()
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if addr:
                ips.add(addr)
    except socket.gaierror:
        pass
    ips.update({'127.0.0.1', '::1'})
    return sorted(ips)


# Създаваме основното Flask/SocketIO приложение
app = create_app()


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5000
    ips = ', '.join(get_local_ips())
    print(f"Сървърът ще слуша на: {ips} (порт {port})")
    # Стартираме Socket.IO сървъра
    socketio.run(app, debug=True, host=host, port=port)
