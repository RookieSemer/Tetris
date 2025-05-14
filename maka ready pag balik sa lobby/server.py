import socket
import threading
import json
import time
from collections import defaultdict

HOST = '127.0.0.1'
PORT = 5555

clients = []  # List of connected clients
ready_status = {}  # Tracks whether each player is ready
lock = threading.Lock()  # Thread safety for shared data
game_in_progress = False
countdown_in_progress = False

def broadcast(message, sender_conn=None):
    with lock:
        for client in clients:
            conn = client['conn']
            if conn != sender_conn:
                try:
                    conn.sendall((json.dumps(message) + "\n").encode('utf-8'))
                except:
                    pass
def handle_client(conn, addr):
    global clients, ready_status, game_in_progress, countdown_in_progress
    username = None
    try:
        buffer = ""
        # Initial handshake: wait for join message
        while True:
            chunk = conn.recv(1024).decode()
            if not chunk:
                return
            buffer += chunk
            if "\n" in buffer:
                break
        line, buffer = buffer.split("\n", 1)
        try:
            msg = json.loads(line)
            if msg["type"] == "join":
                username = msg["username"]
                with lock:
                    found = False
                    for c in clients:
                        if c['conn'] == conn:
                            c['state'] = 'lobby'
                            found = True
                    if not found:
                        clients.append({'conn': conn, 'addr': addr, 'username': username, 'state': 'lobby'})
                        ready_status[username] = False
            else:
                print("Unexpected message type on join:", msg)
                return
        except json.JSONDecodeError:
            print("Failed to parse JSON from client:", line)
            return

        update_lobby()

        while True:
            data = conn.recv(2048)
            if not data:
                break
            msg = json.loads(data.decode())

            if msg['type'] == 'ready':
                with lock:
                    for c in clients:
                        if c['username'] == username:
                            if c.get('state', 'lobby') == 'lobby':
                                ready_status[username] = msg['ready']
                            else:
                                ready_status[username] = False
                update_lobby()

            elif msg['type'] == 'chat':
                broadcast({
                    'type': 'chat',
                    'username': username,
                    'message': msg['message']
                }, sender_conn=None)

            elif msg['type'] == 'solo_start':
                with lock:
                    game_in_progress = True
                try:
                    conn.send(json.dumps({'type': 'start', 'is_solo': True}).encode())
                except:
                    pass

            elif msg['type'] == 'score':
                broadcast({'type': 'score', 'value': msg['value']}, sender_conn=conn)

            elif msg['type'] == 'board':
                broadcast({'type': 'board', 'board': msg['board']}, sender_conn=conn)

            elif msg['type'] == 'block_update':
                broadcast({
                    'type': 'opponent_block_update',
                    'username': username,
                    'next_queue': msg.get('next_queue'),
                    'hold_block': msg.get('hold_block')
                }, sender_conn=conn)

            elif msg['type'] == 'join':
                # Handle re-join (e.g., after game over)
                username = msg["username"]
                with lock:
                    for c in clients:
                        if c['conn'] == conn:
                            c['state'] = 'lobby'
                    ready_status[username] = False
                    # Reset flags on re-join
                    game_in_progress = False
                    countdown_in_progress = False
                update_lobby()

            elif msg['type'] == 'game_over':
                with lock:
                    for c in clients:
                        if c['username'] == username:
                            c['state'] = 'lobby'
                    ready_status[username] = False
                    # Reset flags on game over
                    game_in_progress = False
                    countdown_in_progress = False
                update_lobby()

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        with lock:
            clients[:] = [c for c in clients if c['conn'] != conn]
            if username in ready_status:
                del ready_status[username]
            # Reset flags on disconnect
            game_in_progress = False
            countdown_in_progress = False
            if len(clients) > 0:
                broadcast({'type': 'game_cancelled'})
        conn.close()
        update_lobby()


def update_lobby():
    global countdown_in_progress, game_in_progress
    with lock:
        players = []
        for client in clients:
            username = client['username']
            players.append({
                'name': username,
                'ready': ready_status.get(username, False)
            })

        message = {
            'type': 'lobby',
            'players': players
        }

        # Send lobby state to all clients
        for client in clients:
            try:
                client['conn'].sendall((json.dumps(message) + "\n").encode('utf-8'))
            except:
                pass

        # Check if all lobby players are ready and start countdown if needed
        lobby_players = [c for c in clients if c.get('state', 'lobby')]
        if (
            len(lobby_players) == 2 and
            all(ready_status.get(c['username'], False) for c in lobby_players) and
            not game_in_progress and
            not countdown_in_progress
        ):
            countdown_in_progress = True
            threading.Thread(target=start_game_with_countdown, daemon=True).start()

def handle_game_over():
    with lock:
        for c in clients:
            c['state'] = 'lobby'
            ready_status[c['username']] = False
    update_lobby()

def start_game_with_countdown():
    global game_in_progress, countdown_in_progress
    try:
        for i in range(3, 0, -1):
            with lock:
                ready_players = [c['username'] for c in clients
                                if ready_status.get(c['username'], False) and c.get('state', 'lobby') == 'lobby']
                if len(ready_players) != 2:
                    broadcast({'type': 'game_cancelled'})
                    countdown_in_progress = False
                    return
            broadcast({'type': 'countdown', 'value': i})
            time.sleep(1)
        with lock:
            # Set state to playing only after countdown
            for c in clients:
                if c['username'] in ready_players:
                    c['state'] = 'playing'
            game_in_progress = True
        broadcast({'type': 'start', 'is_solo': False})
    except:
        pass
    finally:
        countdown_in_progress = False

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()