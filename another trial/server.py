import socket
import threading
import json
import time  # Added for countdown

HOST = '127.0.0.1'
PORT = 5555

clients = []  # List of connected clients
ready_status = {}  # Tracks whether each player is ready
lock = threading.Lock()  # Thread safety for shared data

# Broadcast a message to all clients except the sender (if specified)
def broadcast(message, sender_conn=None):
    with lock:
        for client in clients:
            conn = client['conn']
            if conn != sender_conn:
                try:
                    conn.send(json.dumps(message).encode())
                except:
                    pass

# Handle a connected client
def handle_client(conn, addr):
    global clients, ready_status
    try:
        data = conn.recv(1024).decode()
        try:
            msg = json.loads(data)
            if msg["type"] == "join":
                username = msg["username"]
            else:
                print("Unexpected message type on join:", msg)
                return
        except json.JSONDecodeError:
            print("Failed to parse JSON from client:", data)
            return

        with lock:
            clients.append({'conn': conn, 'addr': addr, 'username': username})
            ready_status[username] = False
        update_lobby()

        while True:
            data = conn.recv(2048)
            if not data:
                break
            msg = json.loads(data.decode())

            if msg['type'] == 'ready':
                with lock:
                    ready_status[username] = msg['ready']
                update_lobby()

                # Start game when exactly 2 players are ready
                with lock:
                    if len(clients) == 2 and all(ready_status[c['username']] for c in clients):
                        threading.Thread(target=start_game_with_countdown, daemon=True).start()  # updated

            elif msg['type'] == 'score':
                broadcast({'type': 'score', 'value': msg['value']}, sender_conn=conn)

            elif msg['type'] == 'board':
                broadcast({'type': 'board', 'board': msg['board']}, sender_conn=conn)

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        with lock:
            clients[:] = [c for c in clients if c['conn'] != conn]
            if username in ready_status:
                del ready_status[username]
        conn.close()
        update_lobby()

# Send updated lobby info to all clients
def update_lobby():
    with lock:
        players = [{'name': c['username'], 'ready': ready_status.get(c['username'], False)} for c in clients]
        message = {'type': 'lobby', 'players': players}
        for client in clients:
            try:
                client['conn'].send(json.dumps(message).encode())
            except:
                pass

# Countdown + notify all clients to start the game
def start_game_with_countdown():
    for i in range(3, 0, -1):
        broadcast({'type': 'countdown', 'value': i})
        time.sleep(1)
    broadcast({'type': 'start'})

# Accept incoming client connections
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
#bag o