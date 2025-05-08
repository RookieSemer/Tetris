import tkinter as tk
import socket
import threading
import json
import random
import time
import queue
import pygame
import os
from tkinter import messagebox


class TetrisClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tetris")
        self.root.geometry("400x500")
        self.root.configure(bg="#222244")
        self.root.resizable(False, False)

        # Initialize all game attributes
        self.canvas = None
        self.opponent_canvas = None
        self.score_label = None
        self.opponent_score_label = None
        self.next_piece_canvas = None
        self.hold_piece_canvas = None
        self.opponent_next_canvas = None
        self.opponent_hold_canvas = None
        self.players_frame = None
        self.ready_button = None
        self.start_now_button = None
        self.status_label = None
        self.bg_canvas = None
        self.high_score_label = None
        self.high_scores_button = None
        self.high_scores_window = None

        self.hold_piece = None
        self.can_hold = True
        self.username = None
        self.password = None
        self.conn = None
        self.send_queue = queue.Queue()
        self.is_solo = False
        self.last_board_send_time = 0
        self.running = False
        self.board = []
        self.current_piece = None
        self.next_piece = None
        self.score = 0
        self.server_ip = '127.0.0.1'
        self.server_port = 5555
        self.high_scores = {}

        self.FONT_NAME = "Trebuchet MS"
        self.FONT_TITLE = (self.FONT_NAME, 18, "bold")
        self.FONT_LABEL = (self.FONT_NAME, 12)
        self.FONT_BUTTON = (self.FONT_NAME, 10, "bold")

        # Create files if they don't exist
        if not os.path.exists('users.txt'):
            with open('users.txt', 'w') as f:
                pass
        if not os.path.exists('highscores.txt'):
            with open('highscores.txt', 'w') as f:
                pass
        else:
            self.load_high_scores()

        self.show_login_screen()
        self.connect_to_server()

        self.root.mainloop()

    def load_high_scores(self):
        try:
            with open('highscores.txt', 'r') as f:
                for line in f:
                    parts = line.strip().split(':')
                    if len(parts) == 2:
                        username, score = parts
                        self.high_scores[username] = int(score)
        except:
            pass

    def save_high_score(self):
        if self.username and self.score > self.high_scores.get(self.username, 0):
            self.high_scores[self.username] = self.score
            with open('highscores.txt', 'w') as f:
                for username, score in self.high_scores.items():
                    f.write(f"{username}:{score}\n")

    def show_high_scores(self):
        self.high_scores_window = tk.Toplevel(self.root)
        self.high_scores_window.title("High Scores")
        self.high_scores_window.geometry("300x400")
        self.high_scores_window.configure(bg="#222244")

        tk.Label(self.high_scores_window, text="High Scores", font=self.FONT_TITLE, bg="#222244", fg="white").pack(
            pady=10)

        scores_frame = tk.Frame(self.high_scores_window, bg="#333366")
        scores_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Sort high scores in descending order
        sorted_scores = sorted(self.high_scores.items(), key=lambda x: x[1], reverse=True)

        for i, (username, score) in enumerate(sorted_scores[:10]):  # Show top 10
            tk.Label(scores_frame,
                     text=f"{i + 1}. {username}: {score}",
                     font=self.FONT_LABEL,
                     bg="#333366",
                     fg="white").pack(pady=2, anchor="w")

    def connect_to_server(self):
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((self.server_ip, self.server_port))
            threading.Thread(target=self.listen_server, daemon=True).start()
            threading.Thread(target=self.sender_thread, daemon=True).start()
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            return False

    def sender_thread(self):
        while True:
            msg = self.send_queue.get()
            try:
                if self.conn:
                    self.conn.sendall(msg.encode())
            except Exception as e:
                print("Error sending:", e)

    def safe_send(self, msg_dict):
        self.send_queue.put(json.dumps(msg_dict))

    def show_login_screen(self):
        self.clear_window()

        self.bg_canvas = tk.Canvas(self.root, width=400, height=500, bg="#222244", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)

        login_frame = tk.Frame(self.root, bg="#333366", padx=20, pady=20)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(login_frame, text="Tetris Login", font=self.FONT_TITLE, bg="#333366", fg="white").pack(pady=10)

        tk.Label(login_frame, text="Username:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(anchor="w")
        self.login_user_entry = tk.Entry(login_frame, font=self.FONT_LABEL)
        self.login_user_entry.pack(fill="x", pady=5)

        tk.Label(login_frame, text="Password:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(anchor="w")
        self.login_pass_entry = tk.Entry(login_frame, font=self.FONT_LABEL, show="*")
        self.login_pass_entry.pack(fill="x", pady=5)

        tk.Button(login_frame, text="Login", font=self.FONT_BUTTON, bg="#44aa88", fg="white",
                  command=self.attempt_login).pack(pady=10, fill='x')
        tk.Button(login_frame, text="Register", font=self.FONT_BUTTON, bg="#88aaff", fg="white",
                  command=self.show_register_screen).pack(pady=5, fill='x')

    def show_register_screen(self):
        self.clear_window()

        register_frame = tk.Frame(self.root, bg="#333366", padx=20, pady=20)
        register_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(register_frame, text="Register Account", font=self.FONT_TITLE, bg="#333366", fg="white").pack(pady=10)

        tk.Label(register_frame, text="Username:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(anchor="w")
        self.reg_user_entry = tk.Entry(register_frame, font=self.FONT_LABEL)
        self.reg_user_entry.pack(fill="x", pady=5)

        tk.Label(register_frame, text="Password:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(anchor="w")
        self.reg_pass_entry = tk.Entry(register_frame, font=self.FONT_LABEL, show="*")
        self.reg_pass_entry.pack(fill="x", pady=5)

        tk.Label(register_frame, text="Confirm Password:", font=self.FONT_LABEL, bg="#333366", fg="white").pack(
            anchor="w")
        self.reg_confirm_entry = tk.Entry(register_frame, font=self.FONT_LABEL, show="*")
        self.reg_confirm_entry.pack(fill="x", pady=5)

        tk.Button(register_frame, text="Register", font=self.FONT_BUTTON, bg="#44aa88", fg="white",
                  command=self.attempt_register).pack(pady=10, fill='x')
        tk.Button(register_frame, text="Back to Login", font=self.FONT_BUTTON, bg="#aa4444", fg="white",
                  command=self.show_login_screen).pack(pady=5, fill='x')

    def attempt_login(self):
        username = self.login_user_entry.get()
        password = self.login_pass_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Username and password are required")
            return

        # Check credentials in the text file
        with open('users.txt', 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) == 2:
                    stored_user, stored_pass = parts
                    if stored_user == username and stored_pass == password:
                        self.username = username
                        self.password = password
                        self.safe_send({"type": "join", "username": username})
                        self.lobby_screen()
                        return

        messagebox.showerror("Error", "Invalid username or password")

    def attempt_register(self):
        username = self.reg_user_entry.get()
        password = self.reg_pass_entry.get()
        confirm = self.reg_confirm_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Username and password are required")
            return

        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return

        # Check if username already exists
        with open('users.txt', 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) > 0 and parts[0] == username:
                    messagebox.showerror("Error", "Username already exists")
                    return

        # Add new user
        with open('users.txt', 'a') as f:
            f.write(f"{username}:{password}\n")

        messagebox.showinfo("Success", "Registration successful!")
        self.show_login_screen()

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

        self.high_scores_button = tk.Button(self.root, text="High Scores", font=self.FONT_BUTTON, bg="#aa88ff",
                                            fg="white",
                                            command=self.show_high_scores)
        self.high_scores_button.pack(pady=5)

    def toggle_ready(self):
        self.ready = not self.ready
        self.safe_send({"type": "ready", "ready": self.ready})
        self.ready_button.config(
            text="Unready" if self.ready else "Ready",
            bg="#aa4444" if self.ready else "#44aa88"
        )

    def force_start(self):
        self.is_solo = True
        self.ready = True  # Mark as ready for solo mode
        self.countdown_and_start()

    def countdown_and_start(self):
        def do_countdown(i):
            if not self.is_solo and not self.ready:  # Check if cancelled
                return
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

                    self.is_solo = msg.get('is_solo', False)
                    if not self.is_solo:

                        if 'opponent_next' in msg:
                            self.opponent_next_piece = msg['opponent_next']

                        if 'opponent_hold' in msg:
                            self.opponent_hold_piece = msg['opponent_hold']
                            self.root.after(0, self.start_game)

                elif msg['type'] == 'score' and not self.is_solo:
                    if self.opponent_score_label:
                        self.opponent_score_label.config(text=f"Opponent Score: {msg['value']}")

                elif msg['type'] == 'board' and not self.is_solo:
                    if self.opponent_canvas:
                        self.draw_opponent_board(msg['board'])

                elif msg['type'] == 'countdown':
                    self.root.after(0, self.show_countdown, msg['value'])

                elif msg['type'] == 'game_cancelled':
                    self.root.after(0, self.cancel_countdown)
                    self.root.after(0, self.status_label.config, {"text": "Game cancelled - other player left"})

                elif msg['type'] == 'opponent_next':
                    self.opponent_next_piece = msg['piece']
                    self.draw_opponent_next_piece()

                elif msg['type'] == 'opponent_hold':
                    self.opponent_hold_piece = msg['piece']
                    self.draw_opponent_hold_piece()


            except Exception as e:
                print("Error in client listener:", e)
                break

    def show_countdown(self, value):
        if hasattr(self, 'countdown_label'):
            self.countdown_label.destroy()
        self.countdown_label = tk.Label(self.root, text=str(value), font=("Trebuchet MS", 48), fg="white", bg="#222244")
        self.countdown_label.place(relx=0.5, rely=0.5, anchor="center")
        self.root.after(1000, self.countdown_label.destroy)

    def cancel_countdown(self):
        if hasattr(self, 'countdown_label'):
            self.countdown_label.destroy()
        self.status_label.config(text="Countdown cancelled")

    def update_lobby(self, players):
        if not self.players_frame:
            return

        # Clear the frame first
        for widget in self.players_frame.winfo_children():
            widget.destroy()

        # Add a title label
        title_label = tk.Label(
            self.players_frame,
            text="Players in Lobby:",
            font=self.FONT_LABEL,
            bg="#444477",
            fg="white"
        )
        title_label.pack(pady=5, anchor="w")

        # Add each player with their status
        for player in players:
            username = player.get('name', 'Unknown')
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

        # Update status label based on number of players
        if len(players) == 1:
            self.status_label.config(text="Waiting for another player...")
        elif len(players) >= 2:
            self.status_label.config(text=f"{len(players)} players in lobby - ready up!")

    def start_game(self):
        self.clear_window()

        pygame.mixer.init()
        pygame.mixer.music.load("tetrisa.wav")
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play(-1)

        # Set window size based on game mode
        if self.is_solo:
            self.root.geometry("700x650")  # Smaller window for solo
        else:
            self.root.geometry("1200x650")  # Wider window for multiplayer

        main_frame = tk.Frame(self.root)
        main_frame.pack()

        # Left panel for player's info
        left_panel = tk.Frame(main_frame, width=200)
        left_panel.pack(side='left', padx=10)

        # Player's score
        self.score_label = tk.Label(left_panel, text="Your Score: 0", font=self.FONT_LABEL)
        self.score_label.pack(pady=10)

        # Player's next piece
        player_next_frame = tk.Frame(left_panel)
        player_next_frame.pack(pady=10)
        tk.Label(player_next_frame, text="Your Next Block", font=self.FONT_LABEL).pack()
        self.next_piece_canvas = tk.Canvas(player_next_frame, width=120, height=120, bg='grey')
        self.next_piece_canvas.pack()

        # Player's hold piece
        player_hold_frame = tk.Frame(left_panel)
        player_hold_frame.pack(pady=10)
        tk.Label(player_hold_frame, text="Your Hold Block", font=self.FONT_LABEL).pack()
        self.hold_piece_canvas = tk.Canvas(player_hold_frame, width=120, height=120, bg='darkgrey')
        self.hold_piece_canvas.pack()

        # Game boards in the middle
        game_frame = tk.Frame(main_frame)
        game_frame.pack(side='left')

        # Player's game board
        self.canvas = tk.Canvas(game_frame, width=300, height=600, bg='black')
        self.canvas.pack(side='left', padx=10)

        # Opponent's game board (only in multiplayer)
        if not self.is_solo:
            self.opponent_canvas = tk.Canvas(game_frame, width=300, height=600, bg='black')
            self.opponent_canvas.pack(side='left', padx=10)

        # Right panel for opponent's info (only in multiplayer)
        right_panel = tk.Frame(main_frame, width=200)
        right_panel.pack(side='left', padx=10)

        if not self.is_solo:
            # Opponent's score
            self.opponent_score_label = tk.Label(right_panel, text="Opponent Score: 0", font=self.FONT_LABEL)
            self.opponent_score_label.pack(pady=10)

            # Opponent's next piece
            opp_next_frame = tk.Frame(right_panel)
            opp_next_frame.pack(pady=10)
            tk.Label(opp_next_frame, text="Opponent Next Block", font=self.FONT_LABEL).pack()
            self.opponent_next_canvas = tk.Canvas(opp_next_frame, width=120, height=120, bg='lightgrey')
            self.opponent_next_canvas.pack()

            # Opponent's hold piece
            opp_hold_frame = tk.Frame(right_panel)
            opp_hold_frame.pack(pady=10)
            tk.Label(opp_hold_frame, text="Opponent Hold Block", font=self.FONT_LABEL).pack()
            self.opponent_hold_canvas = tk.Canvas(opp_hold_frame, width=120, height=120, bg='lightgrey')
            self.opponent_hold_canvas.pack()

        # Initialize game state
        self.board = [[0] * 10 for _ in range(20)]
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.running = True
        self.can_hold = True

        # Initialize opponent state (for multiplayer)
        self.opponent_board = [[0] * 10 for _ in range(20)]
        self.opponent_next_piece = None
        self.opponent_hold_piece = None

        if not self.is_solo:
            self.safe_send({
                'type': 'initial_pieces',
                'next_piece': self.next_piece,
                'hold_piece': self.hold_piece
            })

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
        if self.hold_piece_canvas:
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
            self.next_piece = self.new_piece()  # Generate new next piece
        else:
            self.hold_piece, self.current_piece = self.current_piece, self.hold_piece
            self.current_piece['x'] = 5 - len(self.current_piece['shape'][0]) // 2
            self.current_piece['y'] = 0

        # Send updates to opponent
        if not self.is_solo:
            self.safe_send({
                'type': 'hold_piece',
                'piece': self.hold_piece
            })
            self.safe_send({
                'type': 'next_piece',
                'piece': self.next_piece
            })

        self.draw_hold_piece()

    def draw_tile(self, canvas, x, y, color, tile_size=30):
        if canvas:
            canvas.create_rectangle(
                x * tile_size, y * tile_size,
                (x + 1) * tile_size, (y + 1) * tile_size,
                fill=color, outline="gray"
            )

    def draw(self):
        if self.canvas:
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
        if self.opponent_canvas:
            self.opponent_canvas.delete("all")
            for y in range(20):
                for x in range(10):
                    if board[y][x]:
                        self.draw_tile(self.opponent_canvas, x, y, "red")

    def draw_next_piece(self):
        if self.next_piece_canvas:
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

    def draw_opponent_next_piece(self):
        if self.opponent_next_canvas and hasattr(self, 'opponent_next_piece') and self.opponent_next_piece:
            self.opponent_next_canvas.delete("all")
            shape = self.opponent_next_piece['shape']
            tile_size = 15
            offset_x = (120 - len(shape[0]) * tile_size) // 2
            offset_y = (120 - len(shape) * tile_size) // 2
            for y, row in enumerate(shape):
                for x, val in enumerate(row):
                    if val:
                        self.opponent_next_canvas.create_rectangle(
                            offset_x + x * tile_size,
                            offset_y + y * tile_size,
                            offset_x + (x + 1) * tile_size,
                            offset_y + (y + 1) * tile_size,
                            fill="red", outline="black"
                        )

    def draw_opponent_hold_piece(self):
        if self.opponent_hold_canvas and hasattr(self, 'opponent_hold_piece') and self.opponent_hold_piece:
            self.opponent_hold_canvas.delete("all")
            shape = self.opponent_hold_piece['shape']
            tile_size = 15
            offset_x = (120 - len(shape[0]) * tile_size) // 2
            offset_y = (120 - len(shape) * tile_size) // 2
            for y, row in enumerate(shape):
                for x, val in enumerate(row):
                    if val:
                        self.opponent_hold_canvas.create_rectangle(
                            offset_x + x * tile_size,
                            offset_y + y * tile_size,
                            offset_x + (x + 1) * tile_size,
                            offset_y + (y + 1) * tile_size,
                            fill="red", outline="black"
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

        if not self.is_solo:
            self.safe_send({
                'type': 'next_piece',
                'piece': self.next_piece
            })

        if self.collision():
            self.running = False
            if self.score_label:
                self.score_label.config(text="Game Over")
            self.save_high_score()
            self.root.after(3000, self.lobby_screen)

    def clear_lines(self):
        new_board = [row for row in self.board if any(val == 0 for val in row)]
        lines_cleared = 20 - len(new_board)
        self.score += lines_cleared * 100
        if self.score_label:
            self.score_label.config(text=f"Your Score: {self.score}")

        # Only send score updates in multiplayer mode
        if not self.is_solo:
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

        # Only send board updates in multiplayer mode
        now = time.time()
        if not self.is_solo and now - self.last_board_send_time > 0.5:
            self.safe_send({"type": "board", "board": self.board})
            self.last_board_send_time = now

        self.root.after(500, self.game_loop)

    def key_press(self, event):
        if not self.running or not self.canvas:
            return

        if event.keysym in ['a', 'Left']:
            self.move(-1, 0)
        elif event.keysym in ['d', 'Right']:
            self.move(1, 0)
        elif event.keysym in ['s', 'Down']:
            self.move(0, 1)
        elif event.keysym in ['w', 'Up']:
            self.rotate()
        elif event.keysym in ['Shift_L', 'Shift_R']:
            self.hold_current_piece()
        self.draw()

    def clear_window(self):
        # Stop any music playing
        try:
            pygame.mixer.music.stop()
        except:
            pass

        # Unbind keys to prevent ghost inputs
        try:
            self.root.unbind("<Key>")
        except:
            pass

        # Destroy all widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        # Reset critical game attributes
        self.canvas = None
        self.opponent_canvas = None
        self.score_label = None
        self.opponent_score_label = None
        self.next_piece_canvas = None
        self.hold_piece_canvas = None
        self.opponent_next_canvas = None
        self.opponent_hold_canvas = None
        self.players_frame = None
        self.ready_button = None
        self.start_now_button = None
        self.status_label = None
        self.bg_canvas = None
        self.running = False


if __name__ == "__main__":
    TetrisClient()