import tkinter as tk
import socket
import threading
import json
import random
import time
import queue
import pygame

# Networking
HOST = '127.0.0.1'
PORT = 5555

# Tetris Constants
TILE_SIZE = 30
COLUMNS = 10
ROWS = 20

SHAPES = [
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 1, 1]],          # I
    [[1, 1], [1, 1]],        # O
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]],  # Z
    [[1, 0, 0], [1, 1, 1]],  # L
    [[0, 0, 1], [1, 1, 1]]   # J
]

class TetrisClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tetris Login")
        self.root.geometry("400x500")
        self.root.configure(bg="#222244")
        self.root.resizable(False, False)

        self.root.bind("<Key>", self.key_press)
        self.hold_piece = None
        self.can_hold = True

        self.username = None
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((HOST, PORT))

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
            circle = self.bg_canvas.create_oval(x, y, x+r, y+r, fill="#444477", outline="")
            self.circles.append((circle, random.choice([-1, 1]), random.choice([-1, 1])))

        self.animate_background()

        login_frame = tk.Frame(self.bg_canvas, bg="#333366", padx=20, pady=20)
        login_window = self.bg_canvas.create_window(200, 250, window=login_frame)

        tk.Label(login_frame, text="Login", font=self.FONT_TITLE, bg="#333366", fg="white").pack(pady=10)
        tk.Label(login_frame, text="Username:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(anchor="w")
        self.name_entry = tk.Entry(login_frame, font=self.FONT_LABEL)
        self.name_entry.pack(fill="x", pady=5)

        tk.Button(login_frame, text="Login", font=self.FONT_BUTTON, bg="#44aa88", fg="white", command=self.join_lobby).pack(pady=10)

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
            self.conn.send(self.username.encode())
            self.lobby_screen()

    def lobby_screen(self):
        self.clear_window()

        self.status_label = tk.Label(self.root, text="Waiting for players...", font=self.FONT_LABEL, bg="#222244", fg="white")
        self.status_label.pack(pady=10)
        self.players_frame = tk.Frame(self.root, bg="#444477")
        self.players_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.ready = False
        self.ready_button = tk.Button(self.root, text="Ready", font=self.FONT_BUTTON, bg="#44aa88", fg="white", command=self.toggle_ready)
        self.ready_button.pack(pady=5)

        self.start_now_button = tk.Button(self.root, text="Start Solo", font=self.FONT_BUTTON, bg="#88aaff", fg="white", command=self.force_start)
        self.start_now_button.pack(pady=5)

    def toggle_ready(self):
        self.ready = not self.ready
        self.safe_send({"type": "ready", "ready": self.ready})
        self.ready_button.config(text="Unready" if self.ready else "Ready")

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

                if msg['type'] == 'lobby' and hasattr(self, 'players_frame') and self.players_frame.winfo_exists():
                    self.update_lobby(msg['players'])

                elif msg['type'] == 'start':
                    self.is_solo = False
                    self.start_game()

                elif msg['type'] == 'score' and not self.is_solo:
                    if hasattr(self, 'opponent_score_label') and self.opponent_score_label.winfo_exists():
                        self.opponent_score_label.config(text=f"Opponent Score: {msg['value']}")

                elif msg['type'] == 'board' and not self.is_solo:
                    if hasattr(self, 'opponent_canvas') and self.opponent_canvas.winfo_exists():
                        self.draw_opponent_board(msg['board'])

                elif msg['type'] == 'countdown':  # Added
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
        for player in players:
            text = f"{player['name']} - {'Ready' if player['ready'] else 'Not Ready'}"
            tk.Label(self.players_frame, text=text, font=self.FONT_LABEL, bg="#444477", fg="white").pack(pady=2, anchor="w")

    def start_game(self):
        pygame.mixer.init()
        pygame.mixer.music.load("tetrisa.mp3")
        pygame.mixer.music.play(-1)

        self.clear_window()
        self.root.geometry("700x650")

        main_frame = tk.Frame(self.root)
        main_frame.pack()

        game_frame = tk.Frame(main_frame)
        game_frame.pack(side='left')

        self.canvas = tk.Canvas(game_frame, width=COLUMNS * TILE_SIZE, height=ROWS * TILE_SIZE, bg='black')
        self.canvas.pack()

        if not self.is_solo:
            self.opponent_canvas = tk.Canvas(game_frame, width=COLUMNS * TILE_SIZE, height=ROWS * TILE_SIZE, bg='black')
            self.opponent_canvas.pack(side='left', padx=10)

        side_panel = tk.Frame(main_frame)
        side_panel.pack(side='left', padx=20)

        self.score_label = tk.Label(side_panel, text="Your Score: 0")
        self.score_label.pack(pady=10)

        if not self.is_solo:
            self.opponent_score_label = tk.Label(side_panel, text="Opponent Score: 0")
            self.opponent_score_label.pack(pady=10)

        # ✅ Next piece canvas
        tk.Label(side_panel, text="Next Block", font=self.FONT_LABEL).pack()
        self.next_piece_canvas = tk.Canvas(side_panel, width=6 * TILE_SIZE, height=6 * TILE_SIZE, bg='grey')
        self.next_piece_canvas.pack(pady=10)

        # ➕ Hold piece canvas
        tk.Label(side_panel, text="Hold Block", font=self.FONT_LABEL).pack()
        self.hold_piece_canvas = tk.Canvas(side_panel, width=6 * TILE_SIZE, height=6 * TILE_SIZE, bg='darkgrey')
        self.hold_piece_canvas.pack(pady=10)

        self.board = [[0] * COLUMNS for _ in range(ROWS)]
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.running = True
        self.can_hold = True  # ➕ Reset on game start

        self.root.bind("<Key>", self.key_press)
        self.game_loop()

    def new_piece(self):
        shape = random.choice(SHAPES)
        return {'shape': shape, 'x': COLUMNS // 2 - len(shape[0]) // 2, 'y': 0}

    def draw_hold_piece(self):
        self.hold_piece_canvas.delete("all")
        if not self.hold_piece:
            return
        shape = self.hold_piece['shape']
        tile_size = TILE_SIZE // 2
        offset_x = (6 * TILE_SIZE - len(shape[0]) * tile_size) // 2
        offset_y = (6 * TILE_SIZE - len(shape) * tile_size) // 2
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
            self.current_piece['x'] = COLUMNS // 2 - len(self.current_piece['shape'][0]) // 2
            self.current_piece['y'] = 0
        self.draw_hold_piece()

    def draw(self):
        self.canvas.delete("all")
        temp_board = self.get_temp_board_with_piece()
        for y in range(ROWS):
            for x in range(COLUMNS):
                if temp_board[y][x]:
                    self.draw_tile(self.canvas, x, y, "green")
        self.draw_next_piece()
        self.draw_hold_piece()  # ➕ Draw hold piece

    def draw_tile(self, canvas, x, y, color, tile_size=TILE_SIZE):
        canvas.create_rectangle(
            x*tile_size, y*tile_size,
            (x+1)*tile_size, (y+1)*tile_size,
            fill=color, outline="gray"
        )

    def draw(self):
        self.canvas.delete("all")
        temp_board = self.get_temp_board_with_piece()
        for y in range(ROWS):
            for x in range(COLUMNS):
                if temp_board[y][x]:
                    self.draw_tile(self.canvas, x, y, "green")
        self.draw_next_piece()

    def get_temp_board_with_piece(self):
        temp_board = [row[:] for row in self.board]
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    px = self.current_piece['x'] + x
                    py = self.current_piece['y'] + y
                    if 0 <= px < COLUMNS and 0 <= py < ROWS:
                        temp_board[py][px] = 1
        return temp_board

    def draw_opponent_board(self, board):
        self.opponent_canvas.delete("all")
        for y in range(ROWS):
            for x in range(COLUMNS):
                if board[y][x]:
                    self.draw_tile(self.opponent_canvas, x, y, "red")

    def draw_next_piece(self):
        self.next_piece_canvas.delete("all")
        shape = self.next_piece['shape']
        tile_size = TILE_SIZE // 2
        offset_x = (6 * TILE_SIZE - len(shape[0]) * tile_size) // 2
        offset_y = (6 * TILE_SIZE - len(shape) * tile_size) // 2
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    self.next_piece_canvas.create_rectangle(
                        offset_x + x*tile_size,
                        offset_y + y*tile_size,
                        offset_x + (x+1)*tile_size,
                        offset_y + (y+1)*tile_size,
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
                    if px < 0 or px >= COLUMNS or py >= ROWS or (py >= 0 and self.board[py][px]):
                        return True
        return False

    def freeze(self):
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    px = self.current_piece['x'] + x
                    py = self.current_piece['y'] + y
                    if 0 <= py < ROWS:
                        self.board[py][px] = 1
        self.clear_lines()
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()
        self.can_hold = True  # ➕ Allow holding again
        if self.collision():
            self.running = False
            self.score_label.config(text="Game Over")

    def clear_lines(self):
        new_board = [row for row in self.board if any(val == 0 for val in row)]
        lines_cleared = ROWS - len(new_board)
        self.score += lines_cleared * 100
        self.score_label.config(text=f"Your Score: {self.score}")
        self.safe_send({"type": "score", "value": self.score})
        for _ in range(lines_cleared):
            new_board.insert(0, [0]*COLUMNS)
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
        elif event.keysym in ['Shift_L', 'Shift_R']:  # ➕ Hold on Shift
            self.hold_current_piece()
        self.draw()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    TetrisClient()
