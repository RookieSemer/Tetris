import tkinter as tk
import socket
import threading
import json
import random
import time
import queue
import pygame

HOST = '127.0.0.1'
PORT = 5555

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
        self.start_game()

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

            except Exception as e:
                print("Error in client listener:", e)
                break

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

        game_frame = tk.Frame(self.root)
        game_frame.pack()

        self.canvas = tk.Canvas(game_frame, width=COLUMNS*TILE_SIZE, height=ROWS*TILE_SIZE, bg='black')
        self.canvas.pack(side='left')

        if not self.is_solo:
            self.opponent_canvas = tk.Canvas(game_frame, width=COLUMNS*TILE_SIZE, height=ROWS*TILE_SIZE, bg='black')
            self.opponent_canvas.pack(side='left', padx=10)

        info_frame = tk.Frame(self.root)
        info_frame.pack()

        self.score_label = tk.Label(info_frame, text="Your Score: 0")
        self.score_label.pack(side='left', padx=10)

        if not self.is_solo:
            self.opponent_score_label = tk.Label(info_frame, text="Opponent Score: 0")
            self.opponent_score_label.pack(side='left', padx=10)

        self.next_piece_canvas = tk.Canvas(self.root, width=6*TILE_SIZE, height=6*TILE_SIZE, bg='grey')
        self.next_piece_canvas.pack(pady=10)

        self.board = [[0]*COLUMNS for _ in range(ROWS)]
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.running = True

        self.root.bind("<Key>", self.key_press)
        self.game_loop()

    def new_piece(self):
        shape = random.choice(SHAPES)
        return {'shape': shape, 'x': COLUMNS // 2 - len(shape[0]) // 2, 'y': 0}

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
        self.draw_next_piece()
        if self.collision():
            self.running = False
            self.score_label.config(text="Game Over")

    def clear_lines(self):
        new_board = [row for row in self.board if any(val == 0 for val in row)]
        lines_cleared = ROWS - len(new_board)
        self.score += lines_cleared * 100
        self.score_label.config(text=f"Your Score: {self.score}")
        if not self.is_solo:
            self.safe_send({"type": "score", "value": self.score})
        for _ in range(lines_cleared):
            new_board.insert(0, [0]*COLUMNS)
        self.board = new_board

    def get_temp_board_with_piece(self):
        temp = [row.copy() for row in self.board]
        if self.current_piece:
            for y, row in enumerate(self.current_piece['shape']):
                for x, val in enumerate(row):
                    if val:
                        px = self.current_piece['x'] + x
                        py = self.current_piece['y'] + y
                        if 0 <= px < COLUMNS and 0 <= py < ROWS:
                            temp[py][px] = 1
        return temp

    def send_board(self):
        now = time.time()
        if now - self.last_board_send_time > 0.5:
            temp_board = self.get_temp_board_with_piece()
            self.safe_send({"type": "board", "board": temp_board})
            self.last_board_send_time = now

    def game_loop(self):
        if not self.running:
            return
        if not self.move(0, 1):
            self.freeze()
        self.draw()
        if not self.is_solo:
            self.send_board()
        self.root.after(500, self.game_loop)

    def key_press(self, event):
        if not self.running:
            return
        if event.keysym == 'Left':
            self.move(-1, 0)
        elif event.keysym == 'Right':
            self.move(1, 0)
        elif event.keysym == 'Down':
            self.move(0, 1)
        elif event.keysym == 'Up':
            self.rotate()
        self.draw()
        if not self.is_solo:
            self.send_board()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    TetrisClient()
