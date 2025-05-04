import tkinter as tk
import socket
import threading
import json
import random
import time
import queue
import pygame


# Server Code
def start_server():
    HOST = '127.0.0.1'
    PORT = 5555

    clients = []  # List of connected clients
    ready_status = {}  # Tracks whether each player is ready
    lock = threading.Lock()  # Thread safety for shared data

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
        try:
            data = conn.recv(1024)
            if not data:
                return
            msg = json.loads(data.decode())

            if msg['type'] == 'join':
                username = msg['username']
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

                    with lock:
                        if len(clients) == 2 and all(ready_status[c['username']] for c in clients):
                            threading.Thread(target=start_game_with_countdown, daemon=True).start()

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
            broadcast(message)

    def start_game_with_countdown():
        for i in range(3, 0, -1):
            broadcast({'type': 'countdown', 'value': i})
            time.sleep(1)
        broadcast({'type': 'start'})

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


# Client Code
class TetrisClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tetris")
        self.root.geometry("400x500")
        self.root.configure(bg="#222244")
        self.root.resizable(False, False)

        self.root.bind("<Key>", self.key_press)
        self.hold_piece = None
        self.can_hold = True

        self.username = None
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect(('127.0.0.1', 5555))

        self.send_queue = queue.Queue()
        self.is_solo = False
        self.last_board_send_time = 0

        self.FONT_NAME = "Trebuchet MS"
        self.FONT_TITLE = (self.FONT_NAME, 18, "bold")
        self.FONT_LABEL = (self.FONT_NAME, 12)
        self.FONT_BUTTON = (self.FONT_NAME, 10, "bold")

        self.show_login()

        threading.Thread(target=self.listen_server, daemon=True).start()
        threading.Thread(target=self.sender_thread, daemon=True).start()

        self.root.mainloop()

    def sender_thread(self):
        while True:
            msg = self.send_queue.get()
            try:
                self.conn.sendall(msg.encode())
            except Exception as e:
                print("Error sending:", e)

    def safe_send(self, msg_dict):
        self.send_queue.put(json.dumps(msg_dict))

    def show_login(self):
        self.clear_window()

        self.bg_canvas = tk.Canvas(self.root, width=400, height=500, bg="#222244", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)

        self.circles = []
        for _ in range(20):
            x = random.randint(0, 400)
            y = random.randint(0, 500)
            r = random.randint(10, 30)
            circle = self.bg_canvas.create_oval(x, y, x + r, y + r, fill="#444477", outline="")
            self.circles.append((circle, random.choice([-1, 1]), random.choice([-1, 1])))

        self.animate_background()

        login_frame = tk.Frame(self.bg_canvas, bg="#333366", padx=20, pady=20)
        login_window = self.bg_canvas.create_window(200, 250, window=login_frame)

        tk.Label(login_frame, text="Welcome to Tetris", font=self.FONT_TITLE, bg="#333366", fg="white").pack(pady=10)
        tk.Label(login_frame, text="Username:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(anchor="w")
        self.name_entry = tk.Entry(login_frame, font=self.FONT_LABEL)
        self.name_entry.pack(fill="x", pady=5)

        tk.Button(login_frame, text="Join", font=self.FONT_BUTTON, bg="#44aa88", fg="white",
                  command=self.join_lobby).pack(pady=10)

    def animate_background(self):
        for i, (circle, dx, dy) in enumerate(self.circles):
            self.bg_canvas.move(circle, dx, dy)
            coords = self.bg_canvas.coords(circle)
            if coords[0] <= 0 or coords[2] >= 400:
                dx = -dx
            if coords[1] <= 0 or coords[3] >= 500:
                dy = -dy
            self.circles[i] = (circle, dx, dy)
        self.root.after(50, self.animate_background)

    def join_lobby(self):
        username = self.name_entry.get()
        if username:
            self.username = username
            self.safe_send({"type": "join", "username": username})
            self.lobby_screen()

    def lobby_screen(self):
        self.clear_window()

        self.status_label = tk.Label(self.root, text="Waiting for players...", font=self.FONT_LABEL, bg="#222244",
                                     fg="white")
        self.status_label.pack(pady=10)

        self.players_frame = tk.Frame(self.root, bg="#444477")
        self.players_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.ready = False
        self.ready_button = tk.Button(self.root, text="Ready", font=self.FONT_BUTTON, bg="#44aa88", fg="white",
                                      command=self.toggle_ready)
        self.ready_button.pack(pady=5)

        self.start_now_button = tk.Button(self.root, text="Start Solo", font=self.FONT_BUTTON, bg="#88aaff", fg="white",
                                          command=self.force_start)
        self.start_now_button.pack(pady=5)

    def toggle_ready(self):
        self.ready = not self.ready
        self.safe_send({"type": "ready", "ready": self.ready})
        self.ready_button.config(
            text="Unready" if self.ready else "Ready",
            bg="#aa4444" if self.ready else "#44aa88"
        )

    def force_start(self):
        self.is_solo = True
        self.countdown_and_start()

    def countdown_and_start(self):
        def do_countdown(i):
            if i == 0:
                self.start_game()
                return
            self.show_countdown(i)
            self.root.after(1000, lambda: do_countdown(i - 1))

        do_countdown(3)

    def listen_server(self):
        while True:
            try:
                data = self.conn.recv(4096)
                if not data:
                    break
                msg = json.loads(data.decode())

                if msg['type'] == 'lobby':
                    self.root.after(0, self.update_lobby, msg['players'])

                elif msg['type'] == 'start':
                    self.is_solo = False
                    self.start_game()

                elif msg['type'] == 'score' and not self.is_solo:
                    if hasattr(self, 'opponent_score_label'):
                        self.opponent_score_label.config(text=f"Opponent Score: {msg['value']}")

                elif msg['type'] == 'board' and not self.is_solo:
                    if hasattr(self, 'opponent_canvas'):
                        self.draw_opponent_board(msg['board'])

                elif msg['type'] == 'countdown':
                    self.show_countdown(msg['value'])

            except Exception as e:
                print("Error in client listener:", e)
                break

    def show_countdown(self, value):
        countdown_label = tk.Label(self.root, text=str(value), font=("Trebuchet MS", 48), fg="white", bg="#222244")
        countdown_label.place(relx=0.5, rely=0.5, anchor="center")
        self.root.after(1000, countdown_label.destroy)

    def update_lobby(self, players):
        for widget in self.players_frame.winfo_children():
            widget.destroy()

        if not isinstance(players, list):
            return  # Make sure we have a list of players

        for player in players:
            if not isinstance(player, dict):
                continue  # Skip if not a dictionary

            # Safely get the username and ready status
            username = player.get('username') or player.get('name', 'Unknown')
            is_ready = player.get('ready', False)

            status = "Ready" if is_ready else "Not Ready"
            color = "green" if is_ready else "red"

            player_label = tk.Label(
                self.players_frame,
                text=f"{username}: {status}",
                font=self.FONT_LABEL,
                bg="#444477",
                fg=color
            )
            player_label.pack(pady=2, anchor="w")

    def start_game(self):
        pygame.mixer.init()
        try:
            pygame.mixer.music.load("tetrisa.mp3")
            pygame.mixer.music.play(-1)
        except:
            pass

        self.clear_window()
        if self.is_solo:
            self.root.geometry("700x650")
        else:
            self.root.geometry("1000x650")

        main_frame = tk.Frame(self.root)
        main_frame.pack()

        game_frame = tk.Frame(main_frame)
        game_frame.pack(side='left')

        self.canvas = tk.Canvas(game_frame, width=300, height=600, bg='black')
        self.canvas.pack(side='left', padx=10)

        if not self.is_solo:
            self.opponent_canvas = tk.Canvas(game_frame, width=300, height=600, bg='black')
            self.opponent_canvas.pack(side='left', padx=10)

        side_panel = tk.Frame(main_frame)
        side_panel.pack(side='left', padx=20)

        self.score_label = tk.Label(side_panel, text="Your Score: 0", font=self.FONT_LABEL)
        self.score_label.pack(pady=10)

        if not self.is_solo:
            self.opponent_score_label = tk.Label(side_panel, text="Opponent Score: 0", font=self.FONT_LABEL)
            self.opponent_score_label.pack(pady=10)

            tk.Label(side_panel, text="Opponent Next", font=self.FONT_LABEL).pack()
            self.opponent_next_canvas = tk.Canvas(side_panel, width=120, height=120, bg='lightgrey')
            self.opponent_next_canvas.pack(pady=10)

            tk.Label(side_panel, text="Opponent Hold", font=self.FONT_LABEL).pack()
            self.opponent_hold_canvas = tk.Canvas(side_panel, width=120, height=120, bg='lightgrey')
            self.opponent_hold_canvas.pack(pady=10)

        tk.Label(side_panel, text="Next Block", font=self.FONT_LABEL).pack()
        self.next_piece_canvas = tk.Canvas(side_panel, width=120, height=120, bg='grey')
        self.next_piece_canvas.pack(pady=10)

        tk.Label(side_panel, text="Hold Block", font=self.FONT_LABEL).pack()
        self.hold_piece_canvas = tk.Canvas(side_panel, width=120, height=120, bg='darkgrey')
        self.hold_piece_canvas.pack(pady=10)

        self.board = [[0] * 10 for _ in range(20)]
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.running = True
        self.can_hold = True

        self.root.bind("<Key>", self.key_press)
        self.game_loop()

    def new_piece(self):
        shapes = [
            [[1, 1, 1], [0, 1, 0]],
            [[1, 1, 1, 1]],
            [[1, 1], [1, 1]],
            [[0, 1, 1], [1, 1, 0]],
            [[1, 1, 0], [0, 1, 1]],
            [[1, 0, 0], [1, 1, 1]],
            [[0, 0, 1], [1, 1, 1]]
        ]
        shape = random.choice(shapes)
        return {'shape': shape, 'x': 5 - len(shape[0]) // 2, 'y': 0}

    def draw_hold_piece(self):
        self.hold_piece_canvas.delete("all")
        if not self.hold_piece:
            return
        shape = self.hold_piece['shape']
        tile_size = 15
        offset_x = (120 - len(shape[0]) * tile_size) // 2
        offset_y = (120 - len(shape) * tile_size) // 2
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    self.hold_piece_canvas.create_rectangle(
                        offset_x + x * tile_size,
                        offset_y + y * tile_size,
                        offset_x + (x + 1) * tile_size,
                        offset_y + (y + 1) * tile_size,
                        fill="cyan", outline="black"
                    )

    def hold_current_piece(self):
        if not self.can_hold:
            return
        self.can_hold = False
        if self.hold_piece is None:
            self.hold_piece = self.current_piece
            self.current_piece = self.next_piece
            self.next_piece = self.new_piece()
        else:
            self.hold_piece, self.current_piece = self.current_piece, self.hold_piece
            self.current_piece['x'] = 5 - len(self.current_piece['shape'][0]) // 2
            self.current_piece['y'] = 0
        self.draw_hold_piece()

    def draw_tile(self, canvas, x, y, color, tile_size=30):
        canvas.create_rectangle(
            x * tile_size, y * tile_size,
            (x + 1) * tile_size, (y + 1) * tile_size,
            fill=color, outline="gray"
        )

    def draw(self):
        self.canvas.delete("all")
        temp_board = self.get_temp_board_with_piece()
        for y in range(20):
            for x in range(10):
                if temp_board[y][x]:
                    self.draw_tile(self.canvas, x, y, "green")
        self.draw_next_piece()
        self.draw_hold_piece()

    def get_temp_board_with_piece(self):
        temp_board = [row[:] for row in self.board]
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    px = self.current_piece['x'] + x
                    py = self.current_piece['y'] + y
                    if 0 <= px < 10 and 0 <= py < 20:
                        temp_board[py][px] = 1
        return temp_board

    def draw_opponent_board(self, board):
        self.opponent_canvas.delete("all")
        for y in range(20):
            for x in range(10):
                if board[y][x]:
                    self.draw_tile(self.opponent_canvas, x, y, "red")

    def draw_next_piece(self):
        self.next_piece_canvas.delete("all")
        shape = self.next_piece['shape']
        tile_size = 15
        offset_x = (120 - len(shape[0]) * tile_size) // 2
        offset_y = (120 - len(shape) * tile_size) // 2
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    self.next_piece_canvas.create_rectangle(
                        offset_x + x * tile_size,
                        offset_y + y * tile_size,
                        offset_x + (x + 1) * tile_size,
                        offset_y + (y + 1) * tile_size,
                        fill="purple", outline="black"
                    )

    def move(self, dx, dy):
        self.current_piece['x'] += dx
        self.current_piece['y'] += dy
        if self.collision():
            self.current_piece['x'] -= dx
            self.current_piece['y'] -= dy
            return False
        return True

    def rotate(self):
        shape = self.current_piece['shape']
        rotated = list(zip(*shape[::-1]))
        rotated = [list(row) for row in rotated]
        old_shape = self.current_piece['shape']
        self.current_piece['shape'] = rotated
        if self.collision():
            self.current_piece['shape'] = old_shape

    def collision(self):
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    px = self.current_piece['x'] + x
                    py = self.current_piece['y'] + y
                    if px < 0 or px >= 10 or py >= 20 or (py >= 0 and self.board[py][px]):
                        return True
        return False

    def freeze(self):
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    px = self.current_piece['x'] + x
                    py = self.current_piece['y'] + y
                    if 0 <= py < 20:
                        self.board[py][px] = 1
        self.clear_lines()
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()
        self.can_hold = True
        if self.collision():
            self.running = False
            self.score_label.config(text="Game Over")

    def clear_lines(self):
        new_board = [row for row in self.board if any(val == 0 for val in row)]
        lines_cleared = 20 - len(new_board)
        self.score += lines_cleared * 100
        self.score_label.config(text=f"Your Score: {self.score}")
        self.safe_send({"type": "score", "value": self.score})
        for _ in range(lines_cleared):
            new_board.insert(0, [0] * 10)
        self.board = new_board

    def game_loop(self):
        if not self.running:
            return
        if not self.move(0, 1):
            self.freeze()
        self.draw()

        now = time.time()
        if not self.is_solo and now - self.last_board_send_time > 0.5:
            self.safe_send({"type": "board", "board": self.board})
            self.last_board_send_time = now

        self.root.after(500, self.game_loop)

    def key_press(self, event):
        if event.keysym == 'Left':
            self.move(-1, 0)
        elif event.keysym == 'Right':
            self.move(1, 0)
        elif event.keysym == 'Down':
            self.move(0, 1)
        elif event.keysym == 'Up':
            self.rotate()
        elif event.keysym in ['Shift_L', 'Shift_R']:
            self.hold_current_piece()
        self.draw()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()


# Main Execution
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        start_server()
    else:
        TetrisClient()