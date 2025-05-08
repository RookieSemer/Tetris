import socket
import threading
import json
import time


HOST = '127.0.0.1'
PORT = 5555

clients = []  # List of connected clients
ready_status = {}  # Tracks whether each player is ready
lock = threading.Lock()  # Thread safety for shared data
game_in_progress = False

def broadcast(message, sender_conn=None):
    with lock:
        for client in clients:
            conn = client['conn']
            if conn != sender_conn:
                try:
                    conn.send(json.dumps(message).encode())
                except:
                    pass

def handle_client(conn, addr):
    global clients, ready_status, game_in_progress
    username = None
    try:
        data = conn.recv(1024).decode()
        try:
            msg = json.loads(data)
            if msg["type"] == "join":
                username = msg["username"]
                with lock:
                    ready_status[username] = False
            else:
                print("Unexpected message type on join:", msg)
                return
        except json.JSONDecodeError:
            print("Failed to parse JSON from client:", data)
            return

        with lock:
            clients.append({'conn': conn, 'addr': addr, 'username': username})
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
                    ready_players = [c['username'] for c in clients if ready_status.get(c['username'], False)]
                    if len(ready_players) == 2 and not game_in_progress:
                        game_in_progress = True
                        threading.Thread(target=start_game_with_countdown, daemon=True).start()

            elif msg['type'] == 'solo_start':
                with lock:
                    game_in_progress = True
                # Only send start message to the solo player
                try:
                    conn.send(json.dumps({'type': 'start', 'is_solo': True}).encode())
                except:
                    pass

            elif msg['type'] == 'score':
                broadcast({'type': 'score', 'value': msg['value']}, sender_conn=conn)

            elif msg['type'] == 'board':
                broadcast({'type': 'board', 'board': msg['board']}, sender_conn=conn)

            elif msg['type'] == 'next_piece':

                with lock:
                    opponent = next((c for c in clients if c['conn'] != conn), None)
                    if opponent:
                        try:
                            opponent['conn'].send(json.dumps({
                                'type': 'opponent_next',
                                'piece': msg['piece']
                            }).encode())
                        except:
                            pass

            elif msg['type'] == 'hold_piece':
                # Broadcast the player's hold piece to opponent
                with lock:
                    opponent = next((c for c in clients if c['conn'] != conn), None)
                    if opponent:
                        try:
                            opponent['conn'].send(json.dumps({
                                'type': 'opponent_hold',
                                'piece': msg['piece']
                            }).encode())
                        except:
                            pass
            elif msg['type'] == 'initial_pieces':
                with lock:
                    # Update this client's piece information
                    for client in clients:
                        if client['conn'] == conn:
                            client['next_piece'] = msg.get('next_piece')
                            client['hold_piece'] = msg.get('hold_piece')
                            break

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        with lock:
            clients[:] = [c for c in clients if c['conn'] != conn]
            if username in ready_status:
                del ready_status[username]
            game_in_progress = False
            # Notify remaining players that game is cancelled
            if len(clients) > 0:
                broadcast({'type': 'game_cancelled'})
        conn.close()
        update_lobby()


def update_lobby():
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

        for client in clients:
            try:
                client['conn'].send(json.dumps(message).encode())
            except:
                pass


def start_game_with_countdown():
    global game_in_progress
    try:
        for i in range(3, 0, -1):
            broadcast({'type': 'countdown', 'value': i})
            time.sleep(1)

        # After countdown, exchange initial pieces
        with lock:
            if len(clients) == 2:
                client1, client2 = clients[0], clients[1]

                # Send each client their opponent's initial pieces
                try:
                    client1['conn'].send(json.dumps({
                        'type': 'start',
                        'is_solo': False,
                        'opponent_next': client2.get('next_piece'),
                        'opponent_hold': client2.get('hold_piece')
                    }).encode())

                    client2['conn'].send(json.dumps({
                        'type': 'start',
                        'is_solo': False,
                        'opponent_next': client1.get('next_piece'),
                        'opponent_hold': client1.get('hold_piece')
                    }).encode())
                except:
                    pass
    except:
        pass
    finally:
        game_in_progress = False

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