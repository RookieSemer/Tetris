import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time

# Simulate asset loading
def simulate_loading(progressbar, loading_window, root):
    for i in range(101):
        time.sleep(0.02)
        progressbar["value"] = i
        loading_window.update_idletasks()
    loading_window.destroy()
    open_main_game(root)

# Start loading screen
def start_loading(root):
    loading_window = tk.Toplevel(root)
    loading_window.geometry("600x400")
    loading_window.title("Game Loading")
    loading_window.resizable(False, False)

    # Load and place background image
    bg_image = Image.open("tetris bg.jpg").resize((600, 400))
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = tk.Label(loading_window, image=bg_photo)
    bg_label.image = bg_photo
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    # Transparent label over background
    label = tk.Label(loading_window, text="Loading Game...", font=("Helvetica", 20, "bold"), bg="#000000", fg="white")
    label.pack(pady=30)

    # Style and add progress bar
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

    threading.Thread(target=simulate_loading, args=(progressbar, loading_window, root), daemon=True).start()

# Main game window after loading
def open_main_game(root):
    game_window = tk.Toplevel(root)
    game_window.geometry("600x400")
    game_window.title("Main Game")
    tk.Label(game_window, text="Welcome to the Game!", font=("Pixel Emulator", 22)).pack(pady=150)

# Main setup
root = tk.Tk()
root.withdraw()
start_loading(root)
root.mainloop()