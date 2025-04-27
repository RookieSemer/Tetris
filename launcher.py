import tkinter as tk
import subprocess
import socket
import sys
import time
import os

HOST = '127.0.0.1'
PORT = 5555

SERVER_FILE = "server.py"
CLIENT_FILE = "client.py"

class TetrisLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tetris Launcher")
        self.root.geometry("300x250")

        tk.Label(self.root, text="Tetris Launcher", font=("Arial", 16)).pack(pady=10)

        self.players_var = tk.IntVar(value=1)
        tk.Label(self.root, text="How many players?").pack()
        tk.Spinbox(self.root, from_=1, to=2, textvariable=self.players_var).pack(pady=5)

        tk.Button(self.root, text="Launch Game", command=self.launch_game).pack(pady=15)
        tk.Button(self.root, text="Exit", command=self.root.quit).pack()

        self.root.mainloop()

    def is_server_running(self):
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except:
            return False

    def start_server(self):
        subprocess.Popen([sys.executable, SERVER_FILE], creationflags=subprocess.CREATE_NEW_CONSOLE)
        time.sleep(1)

    def launch_game(self):
        players = self.players_var.get()

        if not self.is_server_running():
            self.start_server()

        subprocess.Popen([sys.executable, CLIENT_FILE], creationflags=subprocess.CREATE_NEW_CONSOLE)
        if players == 2:
            time.sleep(1)
            subprocess.Popen([sys.executable, CLIENT_FILE], creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    TetrisLauncher()