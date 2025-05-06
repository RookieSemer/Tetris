import tkinter as tk
from tkinter import simpledialog, messagebox


class LobbySystem:
    def __init__(self):
        self.lobbies = {}  # lobby_name -> {password, public, players}

    def create_lobby(self, name, public, password, creator):
        if name in self.lobbies:
            return False, "Lobby name already taken"
        self.lobbies[name] = {
            'public': public,
            'password': password,
            'players': [creator]
        }
        return True, "Lobby created"

    def get_lobby_list(self):
        return {
            name: lobby for name, lobby in self.lobbies.items()
            if lobby['public']
        }

    def join_lobby(self, name, user, password=""):
        if name not in self.lobbies:
            return False, "Lobby not found"
        lobby = self.lobbies[name]
        if not lobby['public'] and lobby['password'] != password:
            return False, "Incorrect password"
        if user not in lobby['players']:
            lobby['players'].append(user)
        return True, "Joined lobby"


class LobbyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tetris Lobby")
        self.geometry("500x400")
        self.lobby_system = LobbySystem()
        self.username = simpledialog.askstring("Username", "Enter your username:")

        self.lobby_frame = tk.Frame(self)
        self.lobby_frame.pack(pady=10)

        self.lobby_listbox = tk.Listbox(self.lobby_frame, width=50, height=10)
        self.lobby_listbox.pack()

        self.refresh_button = tk.Button(self.lobby_frame, text="Refresh Lobby List", command=self.update_lobby_list)
        self.refresh_button.pack(pady=5)

        self.create_button = tk.Button(self, text="Create Lobby", command=self.create_lobby)
        self.create_button.pack(pady=5)

        self.join_button = tk.Button(self, text="Join Selected Lobby", command=self.join_lobby)
        self.join_button.pack(pady=5)

        self.players_label = tk.Label(self, text="Players:")
        self.players_label.pack(pady=5)
        self.players_listbox = tk.Listbox(self, width=50)
        self.players_listbox.pack()

        self.update_lobby_list()

    def create_lobby(self):
        name = simpledialog.askstring("Lobby Name", "Enter lobby name:")
        if not name:
            return

        public = messagebox.askyesno("Privacy", "Should this lobby be public?")
        password = ""
        if not public:
            password = simpledialog.askstring("Password", "Enter password (private lobby):")

        success, message = self.lobby_system.create_lobby(name, public, password, self.username)
        messagebox.showinfo("Create Lobby", message)
        if success:
            self.update_lobby_list()
            self.show_players(name)

    def join_lobby(self):
        selection = self.lobby_listbox.curselection()
        if not selection:
            return
        name = self.lobby_listbox.get(selection[0])
        lobby = self.lobby_system.lobbies[name]
        password = ""
        if not lobby['public']:
            password = simpledialog.askstring("Password", "Enter password:")

        success, message = self.lobby_system.join_lobby(name, self.username, password)
        messagebox.showinfo("Join Lobby", message)
        if success:
            self.show_players(name)

    def update_lobby_list(self):
        self.lobby_listbox.delete(0, tk.END)
        for name in self.lobby_system.get_lobby_list().keys():
            self.lobby_listbox.insert(tk.END, name)

    def show_players(self, lobby_name):
        self.players_listbox.delete(0, tk.END)
        players = self.lobby_system.lobbies[lobby_name]['players']
        for player in players:
            self.players_listbox.insert(tk.END, player)


if __name__ == "__main__":
    app = LobbyApp()
    app.mainloop()
