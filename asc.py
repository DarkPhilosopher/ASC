#!/data/data/com.termux/files/usr/bin/python3
"""ASC -- move a cursor (shown as an underscore) around a fixed 16x16
grid of ASCII squares, and type any letter to spawn it right there,
under the cursor.

Requested directly: "the game will let me spawn where there is an
underscore as my cursor any letter and place it on ASC square area of
16x16 area."

    python3 asc.py

Controls: arrows/wasd move the cursor, any letter key places it at the
cursor's current square, space clears that square back to empty, q
quits (autosaves first).

No external libraries -- one file, Python's own standard library only.
"""

import json
import os
import select
import shutil
import sys
import termios
import time
import tty

SIZE = 16  # fixed, not derived from the terminal -- "16x16 area" literally
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grid.json")

REVERSE = "\033[7m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# state -- just the grid and where the cursor is
# ---------------------------------------------------------------------------

def new_state():
    return {"cursor_x": SIZE // 2, "cursor_y": SIZE // 2, "grid": {}}


def _key(x, y):
    return "%d,%d" % (x, y)


def load_grid(state):
    if not os.path.exists(SAVE_FILE):
        return
    try:
        with open(SAVE_FILE) as f:
            state["grid"] = json.load(f)
    except (OSError, ValueError):
        pass


def save_grid(state):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(state["grid"], f)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# the three things a keypress can do
# ---------------------------------------------------------------------------

def move(state, dx, dy):
    state["cursor_x"] = max(0, min(SIZE - 1, state["cursor_x"] + dx))
    state["cursor_y"] = max(0, min(SIZE - 1, state["cursor_y"] + dy))


def place(state, letter):
    """Spawns `letter` at the cursor's own square. The cursor itself
    doesn't move afterward -- arrows are the only thing that moves it,
    so typing a run of letters onto different squares is a deliberate
    move-then-type-then-move sequence, not a typewriter auto-advance."""
    state["grid"][_key(state["cursor_x"], state["cursor_y"])] = letter


def clear(state):
    state["grid"].pop(_key(state["cursor_x"], state["cursor_y"]), None)


# ---------------------------------------------------------------------------
# drawing
# ---------------------------------------------------------------------------

def render(state):
    grid = [[" "] * SIZE for _ in range(SIZE)]
    for k, letter in state["grid"].items():
        x, y = (int(p) for p in k.split(","))
        grid[y][x] = letter
    cx, cy = state["cursor_x"], state["cursor_y"]
    grid[cy][cx] = REVERSE + (grid[cy][cx] if grid[cy][cx] != " " else "_") + RESET
    lines = ["+" + "-" * SIZE + "+"]
    lines += ["|" + "".join(row) + "|" for row in grid]
    lines.append("+" + "-" * SIZE + "+")
    return lines


def draw(state):
    out = ["\033[H\033[2J"]
    out.extend(render(state))
    placed = len(state["grid"])
    out.append("pos %d,%d   %d square%s filled" % (state["cursor_x"], state["cursor_y"],
                                                     placed, "" if placed == 1 else "s"))
    out.append("arrows/wasd move . any letter spawns it . space clears . q quits")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# raw keyboard -- same shape as gridplace.py's own Keyboard
# ---------------------------------------------------------------------------

class Keyboard:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old = None

    def __enter__(self):
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, *exc):
        if self.old is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def pressed(self):
        if not select.select([self.fd], [], [], 0)[0]:
            return None
        ch = os.read(self.fd, 1)
        if ch == b"\x1b":
            if select.select([self.fd], [], [], 0.05)[0]:
                rest = os.read(self.fd, 2)
                return {b"[A": "up", b"[B": "down", b"[C": "right", b"[D": "left"}.get(rest)
            return "quit"
        if ch in (b"\x03", b"\x04"):
            return "quit"
        text = ch.decode("utf-8", "ignore")
        low = text.lower()
        if low in ("w", "a", "s", "d"):
            return {"w": "up", "a": "left", "s": "down", "d": "right"}[low]
        if low == "q":
            return "quit"
        if text == " ":
            return "clear"
        if text.isalpha():
            return ("letter", text)
        return None


def run():
    state = new_state()
    load_grid(state)
    moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    with Keyboard() as kb:
        while True:
            draw(state)
            time.sleep(0.05)
            key = kb.pressed()
            if key == "quit":
                break
            elif key in moves:
                move(state, *moves[key])
            elif key == "clear":
                clear(state)
            elif isinstance(key, tuple) and key[0] == "letter":
                place(state, key[1])
    save_grid(state)
    print("\nsaved to " + SAVE_FILE)


if __name__ == "__main__":
    run()
