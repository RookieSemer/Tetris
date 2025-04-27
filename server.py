import socket
import threading
import json

HOST = '127.0.0.1'
PORT = 5555

clients = []
ready_status = {}
lock = threading.Lock()

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
    global clients, ready_status
    try:
        username = conn.recv(1024).decode()
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

            elif msg['type'] == 'score':
                broadcast({'type': 'score', 'value': msg['value']}, sender_conn=conn)

            elif msg['type'] == 'board':
                # 🔥 Corrected part here: also send the moving piece
                broadcast({
                    'type': 'board',
                    'board': msg['board'],
                    'piece': msg['piece']
                }, sender_conn=conn)

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        with lock:
            clients[:] = [c for c in clients if c['conn'] != conn]
            if username in ready_status:
                del ready_status[username]
        conn.close()
        update_lobby()

def update_lobby():
    with lock:
        players = [{'name': c['username'], 'ready': ready_status.get(c['username'], False)} for c in clients]
        message = {'type': 'lobby', 'players': players}
        for client in clients:
            try:
                client['conn'].send(json.dumps(message).encode())
            except:
                pass

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