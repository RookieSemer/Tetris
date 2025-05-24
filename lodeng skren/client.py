import tkinter as tk
import socket
import json
import random
import time
import queue
import pygame
import os
from tkinter import messagebox
from PIL import Image, ImageTk
from tkinter import ttk
pygame.mixer.init()
from tkinter import simpledialog
import threading


def simulate_loading(progressbar, loading_window, root, on_finish):
    def update(i):
        if not progressbar.winfo_exists() or not loading_window.winfo_exists():
            return
        progressbar["value"] = i
        if i < 100:
            loading_window.after(20, update, i + 1)
        else:
            loading_window.destroy()
            on_finish()
    loading_window.after(0, update, 0)

def start_loading(root, on_finish):
    loading_window = tk.Toplevel(root)
    loading_window.geometry("600x400")
    loading_window.title("Game Loading")
    loading_window.resizable(False, False)

    # Load and place background image
    try:
        from PIL import Image, ImageTk
        bg_image = Image.open("tetris bg.jpg").resize((600, 400))
        bg_photo = ImageTk.PhotoImage(bg_image)
        bg_label = tk.Label(loading_window, image=bg_photo)
        bg_label.image = bg_photo
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    except Exception:
        loading_window.configure(bg="#222244")

    label = tk.Label(loading_window, text="Loading Game...", font=("Helvetica", 20, "bold"), bg="#000000", fg="white")
    label.pack(pady=30)

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Custom.Horizontal.TProgressbar",
                    troughcolor='#333',
                    background='#44DD44',
                    thickness=20,
                    bordercolor='#222')

    progressbar = ttk.Progressbar(loading_window, orient="horizontal", length=400, mode="determinate",
                                  style="Custom.Horizontal.TProgressbar")
    progressbar.pack(pady=40)

    threading.Thread(target=simulate_loading, args=(progressbar, loading_window, root, on_finish), daemon=True).start()
# --- End Loading Screen Functions ---



class ChatNode:
    def __init__(self, username, message):
        self.username = username
        self.message = message
        self.next = None

class ChatLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, username, message):
        node = ChatNode(username, message)
        if not self.head:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node

    def to_list(self):
        result = []
        current = self.head
        while current:
            result.append((current.username, current.message))
            current = current.next
        return result


class BSTNode:
    def __init__(self, username, score):
        self.username = username
        self.score = score
        self.left = None
        self.right = None

class LeaderboardBST:
    def __init__(self):
        self.root = None

    def insert(self, username, score):
        def _insert(node, username, score):
            if not node:
                return BSTNode(username, score)
            if username < node.username:
                node.left = _insert(node.left, username, score)
            elif username > node.username:
                node.right = _insert(node.right, username, score)
            else:
                node.score = max(node.score, score)
            return node
        self.root = _insert(self.root, username, score)

    def search(self, username):
        def _search(node, username):
            if not node:
                return None
            if username == node.username:
                return node.score
            elif username < node.username:
                return _search(node.left, username)
            else:
                return _search(node.right, username)
        return _search(self.root, username)

    def in_order(self):
        result = []
        def _in_order(node):
            if node:
                _in_order(node.left)
                result.append((node.username, node.score))
                _in_order(node.right)
        _in_order(self.root)
        return result

class TetrisClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tetris")
        self.root.geometry("700x700")
        self.root.withdraw()
        self.root.configure(bg="#222244")
        self.root.resizable(False, False)
        self.place_sound = pygame.mixer.Sound("put.mp3")
        self.hard_drop_sound = pygame.mixer.Sound("hard.mp3")
        self.opponent_current_block = None
        self.opponent_hold_block = None
        self.leaderboard = LeaderboardBST()
        self.single_leaderboard = LeaderboardBST()
        self.multi_leaderboard = LeaderboardBST()
        self.single_file = 'highscores_single.txt'
        self.multi_file = 'highscores_multi.txt'
        self.load_high_scores()
        self.chat_log_list = ChatLinkedList()
        self.in_game = False
        self.FONT_NAME = "Trebuchet MS"
        self.FONT_NORMAL = (self.FONT_NAME, 12)
        self.piece_shapes = {
            # ... your piece shapes ...
        }
        self.next_queue = []
        self.opponent_next_queue = []
        self.hold_stack = []
        # Initialize all game attributes
        self.canvas = None
        self.opponent_canvas = None
        self.score_label = None
        self.opponent_score_label = None
        self.next_piece_canvas = None
        self.hold_piece_canvas = None
        self.latest_opponent_piece = None
        self.latest_opponent_board = None
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
        self.network_update_interval = 0.1  # 100ms
        self.network_thread = threading.Thread(target=self.network_update_loop, daemon=True)
        self.network_thread.start()

        self.FONT_NAME = "Trebuchet MS"
        self.FONT_TITLE = (self.FONT_NAME, 18, "bold")
        self.FONT_LABEL = (self.FONT_NAME, 12)
        self.FONT_BUTTON = (self.FONT_NAME, 10, "bold")
        self.FONT_TEXT = "pixel_emulator"

        # Create files if they don't exist
        if not os.path.exists('users.txt'):
            with open('users.txt', 'w') as f:
                pass
        if not os.path.exists('highscores.txt'):
            with open('highscores.txt', 'w') as f:
                pass

        def after_loading():
            self.root.deiconify()
            self.show_login_screen()

        start_loading(self.root, after_loading)

        self.root.mainloop()

    def load_high_scores(self):
        for file, board in [(self.single_file, self.single_leaderboard), (self.multi_file, self.multi_leaderboard)]:
            try:
                with open(file, 'r') as f:
                    for line in f:
                        username, score = line.strip().split(':')
                        board.insert(username, int(score))
            except:
                pass

    def save_high_score(self):
        if self.username:
            board = self.single_leaderboard if self.is_solo else self.multi_leaderboard
            file = self.single_file if self.is_solo else self.multi_file
            prev_score = board.search(self.username)
            if prev_score is None or self.score > prev_score:
                board.insert(self.username, self.score)
                with open(file, 'w') as f:
                    for username, score in board.in_order():
                        f.write(f"{username}:{score}\n")

    def show_high_scores(self):
        if self.high_scores_window and self.high_scores_window.winfo_exists():
            self.high_scores_window.lift()
            return

        self.high_scores_window = tk.Toplevel(self.root)
        self.high_scores_window.title("High Scores")
        self.high_scores_window.geometry("500x700")
        self.high_scores_window.configure(bg="#222244")

        btn_frame = tk.Frame(self.high_scores_window, bg="#222244")
        btn_frame.pack(pady=10)

        leaderboard_frame = tk.Frame(self.high_scores_window, bg="#222244")
        leaderboard_frame.pack(fill="both", expand=True)

        def show_single():
            for widget in leaderboard_frame.winfo_children():
                widget.destroy()
            tk.Label(leaderboard_frame, text="Singleplayer LeaderBoard", font=self.FONT_TITLE, bg="#222244",
                     fg="white").pack(pady=10)
            self._show_leaderboard(self.single_leaderboard, leaderboard_frame)

        def show_multi():
            for widget in leaderboard_frame.winfo_children():
                widget.destroy()
            tk.Label(leaderboard_frame, text="Multiplayer LeaderBoard", font=self.FONT_TITLE, bg="#222244",
                     fg="white").pack(pady=10)
            self._show_leaderboard(self.multi_leaderboard, leaderboard_frame)

        tk.Button(btn_frame, text="Singleplayer", font=self.FONT_BUTTON, bg="#44aa88", fg="white", width=16,
                  command=show_single).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Multiplayer", font=self.FONT_BUTTON, bg="#0077cc", fg="white", width=16,
                  command=show_multi).pack(side="left", padx=10)

        show_single()  # Show singleplayer by default

    def _show_leaderboard(self, board, parent):
        scores_frame = tk.Frame(parent, bg="#333366")
        scores_frame.pack(pady=5, padx=20, fill="both", expand=False)
        sorted_scores = sorted(board.in_order(), key=lambda x: x[1], reverse=True)[:20]
        for i, (username, score) in enumerate(sorted_scores):
            tk.Label(scores_frame, text=f"{i + 1}. {username}: {score}", font=self.FONT_LABEL, bg="#333366",
                     fg="orange").pack(anchor="w")

    def search_player_highscore(self, username):
        score = self.leaderboard.search(username)
        if score is not None:
            messagebox.showinfo("Player Highscore", f"{username}'s highscore: {score}")
        else:
            messagebox.showinfo("Player Highscore", f"No highscore found for {username}")

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
        self.send_queue.put(json.dumps(msg_dict) + "\n")

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

        with open('users.txt', 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) == 2:
                    stored_user, stored_pass = parts
                    if stored_user == username and stored_pass == password:
                        self.username = username
                        self.password = password
                        # Connect to server here
                        if not self.connect_to_server():
                            return
                        self.safe_send({"type": "join", "username": username})
                        self.show_lobby_menu()
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

    def show_lobby_menu(self):
        self.clear_window()
        main_frame = tk.Frame(self.root, bg="#222244")
        main_frame.pack(fill="both", expand=True)

        # Left panel (actions)
        left_frame = tk.Frame(main_frame, padx=10, pady=10, bg="#222244")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_frame, text="Create Game", font=self.FONT_LABEL, bg="#89CFF0").pack(pady=5)
        tk.Button(left_frame, text="Create", font=self.FONT_BUTTON, bg="orange", fg="white", width=16,
                  command=self.create_lobby_dialog).pack(pady=5)

        tk.Label(left_frame, text="Join Game", font=self.FONT_LABEL, bg="#89CFF0").pack(pady=10)
        tk.Button(left_frame, text="Join Selected", font=self.FONT_BUTTON, bg="orange", fg="white", width=16,
                  command=self.join_selected_lobby).pack(pady=5)

        tk.Button(left_frame, text="Exit", font=self.FONT_BUTTON, width=16, command=self.root.destroy,
                  bg="orange", fg="white").pack(pady=20)

        tk.Button(left_frame, text="High Scores", font=self.FONT_BUTTON, bg="#44aa88", fg="white", width=16,
                  command=self.show_high_scores).pack(pady=5)

        # Add Start Solo button here
        tk.Button(left_frame, text="Start Solo", font=self.FONT_BUTTON, bg="#0077cc", fg="white", width=16,
                  command=self.force_start).pack(pady=5)

        tk.Button(
            left_frame, text="Matchmaking", font=self.FONT_BUTTON, bg="#ff8800", fg="white", width=16,
            command=self.matchmaking
        ).pack(pady=5)

        # Right panel (lobby list)
        right_frame = tk.Frame(main_frame, padx=10, pady=10, bg="#003153")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(right_frame, text="Available Lobbies", font=self.FONT_LABEL, bg="#003153", fg="white").pack()
        self.lobby_listbox = tk.Listbox(right_frame, font=self.FONT_LABEL, width=40, height=10, bg="#003153",
                                        fg="orange")
        self.lobby_listbox.pack(pady=10)

        tk.Button(right_frame, text="Refresh", font=self.FONT_BUTTON, bg="orange", fg="white",
                  command=lambda: self.safe_send({'type': 'list_lobbies'})).pack()

        self.safe_send({'type': 'list_lobbies'})

    def create_lobby_dialog(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Lobby Name", "Enter lobby name:")
        if name:
            max_players = simpledialog.askinteger("Max Players", "Enter max players (1 or 2):", minvalue=1, maxvalue=2)
            if max_players:
                self.safe_send({'type': 'create_lobby', 'lobby_name': name, 'max_players': max_players})

    def join_selected_lobby(self):
        selection = self.lobby_listbox.curselection()
        if selection:
            idx = selection[0]
            lobby_id = self.lobby_id_map.get(idx)
            if lobby_id:
                self.safe_send({'type': 'join_lobby', 'lobby_id': lobby_id})

        def refresh_lobbies():
            self.safe_send({'type': 'list_lobbies'})

        def create_lobby():
            name = simpledialog.askstring("Lobby Name", "Enter lobby name:")
            if name:
                max_players = simpledialog.askinteger("Max Players", "Enter max players (1 or 2):", minvalue=1,
                                                      maxvalue=2)
                if max_players:
                    self.safe_send({'type': 'create_lobby', 'lobby_name': name, 'max_players': max_players})

    def matchmaking(self):
        def handle_lobbies(lobbies):
            for lobby in lobbies:
                if (
                        lobby.get('name') == 'Matchmaking'
                        and lobby['players'] < lobby['max_players']
                ):
                    if not hasattr(self, 'current_lobby_id') or self.current_lobby_id != lobby['id']:
                        self.safe_send({'type': 'join_lobby', 'lobby_id': lobby['id']})
                    return
            # No available matchmaking lobby, create one and wait for server response
            self.safe_send({'type': 'create_lobby', 'lobby_name': 'Matchmaking', 'max_players': 2, 'hidden': True})
            # Do NOT send another list_lobbies here

        def on_lobby_list(msg):
            if msg['type'] == 'lobby_list':
                handle_lobbies(msg['lobbies'])
                self.matchmaking_waiting = False

        self.matchmaking_waiting = True
        orig_handle_message = self.handle_message

        def temp_handle_message(msg):
            if self.matchmaking_waiting and msg['type'] == 'lobby_list':
                on_lobby_list(msg)
            else:
                orig_handle_message(msg)

        self.handle_message = temp_handle_message
        self.safe_send({'type': 'list_lobbies', 'for_matchmaking': True})

    # In your network/message handler, add:
    def handle_message(self, msg):
        if msg['type'] == 'lobby_list':
            self.update_lobby_list(msg['lobbies'])

        elif msg['type'] == 'lobby_created':
            self.current_lobby_id = msg['lobby_id']
            self.lobby_screen()
            self.safe_send({'type': 'list_lobbies'})

        elif msg['type'] == 'lobby_joined':
            self.current_lobby_id = msg['lobby_id']
            self.lobby_screen()
            self.safe_send({'type': 'list_lobbies'})

        elif msg['type'] == 'opponent_active_piece':
            self.latest_opponent_piece = msg['piece']
            self.latest_opponent_board = msg['board']
            # Optionally, trigger a redraw here if needed
            self.root.after(0, self.draw)

        elif msg['type'] == 'game_result':
            if msg['result'] == 'win':
                self.show_game_over_overlay("You Win!")
            else:
                self.show_game_over_overlay("You Lose!")

    def lobby_screen(self):

        self.clear_window()

        # Lobby Title
        tk.Label(self.root, text="Game Lobby", font=(self.FONT_TEXT, 20, "bold"),
                 bg="#222244", fg="orange").pack(pady=(20, 10))

        # Status Label
        self.status_label = tk.Label(self.root, text="Waiting for players...", font=self.FONT_LABEL,
                                     bg="#003153", fg="white", pady=10)
        self.status_label.pack(pady=5, fill="x", padx=20)

        # Players List Frame
        players_frame_border = tk.LabelFrame(self.root, text="Players", font=self.FONT_LABEL,
                                             bg="#005577", fg="white", bd=2, relief="ridge", padx=10, pady=10)
        players_frame_border.pack(padx=20, pady=10, fill="both", expand=True)

        self.players_frame = tk.Frame(players_frame_border, bg="#004466")
        self.players_frame.pack(fill="both", expand=True)

        # Buttons Frame
        buttons_frame = tk.Frame(self.root, bg="#222244")
        buttons_frame.pack(pady=10)

        # Ready Button
        self.ready = False
        self.ready_button = tk.Button(buttons_frame, text="Ready", font=self.FONT_BUTTON,
                                      bg="#ff8800", fg="white", width=15, height=2, command=self.toggle_ready)
        self.ready_button.grid(row=0, column=0, padx=10, pady=5)

        self.leave_button = tk.Button(
            buttons_frame, text="Leave Lobby", font=self.FONT_BUTTON,
            bg="#aa4444", fg="white", width=15, height=2, command=self.leave_lobby
        )
        self.leave_button.grid(row=0, column=1, padx=10, pady=5)

        chat_frame = tk.Frame(self.root, bg="#222244")
        chat_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 10))

        self.chat_log = tk.Text(chat_frame, height=8, state="disabled", bg="#111133", fg="white", font=self.FONT_LABEL)
        self.chat_log.pack(fill="x", pady=2)

        chat_entry_frame = tk.Frame(chat_frame, bg="#222244")
        chat_entry_frame.pack(fill="x")
        self.chat_entry = tk.Entry(chat_entry_frame, font=self.FONT_LABEL)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(chat_entry_frame, text="Send", font=self.FONT_BUTTON, bg="#44aa88", fg="white",
                  command=self.send_chat_message).pack(side="left")

        self.chat_entry.bind("<Return>", lambda e: self.send_chat_message())

    def update_lobby_list(self, lobbies):
        if not hasattr(self, 'lobby_listbox') or not self.lobby_listbox.winfo_exists():
            return  # Listbox was destroyed, ignore update
        self.lobby_id_map = {}
        self.lobby_listbox.delete(0, tk.END)
        for idx, lobby in enumerate(lobbies):
            name = lobby['name']
            players = lobby['players']
            max_players = lobby['max_players']
            self.lobby_listbox.insert(tk.END, f"{name} ({players}/{max_players})")
            self.lobby_id_map[idx] = lobby['id']

    def leave_lobby(self):
        if hasattr(self, 'current_lobby_id'):
            self.safe_send({'type': 'leave_lobby', 'lobby_id': self.current_lobby_id})
            self.current_lobby_id = None
            self.show_lobby_menu()

    def toggle_ready(self):
        if self.in_game:
            messagebox.showinfo("Info", "Finish your current game before readying up.")
            return
        # Only send the opposite of current ready state; do not update self.ready or the button here!
        self.safe_send({"type": "ready", "ready": not self.ready})

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
        buffer = ""
        while True:
            try:
                data = self.conn.recv(4096)
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
                        print("Error parsing server message:", e, line)
                        continue

                    # Handle some messages inline
                    if msg['type'] == 'lobby':
                        self.root.after(0, self.update_lobby, msg['players'])
                    elif msg['type'] == 'start':
                        self.is_solo = msg.get('is_solo', False)
                        self.root.after(0, self.start_game)
                    elif msg['type'] == 'error':
                        if 'User already online' in msg.get('message', ''):
                            messagebox.showerror("Login Error", "This user is already online.")
                            self.conn.close()
                            self.show_login_screen()

                    elif msg['type'] == 'score' and not self.is_solo:
                        if self.opponent_score_label:
                            self.opponent_score_label.config(text=f"Opponent Score: {msg['value']}")
                    elif msg['type'] == 'board' and not self.is_solo:
                        if self.opponent_canvas:
                            self.draw_opponent_board(msg['board'])
                    elif msg['type'] == 'chat':
                        self.root.after(0, self.add_chat_message, msg['username'], msg['message'])
                    elif msg['type'] == 'countdown':
                        self.root.after(0, self.show_countdown, msg['value'])
                    elif msg['type'] == 'opponent_block_update':
                        self.opponent_next_queue = msg.get('next_queue', [])
                        self.opponent_hold_block = msg.get('hold_block')
                        self.root.after(0, self.draw_opponent_pieces)
                    elif msg['type'] == 'game_cancelled':
                        self.root.after(0, self.cancel_countdown)
                        self.root.after(0, self.status_label.config, {"text": "Game cancelled - other player left"})


                    else:
                        # Pass all other messages to handle_message
                        self.root.after(0, self.handle_message, msg)

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

            # Update your own ready button based on server state
            if username == self.username and self.ready_button:
                self.ready = is_ready
                self.ready_button.config(
                    text="Unready" if is_ready else "Ready",
                    bg="#aa4444" if is_ready else "#44aa88"
                )

        # Update status label based on number of players
        if len(players) == 1:
            self.status_label.config(text="Waiting for another player...")
        elif len(players) >= 2:
            self.status_label.config(text=f"{len(players)} players in lobby - ready up!")

    def send_chat_message(self):
        msg = self.chat_entry.get().strip()
        if msg:
            self.safe_send({"type": "chat", "message": msg})
            self.chat_entry.delete(0, "end")

    def add_chat_message(self, username, message):
        self.chat_log_list.append(username, message)
        self.chat_log.config(state="normal")
        self.chat_log.delete("1.0", "end")
        for user, msg in self.chat_log_list.to_list():
            self.chat_log.insert("end", f"{user}: {msg}\n")
        self.chat_log.see("end")
        self.chat_log.config(state="disabled")

    def start_game(self):
        canvas_width = 300
        canvas_height = 600
        gap = 32
        preview_size = 120
        side_panel_width = 260 if not self.is_solo else 160

        if self.is_solo:
            total_width = canvas_width + gap + 260 + 120
            game_frame_width = canvas_width + gap
        else:
            total_width = side_panel_width * 2 + canvas_width * 2 + gap * 6
            game_frame_width = canvas_width * 2 + gap

        self.root.geometry(f"{total_width}x{canvas_height + 140}")
        self.root.minsize(total_width, canvas_height + 140)
        self.root.update_idletasks()
        self.clear_window()
        pygame.mixer.init()
        pygame.mixer.music.load("tetrisa.wav")
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)

        main_frame = tk.Frame(self.root, bg="#001122")
        main_frame.pack(fill="both", expand=True)

        # --- Left panel (player info) ---
        if not self.is_solo:
            left_panel = tk.Frame(main_frame, width=side_panel_width, bg="#002244")
            left_panel.pack(side='left', fill="y", padx=(gap, 0), pady=48)

            self.score_label = tk.Label(left_panel, text="Your Score: 0", font=self.FONT_LABEL, bg="#002244",
                                        fg="orange")
            self.score_label.pack(pady=10)

            player_pieces_frame = tk.Frame(left_panel, bg="#002244")
            player_pieces_frame.pack(pady=20)

            # --- 3-block next queue for player ---
            self.next_piece_canvases = []
            next_queue_frame = tk.Frame(player_pieces_frame, bg="#002244")
            next_queue_frame.pack(side='left', padx=5)
            tk.Label(next_queue_frame, text="Next", font=self.FONT_TEXT, bg="#002244", fg="white").pack()
            for _ in range(3):
                c = tk.Canvas(next_queue_frame, width=preview_size, height=preview_size, bg="#223355",
                              highlightthickness=2, highlightbackground="#00ADEF")
                c.pack(pady=2)
                self.next_piece_canvases.append(c)

            hold_frame = tk.Frame(player_pieces_frame, bg="#002244", width=preview_size + 10, height=preview_size + 30)
            hold_frame.pack(side='left', padx=5)
            hold_frame.pack_propagate(False)
            tk.Label(hold_frame, text="Hold", font=self.FONT_TEXT, bg="#002244", fg="white").pack(pady=5)
            self.hold_piece_canvas = tk.Canvas(hold_frame, width=preview_size, height=preview_size, bg="#334466",
                                               highlightthickness=2, highlightbackground="#FF8800")
            self.hold_piece_canvas.pack()

        # --- Center game frame ---
        game_frame = tk.Frame(main_frame, bg="#001122", width=game_frame_width, height=canvas_height)
        game_frame.pack_propagate(False)
        game_frame.pack(side='left', fill="y", padx=(gap, gap), pady=48)
        self.game_frame = game_frame

        self.canvas = tk.Canvas(game_frame, width=canvas_width, height=canvas_height, bg="#111133",
                                highlightthickness=2, highlightbackground="#00ADEF")
        self.canvas.pack(side='left', padx=(0, gap // 2))

        if not self.is_solo:
            self.opponent_canvas = tk.Canvas(game_frame, width=canvas_width, height=canvas_height, bg="#111133",
                                             highlightthickness=2, highlightbackground="#FF8800")
            self.opponent_canvas.pack(side='left', padx=(gap // 2, 0))

        # --- Right panel (opponent info) ---
        if self.is_solo:
            side_panel = tk.Frame(main_frame, width=260, bg="#002244")
            side_panel.pack(side='right', fill="y", padx=(10, 48), pady=48)

            self.score_label = tk.Label(side_panel, text="Your Score: 0", font=self.FONT_LABEL, bg="#002244",
                                        fg="orange")
            self.score_label.pack(pady=10)

            player_pieces_frame = tk.Frame(side_panel, bg="#002244")
            player_pieces_frame.pack(pady=20)

            # --- 3-block next queue for solo (optional, or keep single) ---
            self.next_piece_canvases = []
            next_queue_frame = tk.Frame(player_pieces_frame, bg="#002244")
            next_queue_frame.pack(side='left', padx=5)
            tk.Label(next_queue_frame, text="Next", font=self.FONT_TEXT, bg="#002244", fg="white").pack()
            for _ in range(3):
                c = tk.Canvas(next_queue_frame, width=preview_size, height=preview_size, bg="#223355",
                              highlightthickness=2, highlightbackground="#00ADEF")
                c.pack(pady=2)
                self.next_piece_canvases.append(c)

            hold_frame = tk.Frame(player_pieces_frame, bg="#002244", width=preview_size + 10, height=preview_size + 30)
            hold_frame.pack(side='left', padx=5)
            hold_frame.pack_propagate(False)
            tk.Label(hold_frame, text="Hold", font=self.FONT_TEXT, bg="#002244", fg="white").pack(pady=5)
            self.hold_piece_canvas = tk.Canvas(hold_frame, width=preview_size, height=preview_size, bg="#334466",
                                               highlightthickness=2, highlightbackground="#FF8800")
            self.hold_piece_canvas.pack()

        if not self.is_solo:
            right_panel = tk.Frame(main_frame, width=side_panel_width, bg="#002244")
            right_panel.pack(side='left', fill="y", padx=(0, gap), pady=48)

            self.opponent_score_label = tk.Label(right_panel, text="Opponent Score: 0", font=self.FONT_TEXT,
                                                 bg="#002244", fg="#00ADEF")
            self.opponent_score_label.pack(pady=10)

            opponent_pieces_frame = tk.Frame(right_panel, bg="#002244")
            opponent_pieces_frame.pack(pady=20)

            # --- 3-block next queue for opponent ---
            self.opponent_next_canvases = []
            opp_next_queue_frame = tk.Frame(opponent_pieces_frame, bg="#002244")
            opp_next_queue_frame.pack(side='left', padx=5)
            tk.Label(opp_next_queue_frame, text="Opp Next", font=self.FONT_LABEL, bg="#002244", fg="white").pack()
            for _ in range(3):
                c = tk.Canvas(opp_next_queue_frame, width=preview_size, height=preview_size, bg="#223355",
                              highlightthickness=2, highlightbackground="#00ADEF")
                c.pack(pady=2)
                self.opponent_next_canvases.append(c)

            opp_hold_frame = tk.Frame(opponent_pieces_frame, bg="#002244", width=preview_size + 10,
                                      height=preview_size + 30)
            opp_hold_frame.pack(side='left', padx=5)
            opp_hold_frame.pack_propagate(False)
            tk.Label(opp_hold_frame, text="Opp Hold", font=self.FONT_LABEL, bg="#002244", fg="white").pack()
            self.opponent_hold_canvas = tk.Canvas(
                opp_hold_frame, width=preview_size, height=preview_size, bg="#334466",
                highlightthickness=2, highlightbackground="#FF8800"
            )
            self.opponent_hold_canvas.pack()

        # --- Game state initialization ---
        self.board = [[0] * 10 for _ in range(20)]
        self.init_next_queue()
        self.current_piece = self.pop_next_piece()
        self.score = 0
        self.running = True
        self.can_hold = True

        self.root.bind("<Key>", self.key_press)
        self.game_loop()

    def init_next_queue(self):
        self.next_queue = [self.new_piece() for _ in range(3)]

    def pop_next_piece(self):
        piece = self.next_queue.pop(0)
        self.next_queue.append(self.new_piece())
        return piece

    def shake_canvas(self, shakes=1, distance=10, delay=30):
        canvases = [self.canvas]
        if not self.is_solo and self.opponent_canvas:
            canvases.append(self.opponent_canvas)
        orig_positions = []
        for c in canvases:
            c.update_idletasks()
            orig_positions.append((c.winfo_x(), c.winfo_y()))

        def do_shake(n):
            if n == 0:
                for i, c in enumerate(canvases):
                    c.place_forget()
                    c.pack(side='left', padx=(0, 16) if i == 0 else (16, 0))
                self.root.update_idletasks()
                return
            for i, c in enumerate(canvases):
                x, y = orig_positions[i]
                c.place(x=x, y=y + distance)
            self.root.update_idletasks()
            self.root.after(delay, lambda: reset_shake())

        def reset_shake():
            for i, c in enumerate(canvases):
                if c.winfo_exists():
                    x, y = orig_positions[i]
                    c.place(x=x, y=y)
            self.root.update_idletasks()
            self.root.after(delay, lambda: do_shake(0))

        for i, c in enumerate(canvases):
            x, y = orig_positions[i]
            c.place(x=x, y=y)
        do_shake(shakes)


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
            if not self.hold_stack:
                return
            self._draw_block_on_canvas(self.hold_piece_canvas, self.hold_stack[-1]['shape'], fill="cyan")

    def hold_current_piece(self):
        if not self.can_hold:
            return
        self.can_hold = False
        # Push current piece onto the stack
        self.hold_stack.append(self.current_piece)
        # Pop last held piece if available, else get next piece
        if len(self.hold_stack) > 1:
            self.current_piece = self.hold_stack.pop(-2)
            self.current_piece['x'] = 5 - len(self.current_piece['shape'][0]) // 2
            self.current_piece['y'] = 0
        else:
            self.current_piece = self.pop_next_piece()
        self.draw_hold_piece()

    def draw_tile(self, canvas, x, y, color, tile_size=32):
        # Enhanced block: rounded corners, border, and shadow
        if canvas:
            # Shadow
            canvas.create_rectangle(
                x * tile_size + 2, y * tile_size + 2,
                (x + 1) * tile_size + 2, (y + 1) * tile_size + 2,
                fill="#222222", outline=""
            )
            # Main block with border and rounded corners
            canvas.create_rectangle(
                x * tile_size, y * tile_size,
                (x + 1) * tile_size, (y + 1) * tile_size,
                fill=color, outline="#444444", width=2
            )
            # Optional: highlight for a "3D" effect
            canvas.create_line(
                x * tile_size, y * tile_size,
                (x + 1) * tile_size, y * tile_size,
                fill="white", width=2
            )
            canvas.create_line(
                x * tile_size, y * tile_size,
                x * tile_size, (y + 1) * tile_size,
                fill="white", width=2
            )

    def send_block_update(self):
        if not self.is_solo:
            self.safe_send({
                "type": "block_update",
                "next_queue": self.next_queue,
                "hold_block": self.hold_piece
            })

    def draw(self):
        if self.canvas:
            self.canvas.delete("all")
            tile_size = 30  # Use the same tile size as your blocks

            # Draw faint grid
            for i in range(11):
                self.canvas.create_line(i * tile_size, 0, i * tile_size, 20 * tile_size, fill="#333355")
            for i in range(21):
                self.canvas.create_line(0, i * tile_size, 10 * tile_size, i * tile_size, fill="#333355")

            # Draw shadow (darker, semi-transparent)
            shadow = self.get_shadow_piece()
            shape = shadow['shape']
            for y, row in enumerate(shape):
                for x, val in enumerate(row):
                    if val:
                        self.canvas.create_rectangle(
                            (shadow['x'] + x) * tile_size,
                            (shadow['y'] + y) * tile_size,
                            (shadow['x'] + x + 1) * tile_size,
                            (shadow['y'] + y + 1) * tile_size,
                            fill="#222222",
                            outline="gray",
                            stipple="gray25"
                        )
            # Draw current piece and board
            temp_board = self.get_temp_board_with_piece()
            for y in range(20):
                for x in range(10):
                    if temp_board[y][x]:
                        self.draw_tile(self.canvas, x, y, "green", tile_size=tile_size)

            if not self.is_solo and self.opponent_canvas and self.latest_opponent_piece and self.latest_opponent_board:
                self.draw_opponent_board_with_piece(self.latest_opponent_board, self.latest_opponent_piece)

            self.draw_next_piece()
            self.draw_hold_piece()
            self.send_block_update()

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
            tile_size = 30
            # Draw faint grid
            for i in range(11):
                self.opponent_canvas.create_line(i * tile_size, 0, i * tile_size, 20 * tile_size, fill="#553333")
            for i in range(21):
                self.opponent_canvas.create_line(0, i * tile_size, 10 * tile_size, i * tile_size, fill="#553333")
            for y in range(20):
                for x in range(10):
                    if board[y][x]:
                        self.draw_tile(self.opponent_canvas, x, y, "red", tile_size=tile_size)


    def draw_opponent_board_with_piece(self, board, piece):
        if self.opponent_canvas:
            self.opponent_canvas.delete("all")
            tile_size = 30
            # Draw grid
            for i in range(11):
                self.opponent_canvas.create_line(i * tile_size, 0, i * tile_size, 20 * tile_size, fill="#553333")
            for i in range(21):
                self.opponent_canvas.create_line(0, i * tile_size, 10 * tile_size, i * tile_size, fill="#553333")
            # Draw landed blocks
            for y in range(20):
                for x in range(10):
                    if board[y][x]:
                        self.draw_tile(self.opponent_canvas, x, y, "red", tile_size=tile_size)
            # Draw active piece
            shape = piece['shape']
            for y, row in enumerate(shape):
                for x, val in enumerate(row):
                    if val:
                        px = piece['x'] + x
                        py = piece['y'] + y
                        if 0 <= px < 10 and 0 <= py < 20:
                            self.draw_tile(self.opponent_canvas, px, py, "purple", tile_size=tile_size)

    def draw_opponent_pieces(self):
        for i, canvas in enumerate(self.opponent_next_canvases):
            if not canvas.winfo_exists():
                continue
            canvas.delete("all")
            if i < len(self.opponent_next_queue):
                self._draw_block_on_canvas(canvas, self.opponent_next_queue[i]['shape'], fill="purple")

        # Draw opponent's hold block
        if self.opponent_hold_canvas and self.opponent_hold_canvas.winfo_exists():
            self.opponent_hold_canvas.delete("all")
            block = getattr(self, "opponent_hold_block", None)
            if block and "shape" in block:
                self._draw_block_on_canvas(self.opponent_hold_canvas, block["shape"], fill="cyan")

    def _draw_block_on_canvas(self, canvas, shape, fill="gray"):
        size = int(canvas["width"])
        rows = len(shape)
        cols = len(shape[0])
        margin = size // 10
        max_block = max(rows, cols)
        tile_size = (size - 2 * margin) // max_block
        block_width = cols * tile_size
        block_height = rows * tile_size
        offset_x = (size - block_width) // 2
        offset_y = (size - block_height) // 2
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    canvas.create_rectangle(
                        offset_x + x * tile_size,
                        offset_y + y * tile_size,
                        offset_x + (x + 1) * tile_size,
                        offset_y + (y + 1) * tile_size,
                        fill=fill, outline="black"
                    )

    def draw_next_piece(self):
        for i, canvas in enumerate(self.next_piece_canvases):
            canvas.delete("all")
            if i < len(self.next_queue):
                self._draw_block_on_canvas(canvas, self.next_queue[i]['shape'], fill="purple")


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

    def check_collision(self, piece):
        shape = piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    px = piece['x'] + x
                    py = piece['y'] + y
                    if px < 0 or px >= 10 or py >= 20 or (py >= 0 and self.board[py][px]):
                        return True
        return False

    def get_shadow_piece(self):
        shadow_piece = {
            'shape': [row[:] for row in self.current_piece['shape']],
            'x': self.current_piece['x'],
            'y': self.current_piece['y']
        }
        while True:
            shadow_piece['y'] += 1
            if self.check_collision(shadow_piece):
                shadow_piece['y'] -= 1
                break
        return shadow_piece

    def freeze(self):
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, val in enumerate(row):
                if val:
                    bx = self.current_piece['x'] + x
                    by = self.current_piece['y'] + y
                    if 0 <= bx < 10 and 0 <= by < 20:
                        self.board[by][bx] = 1
        self.clear_lines()
        self.current_piece = self.pop_next_piece()
        self.can_hold = True
        if self.collision():
            self.running = False
            if not self.is_solo:
                self.safe_send({"type": "game_over"})
            if self.score_label:
                self.score_label.config(text="Game Over!")
            self.save_high_score()
            self.root.after(500, self.show_game_over_overlay)

        if self.place_sound:
            self.place_sound.play()

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

        now = time.time()

        if now - self.last_board_send_time > 0.5:
                self.safe_send({"type": "board", "board": self.board})
                self.last_board_send_time = now

        self.root.after(500, self.game_loop)

    def network_update_loop(self):
        while True:
            if self.running and not self.is_solo and self.current_piece and self.board:
                self.safe_send({
                    "type": "active_piece",
                    "piece": self.current_piece,
                    "board": self.board
                })
            time.sleep(self.network_update_interval)

    def key_press(self, event):
        if not self.running or not self.canvas:
            return

        redraw = False

        if event.keysym in ['a', 'Left']:
            self.move(-1, 0)
            redraw = True
        elif event.keysym in ['d', 'Right']:
            self.move(1, 0)
            redraw = True
        elif event.keysym in ['s', 'Down']:
            self.move(0, 1)
            redraw = True
        elif event.keysym in ['w', 'Up']:
            self.rotate()
            redraw = True
        elif event.keysym in ['Shift_L', 'Shift_R']:
            self.hold_current_piece()
            redraw = True
        elif event.keysym == 'space':
            # Hard drop
            while self.move(0, 1):
                pass  # Do not call draw here
            if self.hard_drop_sound:
                self.hard_drop_sound.play()
            self.shake_canvas()
            self.freeze()
            redraw = True

        if redraw:
            self.draw()

    def show_game_over_overlay(self, message="Game Over!"):
        overlay = tk.Frame(self.root, bg="#222244")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()

        overlay_bg = tk.Frame(overlay, bg="#111133", bd=0)
        overlay_bg.place(relx=0.15, rely=0.2, relwidth=0.7, relheight=0.5)

        tk.Label(overlay_bg, text=message, font=self.FONT_TITLE, bg="#111133", fg="orange").pack(pady=40)

        btn_frame = tk.Frame(overlay_bg, bg="#111133")
        btn_frame.pack(pady=20)

        def on_lobby():
            overlay.destroy()
            self.in_game = False
            self.ready = False
            if self.is_solo:
                self.show_lobby_menu()
            else:
                self.lobby_screen()
                if hasattr(self, 'current_lobby_id') and self.current_lobby_id:
                    self.safe_send({'type': 'get_lobby_state', 'lobby_id': self.current_lobby_id})

        def on_play_again():
            overlay.destroy()
            self.in_game = False
            self.ready = True
            self.is_solo = True
            self.force_start()  # Start a new solo game

        def on_quit():
            overlay.destroy()
            self.in_game = False
            self.ready = False
            if self.is_solo:
                self.show_lobby_menu()
            else:
                self.lobby_screen()
                if hasattr(self, 'current_lobby_id') and self.current_lobby_id:
                    self.safe_send({'type': 'get_lobby_state', 'lobby_id': self.current_lobby_id})

        tk.Button(btn_frame, text="Back to Lobby", font=self.FONT_BUTTON, bg="#44aa88", fg="white", width=16,
                  command=on_lobby).pack(side="left", padx=10)

        if self.is_solo:
            tk.Button(btn_frame, text="Play Again", font=self.FONT_BUTTON, bg="#0077cc", fg="white", width=16,
                      command=on_play_again).pack(side="left", padx=10)
        else:
            tk.Button(btn_frame, text="Quit", font=self.FONT_BUTTON, bg="#aa4444", fg="white", width=16,
                      command=on_quit).pack(side="left", padx=10)

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