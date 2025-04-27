import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox

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

                if len(clients) == 2 and all(ready_status[c['username']] for c in clients):
                    start_game()

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

def update_lobby():
    with lock:
        players = [{'name': c['username'], 'ready': ready_status.get(c['username'], False)} for c in clients]
        message = {'type': 'lobby', 'players': players}
        for client in clients:
            try:
                client['conn'].send(json.dumps(message).encode())
            except:
                pass

def start_game():
    message = {'type': 'start'}
    for client in clients:
        try:
            client['conn'].send(json.dumps(message).encode())
        except:
            pass

def start_server():
    def server_thread():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen()
        update_status(f"Server listening on {HOST}:{PORT}")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    threading.Thread(target=server_thread, daemon=True).start()

def update_status(msg):
    status_label.config(text=msg)

# Create GUI
root = tk.Tk()
root.title("Multiplayer Server")

start_button = tk.Button(root, text="Start Server", command=start_server)
start_button.pack(pady=10)

status_label = tk.Label(root, text="Server not running", fg="gray")
status_label.pack(pady=5)

root.mainloop()