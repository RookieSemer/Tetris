import tkinter as tk
import subprocess
import sys
import socket
import os

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555
SERVER_FILE = "server.py"  # Change if your server file has a different name
CLIENT_FILE = "client.py"  # Change if your client file has a different name

class TetrisLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tetris Launcher")
        self.root.geometry("300x280")

        tk.Label(self.root, text="Tetris Multiplayer Launcher", font=("Arial", 16)).pack(pady=10)

        tk.Label(self.root, text="Number of Players (1-2):", font=("Arial", 12)).pack(pady=5)

        self.player_count_var = tk.IntVar(value=1)
        self.player_count_spinbox = tk.Spinbox(self.root, from_=1, to=2, textvariable=self.player_count_var,
                                               font=("Arial", 12), width=5)
        self.player_count_spinbox.pack(pady=5)

        tk.Label(self.root, text="Solo play is supported!", font=("Arial", 10), fg="green").pack()

        tk.Button(self.root, text="Create Lobby", command=self.launch_lobby, width=20).pack(pady=10)
        tk.Button(self.root, text="Exit", command=self.root.quit, width=20).pack(pady=5)

        self.root.mainloop()

    def is_server_running(self):
        try:
            with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError):
            return False

    def start_server(self):
        try:
            # Start server in the background
            subprocess.Popen([sys.executable, SERVER_FILE])
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to start server: {e}")

    def launch_lobby(self):
        if not self.is_server_running():
            self.start_server()

        player_count = self.player_count_var.get()

        for _ in range(player_count):
            try:
                subprocess.Popen([sys.executable, CLIENT_FILE])
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to launch client: {e}")

if __name__ == "__main__":
    TetrisLauncher()