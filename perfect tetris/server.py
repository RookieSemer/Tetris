import socket
import threading
import json
import time
from collections import defaultdict

HOST = '127.0.0.1'
PORT = 5555

clients = []  # List of connected clients
lobbies = {}
ready_status = {}  # Tracks whether each player is ready
lock = threading.Lock()  # Thread safety for shared data
game_in_progress = False
countdown_in_progress = False
countdown_threads = {}  # lobby_id -> thread
countdown_flags = {}

def broadcast(message, sender_conn=None):
    with lock:
        for client in clients:
            conn = client['conn']
            if conn != sender_conn:
                try:
                    conn.sendall((json.dumps(message) + "\n").encode('utf-8'))
                except:
                    pass

def send_lobby_state(lobby_id):
    lobby = lobbies[lobby_id]
    players = []
    for user in lobby['players']:
        players.append({
            'name': user,
            'ready': lobby['ready'].get(user, False)
        })
    message = {'type': 'lobby', 'players': players}
    for c in clients:
        if c['username'] in lobby['players']:
            try:
                c['conn'].sendall((json.dumps(message) + "\n").encode('utf-8'))
            except:
                pass

def start_lobby_countdown(lobby_id):
    for i in range(3, 0, -1):
        with lock:
            if (
                lobby_id not in lobbies or
                not all(lobbies[lobby_id]['ready'].get(u, False) for u in lobbies[lobby_id]['players'])
            ):
                return  # Cancel if not all ready
        # Send countdown to all players in lobby
        for user in lobbies[lobby_id]['players']:
            for c in clients:
                if c['username'] == user:
                    try:
                        c['conn'].sendall((json.dumps({'type': 'countdown', 'value': i}) + "\n").encode('utf-8'))
                    except:
                        pass
        # Wait 1 second or until cancelled
        if countdown_flags[lobby_id].wait(1):
            return  # Cancelled
    # After countdown, start game
    with lock:
        if (
            lobby_id in lobbies and
            all(lobbies[lobby_id]['ready'].get(u, False) for u in lobbies[lobby_id]['players'])
        ):
            for user in lobbies[lobby_id]['players']:
                for c in clients:
                    if c['username'] == user:
                        try:
                            c['conn'].sendall((json.dumps({'type': 'start', 'is_solo': False}) + "\n").encode('utf-8'))
                        except:
                            pass

def handle_client(conn, addr):
    global clients, lobbies, ready_status
    username = None
    current_lobby = None
    try:
        buffer = ""
        while True:
            data = conn.recv(2048)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except Exception as e:
                    print("Error parsing client message:", e, line)
                    continue

                if msg["type"] == "join":
                    username = msg["username"]
                    with lock:
                        # Remove clients with dead connections
                        valid_clients = []
                        for c in clients:
                            try:
                                c['conn'].sendall(b'')
                                valid_clients.append(c)
                            except:
                                pass
                        clients[:] = valid_clients

                        # Check for duplicate username (case-sensitive)
                        if any(c['username'] == username for c in clients):
                            conn.sendall(
                                (json.dumps({'type': 'error', 'message': 'User already online'}) + "\n").encode('utf-8')
                            )
                            continue  # Do not add, let client try again

                        # Only add after confirming not present
                        clients.append({'conn': conn, 'addr': addr, 'username': username})
                    continue

                elif msg['type'] == 'list_lobbies':
                    for_matchmaking = msg.get('for_matchmaking', False)
                    with lock:
                        lobby_list = [
                            {
                                'id': lid,
                                'name': lobbies[lid]['name'],
                                'players': len(lobbies[lid]['players']),
                                'max_players': lobbies[lid].get('max_players', 2)
                            }
                            for lid in lobbies
                            if (
                                    not lobbies[lid].get('hidden', False)
                                    or (for_matchmaking and lobbies[lid]['name'] == 'Matchmaking')
                            )
                        ]
                    conn.sendall((json.dumps({'type': 'lobby_list', 'lobbies': lobby_list}) + "\n").encode('utf-8'))

                elif msg['type'] == 'create_lobby':
                    lobby_id = str(time.time())
                    max_players = msg.get('max_players', 2)
                    hidden = msg.get('hidden', False)
                    with lock:
                        lobbies[lobby_id] = {
                            'name': msg.get('lobby_name', f"Lobby {lobby_id}"),
                            'players': [username],
                            'ready': {username: False},
                            'max_players': max_players,
                            'hidden': hidden
                        }
                        current_lobby = lobby_id
                    conn.sendall((json.dumps({'type': 'lobby_created', 'lobby_id': lobby_id}) + "\n").encode('utf-8'))
                    send_lobby_state(lobby_id)

                elif msg['type'] == 'join_lobby':
                    lobby_id = msg['lobby_id']
                    with lock:
                        if (
                                lobby_id in lobbies and
                                len(lobbies[lobby_id]['players']) < lobbies[lobby_id].get('max_players', 2)
                        ):
                            lobbies[lobby_id]['players'].append(username)
                            lobbies[lobby_id]['ready'][username] = False
                            current_lobby = lobby_id
                            conn.sendall(
                                (json.dumps({'type': 'lobby_joined', 'lobby_id': lobby_id}) + "\n").encode('utf-8'))
                            send_lobby_state(lobby_id)
                            # --- Auto-ready for matchmaking lobbies ---
                            if lobbies[lobby_id].get('hidden', False):
                                lobbies[lobby_id]['ready'][username] = True
                                send_lobby_state(lobby_id)
                                # If both players are present and ready, start countdown
                                if (
                                        len(lobbies[lobby_id]['players']) == lobbies[lobby_id].get('max_players', 2) and
                                        all(lobbies[lobby_id]['ready'].get(u, False) for u in
                                            lobbies[lobby_id]['players'])
                                ):
                                    if lobby_id not in countdown_threads or not countdown_threads[lobby_id].is_alive():
                                        countdown_flags[lobby_id] = threading.Event()
                                        t = threading.Thread(target=start_lobby_countdown, args=(lobby_id,))
                                        countdown_threads[lobby_id] = t
                                        t.start()
                        else:
                            conn.sendall((json.dumps(
                                {'type': 'error', 'message': 'Lobby full or does not exist'}) + "\n").encode('utf-8'))

                elif msg['type'] == 'get_lobby_state':
                    lobby_id = msg['lobby_id']
                    with lock:
                        if lobby_id in lobbies:
                            send_lobby_state(lobby_id)

                elif msg['type'] == 'ready':
                    if current_lobby and current_lobby in lobbies:
                        with lock:
                            lobbies[current_lobby]['ready'][username] = msg['ready']
                            send_lobby_state(current_lobby)
                            lobby = lobbies[current_lobby]
                            all_ready = (
                                len(lobby['players']) == lobby.get('max_players', 2) and
                                all(lobby['ready'].get(u, False) for u in lobby['players'])
                            )
                            if all_ready:
                                # Start countdown if not already started
                                if current_lobby not in countdown_threads or not countdown_threads[current_lobby].is_alive():
                                    countdown_flags[current_lobby] = threading.Event()
                                    t = threading.Thread(target=start_lobby_countdown, args=(current_lobby,))
                                    countdown_threads[current_lobby] = t
                                    t.start()
                            else:
                                # Cancel countdown if not all ready
                                if current_lobby in countdown_flags:
                                    countdown_flags[current_lobby].set()

                elif msg['type'] == 'leave_lobby':
                    lobby_id = msg['lobby_id']
                    with lock:
                        if lobby_id in lobbies and username in lobbies[lobby_id]['players']:
                            lobbies[lobby_id]['players'].remove(username)
                            lobbies[lobby_id]['ready'].pop(username, None)
                            # If lobby is empty, delete it
                            if not lobbies[lobby_id]['players']:
                                del lobbies[lobby_id]
                            else:
                                send_lobby_state(lobby_id)
                    # Optionally, send confirmation
                    conn.sendall((json.dumps({'type': 'lobby_left'}) + "\n").encode('utf-8'))

                elif msg['type'] == 'chat':
                    if current_lobby and current_lobby in lobbies:
                        for user in lobbies[current_lobby]['players']:
                            for c in clients:
                                if c['username'] == user:
                                    try:
                                        c['conn'].sendall((json.dumps({
                                            'type': 'chat',
                                            'username': username,
                                            'message': msg['message']
                                        }) + "\n").encode('utf-8'))
                                    except:
                                        pass

                elif msg['type'] == 'board':
                    if current_lobby and current_lobby in lobbies:
                        for user in lobbies[current_lobby]['players']:
                            if user != username:
                                for c in clients:
                                    if c['username'] == user:
                                        try:
                                            c['conn'].sendall((json.dumps({
                                                'type': 'board',
                                                'board': msg['board']
                                            }) + "\n").encode('utf-8'))
                                        except:
                                            pass

                elif msg['type'] == 'active_piece':
                    if current_lobby and current_lobby in lobbies:
                        for user in lobbies[current_lobby]['players']:
                            if user != username:
                                for c in clients:
                                    if c['username'] == user:
                                        try:
                                            c['conn'].sendall((json.dumps({
                                                'type': 'opponent_active_piece',
                                                'piece': msg['piece'],
                                                'board': msg['board']
                                            }) + "\n").encode('utf-8'))
                                        except:
                                            pass

                elif msg['type'] == 'block_update':
                    if current_lobby and current_lobby in lobbies:
                        for user in lobbies[current_lobby]['players']:
                            if user != username:
                                for c in clients:
                                    if c['username'] == user:
                                        try:
                                            c['conn'].sendall((json.dumps({
                                                'type': 'opponent_block_update',
                                                'next_queue': msg.get('next_queue', []),
                                                'hold_block': msg.get('hold_block')
                                            }) + "\n").encode('utf-8'))
                                        except:
                                            pass
                elif msg['type'] == 'score':
                    if current_lobby and current_lobby in lobbies:
                        for user in lobbies[current_lobby]['players']:
                            if user != username:
                                for c in clients:
                                    if c['username'] == user:
                                        try:
                                            c['conn'].sendall((json.dumps({
                                                'type': 'score',
                                                'value': msg['value']
                                            }) + "\n").encode('utf-8'))
                                        except:
                                            pass

                elif msg['type'] == 'game_over':
                    if current_lobby and current_lobby in lobbies:
                        with lock:
                            players = lobbies[current_lobby]['players'][:]
                            # Notify both players of result
                            for user in players:
                                for c in clients:
                                    if c['username'] == user:
                                        result = 'win' if user != username else 'lose'
                                        c['conn'].sendall(
                                            (json.dumps({'type': 'game_result', 'result': result}) + "\n").encode(
                                                'utf-8'))
                            # Reset ready status for all players in the lobby
                            for user in players:
                                lobbies[current_lobby]['ready'][user] = False
                            send_lobby_state(current_lobby)

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        with lock:
            clients[:] = [c for c in clients if c['conn'] != conn]
            if current_lobby and current_lobby in lobbies:
                if username in lobbies[current_lobby]['players']:
                    lobbies[current_lobby]['players'].remove(username)
                    del lobbies[current_lobby]['ready'][username]
                    # Notify remaining players in the lobby
                    send_lobby_state(current_lobby)
                if not lobbies[current_lobby]['players']:
                    # Remove empty lobby
                    del lobbies[current_lobby]
                # Cancel countdown if running
                if current_lobby in countdown_flags:
                    countdown_flags[current_lobby].set()
        conn.close()

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
            threading.Thread(target=start_lobby_countdown, daemon=True).start()

def handle_game_over():
    with lock:
        for c in clients:
            c['state'] = 'lobby'
            ready_status[c['username']] = False
    update_lobby()


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