import tkinter as tk
import socket
import threading
import json
import random

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
        self.root.title("Tetris Lobby")

        self.username = None
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((HOST, PORT))

        self.lobby_ui()
        threading.Thread(target=self.listen_server, daemon=True).start()
        self.root.mainloop()

    def lobby_ui(self):
        self.clear_window()

        tk.Label(self.root, text="Enter your name:").pack()
        self.name_entry = tk.Entry(self.root)
        self.name_entry.pack()

        tk.Button(self.root, text="Join Lobby", command=self.join_lobby).pack()

    def join_lobby(self):
        self.username = self.name_entry.get()
        if self.username:
            self.conn.send(self.username.encode())
            self.lobby_screen()

    def lobby_screen(self):
        self.clear_window()

        self.status_label = tk.Label(self.root, text="Waiting for players...")
        self.status_label.pack()

        self.players_frame = tk.Frame(self.root)
        self.players_frame.pack()

        self.ready = False
        self.ready_button = tk.Button(self.root, text="Ready", command=self.toggle_ready)
        self.ready_button.pack()

    def toggle_ready(self):
        self.ready = not self.ready
        msg = {"type": "ready", "ready": self.ready}
        self.conn.send(json.dumps(msg).encode())
        self.ready_button.config(text="Unready" if self.ready else "Ready")

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
                    self.start_game()

                elif msg['type'] == 'score':
                    if hasattr(self, 'opponent_score_label') and self.opponent_score_label.winfo_exists():
                        self.opponent_score_label.config(text=f"Opponent Score: {msg['value']}")

                elif msg['type'] == 'board':
                    if hasattr(self, 'opponent_canvas') and self.opponent_canvas.winfo_exists():
                        self.draw_board(self.opponent_canvas, msg['board'])

            except Exception as e:
                print("Error in client listener:", e)
                break

    def update_lobby(self, players):
        for widget in self.players_frame.winfo_children():
            widget.destroy()
        for player in players:
            text = f"{player['name']} - {'Ready' if player['ready'] else 'Not Ready'}"
            tk.Label(self.players_frame, text=text).pack()

    def start_game(self):
        self.clear_window()

        # Game UI
        game_frame = tk.Frame(self.root)
        game_frame.pack()

        self.canvas = tk.Canvas(game_frame, width=COLUMNS*TILE_SIZE, height=ROWS*TILE_SIZE, bg='black')
        self.canvas.pack(side='left')

        self.opponent_canvas = tk.Canvas(game_frame, width=COLUMNS*TILE_SIZE, height=ROWS*TILE_SIZE, bg='black')
        self.opponent_canvas.pack(side='left', padx=10)

        info_frame = tk.Frame(self.root)
        info_frame.pack()

        self.score_label = tk.Label(info_frame, text="Your Score: 0")
        self.score_label.pack(side='left', padx=10)

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

    def draw_tile(self, canvas, x, y, color):
        canvas.create_rectangle(
            x*TILE_SIZE, y*TILE_SIZE,
            (x+1)*TILE_SIZE, (y+1)*TILE_SIZE,
            fill=color, outline="gray"
        )

    def draw_board(self, canvas, board):
        canvas.delete("all")
        for y in range(ROWS):
            for x in range(COLUMNS):
                if board[y][x]:
                    self.draw_tile(canvas, x, y, "blue")

    def draw(self):
        self.canvas.delete("all")

        # Draw frozen blocks
        for y in range(ROWS):
            for x in range(COLUMNS):
                if self.board[y][x]:
                    self.draw_tile(self.canvas, x, y, "blue")

        # Draw current moving piece
        for y, row in enumerate(self.current_piece['shape']):
            for x, val in enumerate(row):
                if val:
                    self.draw_tile(
                        self.canvas,
                        self.current_piece['x'] + x,
                        self.current_piece['y'] + y,
                        "green"
                    )

        # Draw next piece preview
        self.draw_next_piece()

    def draw_next_piece(self):
        self.next_piece_canvas.delete("all")
        shape = self.next_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    self.next_piece_canvas.create_rectangle(
                        x*TILE_SIZE, y*TILE_SIZE,
                        (x+1)*TILE_SIZE, (y+1)*TILE_SIZE,
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
        if self.collision():
            self.running = False
            self.score_label.config(text="Game Over")

    def clear_lines(self):
        new_board = [row for row in self.board if any(val == 0 for val in row)]
        lines_cleared = ROWS - len(new_board)
        self.score += lines_cleared * 100
        self.score_label.config(text=f"Your Score: {self.score}")
        self.conn.send(json.dumps({"type": "score", "value": self.score}).encode())
        for _ in range(lines_cleared):
            new_board.insert(0, [0]*COLUMNS)
        self.board = new_board

    def game_loop(self):
        if not self.running:
            return
        if not self.move(0, 1):
            self.freeze()
        self.draw()

        # Send current board to opponent
        self.conn.send(json.dumps({"type": "board", "board": self.board}).encode())

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
        self.draw()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    TetrisClient()
