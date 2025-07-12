from io import BytesIO
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import pygame
import os
import sqlite3
import random
import time

pygame.mixer.init()

conn = sqlite3.connect("playlist.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS songs (filename TEXT)")
conn.commit()

is_paused = False
current_song_index = None
song_paths = []
repeat_mode = False
last_seek_time = 0

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def load_playlist():
    for widget in song_list_frame.winfo_children():
        widget.destroy()
    song_paths.clear()

    cursor.execute("SELECT filename FROM songs")
    for index, row in enumerate(cursor.fetchall()):
        song_path = row[0]
        song_paths.append(song_path)

        frame = tk.Frame(song_list_frame, bg="#282828", bd=1, relief="flat")
        frame.pack(fill="x", padx=5, pady=4)

        img = Image.new('RGB', (50, 50), color='#1DB954')
        try:
            audio = MP3(song_path, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    img = Image.open(BytesIO(tag.data)).resize((50, 50))
                    break
        except:
            pass

        thumb = ImageTk.PhotoImage(img)
        thumb_label = tk.Label(frame, image=thumb, bg="#282828")
        thumb_label.image = thumb
        thumb_label.pack(side="left", padx=10)

        label = tk.Label(frame, text=os.path.basename(song_path), anchor="w",
                         font=("Helvetica", 11), fg="white", bg="#282828")
        label.pack(side="left", fill="x", expand=True)

        for widget in [frame, label, thumb_label]:
            widget.bind("<Button-1>", lambda e, idx=index: play_song(idx))

def add_song():
    files = filedialog.askopenfilenames(filetypes=[("MP3 files", "*.mp3")])
    if files:
        for file in files:
            cursor.execute("INSERT INTO songs VALUES (?)", (file,))
        conn.commit()
        load_playlist()

def play_song(index=None):
    global is_paused, current_song_index, last_seek_time
    if index is None or index >= len(song_paths):
        return
    is_paused = False
    current_song_index = index
    song_path = song_paths[index]
    pygame.mixer.music.load(song_path)
    pygame.mixer.music.play()
    update_track_label(os.path.basename(song_path))
    show_album_art(song_path)

    song = MP3(song_path)
    seek_slider.config(to=song.info.length)
    total_time_label.config(text=format_time(song.info.length))

    highlight_current_song()
    canvas.yview_moveto(current_song_index / len(song_paths))
    last_seek_time = time.time()
    update_seek_bar()

def update_seek_bar():
    global last_seek_time
    if pygame.mixer.music.get_busy() and current_song_index is not None:
        try:
            current_pos = pygame.mixer.music.get_pos() / 1000
            if time.time() - last_seek_time > 0.5:
                seek_slider.set(current_pos)
                current_time_label.config(text=format_time(current_pos))
        except Exception as e:
            print(f"Seek update error: {e}")
    root.after(200, update_seek_bar)

def seek_to_position(event=None):
    global last_seek_time, is_paused
    if current_song_index is not None:
        try:
            seek_pos = seek_slider.get()
            last_seek_time = time.time()
            

            was_playing = pygame.mixer.music.get_busy() and not is_paused
            
            
            pygame.mixer.music.stop()
            pygame.mixer.music.load(song_paths[current_song_index])
            
            
            pygame.mixer.music.play(start=seek_pos)
            
            
            if not was_playing:
                pygame.mixer.music.pause()
                is_paused = True
            
            
            current_time_label.config(text=format_time(seek_pos))
        except Exception as e:
            print(f"Seek error: {e}")

def play_previous_song():
    if current_song_index is not None and current_song_index > 0:
        play_song(current_song_index - 1)

def pause_song():
    global is_paused
    if pygame.mixer.music.get_busy():
        if not is_paused:
            pygame.mixer.music.pause()
            is_paused = True
        else:
            pygame.mixer.music.unpause()
            is_paused = False
    elif song_paths:
        play_song(current_song_index if current_song_index is not None else 0)

def stop_song():
    pygame.mixer.music.stop()

def remove_song():
    global current_song_index
    if current_song_index is not None:
        song = song_paths[current_song_index]
        cursor.execute("DELETE FROM songs WHERE filename = ?", (song,))
        conn.commit()
        current_song_index = None
        load_playlist()

def update_track_label(track):
    track_label.config(text=f"🎵 Now Playing: {track}")

def highlight_current_song():
    for widget in song_list_frame.winfo_children():
        widget.config(bg="#282828")
    if current_song_index is not None:
        song_list_frame.winfo_children()[current_song_index].config(bg="#1DB954")

def set_volume(val):
    pygame.mixer.music.set_volume(float(val))

def check_for_song_end():
    global current_song_index, is_paused
    if not is_paused and not pygame.mixer.music.get_busy():
        if repeat_mode:
            play_song(current_song_index)
        else:
            play_next_song()
    root.after(1000, check_for_song_end)

def play_next_song():
    if current_song_index is not None and current_song_index + 1 < len(song_paths):
        play_song(current_song_index + 1)

def toggle_repeat():
    global repeat_mode
    repeat_mode = not repeat_mode
    repeat_btn.config(bg="#1DB954" if repeat_mode else "#282828")

def shuffle_play():
    if len(song_paths) > 0:
        random_index = random.randint(0, len(song_paths) - 1)
        play_song(random_index)

def move_selection_up():
    global current_song_index
    if current_song_index is not None and current_song_index > 0:
        current_song_index -= 1
        highlight_current_song()
        canvas.yview_moveto(current_song_index / len(song_paths))

def move_selection_down():
    global current_song_index
    if current_song_index is not None and current_song_index + 1 < len(song_paths):
        current_song_index += 1
        highlight_current_song()
        canvas.yview_moveto(current_song_index / len(song_paths))

def show_album_art(song_path):
    try:
        audio = MP3(song_path, ID3=ID3)
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                thumb_img = Image.open(BytesIO(tag.data)).resize((200, 200))
                thumb_photo = ImageTk.PhotoImage(thumb_img)
                album_art_label.config(image=thumb_photo, text='')
                album_art_label.image = thumb_photo
                return
    except:
        pass
    album_art_label.config(image='', text='No Album Art', fg='white')
    album_art_label.image = None

def on_key_press(event):
    key = event.keysym
    if key == "space":
        pause_song()
    elif key == "Right":
        play_next_song()
    elif key == "Left":
        play_previous_song()
    elif key == "Up":
        move_selection_up()
    elif key == "Down":
        move_selection_down()
    elif key == "Escape":
        stop_song()
    elif key == "Return":
        play_song(current_song_index if current_song_index is not None else 0)
    elif key == "r":
        toggle_repeat()
    elif key == "s":
        shuffle_play()
    elif key == "plus" or key == "equal":
        current_vol = pygame.mixer.music.get_volume()
        new_vol = min(1.0, current_vol + 0.1)
        pygame.mixer.music.set_volume(new_vol)
        volume_slider.set(new_vol)
    elif key == "minus":
        current_vol = pygame.mixer.music.get_volume()
        new_vol = max(0.0, current_vol - 0.1)
        pygame.mixer.music.set_volume(new_vol)
        volume_slider.set(new_vol)

root = tk.Tk()
root.title("🎧  MP3 Player")
root.attributes('-fullscreen', True)
root.config(bg="#191414")

def exit_fullscreen(event):
    root.attributes("-fullscreen", False)

def toggle_fullscreen(event):
    root.attributes("-fullscreen", not root.attributes("-fullscreen"))

root.bind("<Escape>", exit_fullscreen)
root.bind("<F11>", toggle_fullscreen)


header = tk.Frame(root, bg="#191414")
header.pack(fill="x", pady=10)

try:
    logo_path = r"C:\Users\akash\OneDrive\Desktop\projects(AKASH)\MP3_PLAYER\logo.png.jpg"
    logo_img = Image.open(logo_path).resize((120, 120))
    logo_photo = ImageTk.PhotoImage(logo_img)
    tk.Label(header, image=logo_photo, bg="#191414").pack(side="left", padx=(30, 10))
except:
    pass

tk.Label(header, text="KPRIT - COE", font=("Helvetica", 20, "bold"), fg="#1DB954", bg="#191414").pack(side="left")


content = tk.Frame(root, bg="#191414")
content.pack(fill="both", expand=True, padx=30, pady=10)

left = tk.Frame(content, bg="#191414")
left.pack(side="left", padx=20)

track_label = tk.Label(left, text="🎵 Now Playing:", bg="#191414", fg="white", font=("Helvetica", 16))
track_label.pack(pady=10)

album_art_label = tk.Label(left, bg="#191414", fg='white', font=("Helvetica", 12))
album_art_label.pack(pady=5)

playlist_canvas_frame = tk.Frame(content, bg="#191414")
playlist_canvas_frame.pack(side="right", fill="both", expand=True, padx=(20, 30))

playlist_label = tk.Label(playlist_canvas_frame, text="🎶 Playlist", font=("Helvetica", 16, "bold"),
                          fg="#1DB954", bg="#191414")
playlist_label.pack(anchor="w", pady=(0, 5))

canvas = tk.Canvas(playlist_canvas_frame, bg="#191414", highlightthickness=0)
scrollbar = tk.Scrollbar(playlist_canvas_frame, orient="vertical", command=canvas.yview)
song_list_frame = tk.Frame(canvas, bg="#191414")

song_list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=song_list_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")


controls = tk.Frame(root, bg="#191414")
controls.pack(pady=25)

def styled_btn(text, command):
    return tk.Button(controls, text=text, width=12, command=command,
                     bg="#1DB954", fg="black", font=("Helvetica", 10, "bold"),
                     activebackground="#1ED760")

btns = [
    ("▶ Play", lambda: play_song(0) if song_paths else None),
    ("⏯ Pause", pause_song),
    ("⏹ Stop", stop_song),
    ("📂 Add", add_song),
    ("🗑 Delete", remove_song),
    ("🔁 Repeat", toggle_repeat),
    ("🔀 Shuffle", shuffle_play)
]

for i, (txt, cmd) in enumerate(btns):
    btn = styled_btn(txt, cmd)
    if txt.startswith("🔁"):
        repeat_btn = btn
    btn.grid(row=0, column=i, padx=5)


slider_frame = tk.Frame(root, bg="#191414")
slider_frame.pack(pady=10)

time_frame = tk.Frame(slider_frame, bg="#191414")
time_frame.pack(fill="x")

current_time_label = tk.Label(time_frame, text="00:00", fg="white", bg="#191414")
current_time_label.pack(side="left")

total_time_label = tk.Label(time_frame, text="00:00", fg="white", bg="#191414")
total_time_label.pack(side="right")

seek_slider = tk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                       length=600, bg="#191414", fg="white", troughcolor="#1DB954",
                       highlightthickness=0)
seek_slider.pack(fill="x", pady=5)
seek_slider.bind("<ButtonRelease-1>", seek_to_position)
seek_slider.bind("<B1-Motion>", seek_to_position)

volume_slider = tk.Scale(slider_frame, from_=0, to=1, resolution=0.1,
                         orient=tk.HORIZONTAL, length=200, label="🔊 Volume",
                         bg="#191414", fg="white", troughcolor="#1DB954",
                         highlightthickness=0, command=set_volume)
volume_slider.set(0.7)
pygame.mixer.music.set_volume(0.7)
volume_slider.pack(pady=5)

root.bind("<Key>", on_key_press)

load_playlist()
check_for_song_end()

root.mainloop()
conn.close()