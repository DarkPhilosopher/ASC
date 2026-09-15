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
quits (autosaves first). / opens a terminal/chat line below the grid --
plain text just logs there (a running chat, never cleared, saved to
disk the moment each line is typed and loaded back on the next run --
not just on a clean quit); /clear wipes the whole grid, /quit leaves,
/help lists this. A blank line closes the chat line and goes back to
moving the cursor around, same as spark2.py's own chat_break --
real-time movement keys and typed text must never fight over the same
keystrokes, so cooked-mode text entry and raw-mode single-key play are
always one or the other, never both at once.

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
_HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(_HERE, "grid.json")
HISTORY_FILE = os.path.join(_HERE, "chat.log")

REVERSE = "\033[7m"
TARGET_MARK = "\033[33;4m"  # yellow + underline -- distinct from the cursor's reverse video
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# state -- just the grid and where the cursor is
# ---------------------------------------------------------------------------

def new_state():
    return {"cursor_x": SIZE // 2, "cursor_y": SIZE // 2, "grid": {}, "history": [],
            "vars": {}, "target": None}


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


def load_history(state):
    if not os.path.exists(HISTORY_FILE):
        return
    try:
        with open(HISTORY_FILE) as f:
            state["history"] = [line.rstrip("\n") for line in f]
    except OSError:
        pass


def _log(state, line):
    """Appends one line to the in-memory history AND to disk, right
    then -- not just on quit. Requested directly ("make so it always
    saves the chat log"): a crash, a killed session, or the phone
    itself dying mid-game must never lose anything already said, the
    same reasoning Spark's own chat panel follows ("nothing typed is
    ever silently lost, live or not"). Appending one line at a time,
    rather than rewriting the whole file, is also just the cheaper
    thing to do on every single line."""
    state["history"].append(line)
    try:
        with open(HISTORY_FILE, "a") as f:
            f.write(line + "\n")
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


CHAT_HELP = [
    "/clear -- wipes the whole grid",
    "/set <name> <number> -- stores a variable",
    "/vars -- lists your variables and the current target",
    "/target -- marks the cursor's own square as the target",
    "/target <x> <y> -- marks that square instead",
    "/calc <a> <op> <b> -- a and b are each a variable name or a plain",
    "  number, op is + - * or / -- the result is placed on the target",
    "  square as a letter (1=a, 2=b, ... wrapping past 26 back to a)",
    "/quit -- leaves ASC", "/help -- this",
]

OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}


def _operand(state, token):
    """token is either a plain number or an already-/set variable name.
    Returns (value, error) -- exactly one of the two is None."""
    try:
        return float(token), None
    except ValueError:
        pass
    if token in state["vars"]:
        return state["vars"][token], None
    return None, "'%s' isn't a number or a variable you've /set" % token


def _letter_for(n):
    """1 -> a, 2 -> b, ... 26 -> z, 27 -> a again -- wraps both ways,
    so a variable that goes negative or past 26 still always lands on
    a real, placeable letter rather than erroring."""
    return chr(ord("a") + (round(n) - 1) % 26)


def run_chat_line(state, said):
    """One line typed into the terminal/chat area below the grid.
    Returns True if the whole program should quit. Anything that
    isn't a recognized command just gets logged, plainly, as chat --
    same as termux_chat.py/spark2.py's own chat areas."""
    said = said.strip()
    if not said:
        return False
    if said == "/quit":
        _log(state, "you: /quit")
        return True
    if said == "/clear":
        state["grid"].clear()
        _log(state, "you: /clear")
        _log(state, "grid wiped")
        return False
    if said == "/help":
        _log(state, "you: /help")
        for line in CHAT_HELP:
            _log(state, line)
        return False
    if said == "/vars":
        _log(state, "you: /vars")
        if not state["vars"]:
            _log(state, "no variables set yet -- /set <name> <number>")
        for name, value in state["vars"].items():
            _log(state, "  %s = %g" % (name, value))
        _log(state, "target: %s" % (state["target"] and "%d,%d" % state["target"]
                                     or "none yet -- /target"))
        return False

    words = said.split()

    if words[0] == "/set":
        _log(state, "you: " + said)
        if len(words) != 3:
            _log(state, "try: /set <name> <number>")
            return False
        try:
            state["vars"][words[1]] = float(words[2])
        except ValueError:
            _log(state, "'%s' isn't a plain number" % words[2])
            return False
        _log(state, "%s = %g" % (words[1], state["vars"][words[1]]))
        return False

    if words[0] == "/target":
        _log(state, "you: " + said)
        if len(words) == 1:
            state["target"] = (state["cursor_x"], state["cursor_y"])
        elif len(words) == 3 and words[1].isdigit() and words[2].isdigit():
            x, y = int(words[1]), int(words[2])
            if not (0 <= x < SIZE and 0 <= y < SIZE):
                _log(state, "that's off the %dx%d grid" % (SIZE, SIZE))
                return False
            state["target"] = (x, y)
        else:
            _log(state, "try: /target  or  /target <x> <y>")
            return False
        _log(state, "target set: %d,%d" % state["target"])
        return False

    if words[0] == "/calc":
        _log(state, "you: " + said)
        if len(words) != 4 or words[2] not in OPS:
            _log(state, "try: /calc <a> <op> <b> -- op is + - * or /")
            return False
        if state["target"] is None:
            _log(state, "no target yet -- /target first")
            return False
        a, err = _operand(state, words[1])
        if err:
            _log(state, err)
            return False
        b, err = _operand(state, words[3])
        if err:
            _log(state, err)
            return False
        try:
            result = OPS[words[2]](a, b)
        except ZeroDivisionError:
            _log(state, "can't divide by zero")
            return False
        letter = _letter_for(result)
        state["grid"][_key(*state["target"])] = letter
        _log(state, "%g %s %g = %g -> '%s' placed at %d,%d"
             % (a, words[2], b, result, letter, state["target"][0], state["target"][1]))
        return False
    _log(state, "you: " + said)
    return False


# ---------------------------------------------------------------------------
# drawing
# ---------------------------------------------------------------------------

def render(state):
    grid = [[" "] * SIZE for _ in range(SIZE)]
    for k, letter in state["grid"].items():
        x, y = (int(p) for p in k.split(","))
        grid[y][x] = letter
    target = state["target"]
    if target is not None and target != (state["cursor_x"], state["cursor_y"]):
        tx, ty = target
        grid[ty][tx] = TARGET_MARK + (grid[ty][tx] if grid[ty][tx] != " " else ".") + RESET
    cx, cy = state["cursor_x"], state["cursor_y"]
    grid[cy][cx] = REVERSE + (grid[cy][cx] if grid[cy][cx] != " " else "_") + RESET
    lines = ["+" + "-" * SIZE + "+"]
    lines += ["|" + "".join(row) + "|" for row in grid]
    lines.append("+" + "-" * SIZE + "+")
    return lines


def _log_height():
    """However many rows are left under the grid/status/help lines and
    the rule that separates them from the chat log -- recomputed every
    draw from the real terminal size, never a guessed constant."""
    _, rows = shutil.get_terminal_size(fallback=(40, 24))
    return max(3, rows - (SIZE + 2) - 3)


def draw(state):
    out = ["\033[H\033[2J"]
    out.extend(render(state))
    placed = len(state["grid"])
    out.append("pos %d,%d   %d square%s filled" % (state["cursor_x"], state["cursor_y"],
                                                     placed, "" if placed == 1 else "s"))
    out.append("arrows/wasd move . any letter spawns it . space clears . q quits . / chats")
    out.append("-" * (SIZE + 2))
    out.extend(state["history"][-_log_height():])
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

    def pause(self):
        """Drops back to cooked mode temporarily, for a real input()
        line -- raw single-key reads and a cooked chat line must never
        run at once, or a keystroke meant for one gets eaten by the
        other."""
        self.__exit__()

    def resume(self):
        self.__enter__()

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
        if text == "/":
            return "chat"
        if text.isalpha():
            return ("letter", text)
        return None


def chat_break(kb, state):
    """Drops to cooked mode for a real input() line, the same reason
    spark2.py's own chat_break does: real-time movement keys and typed
    text must never fight over the same keystrokes. Returns True if
    /quit was typed, so run()'s own loop knows to stop, not just this
    one line. A blank line closes the chat line and goes straight back
    to moving the cursor -- it isn't itself a command worth logging."""
    kb.pause()
    quitting = False
    try:
        while True:
            draw(state)
            try:
                said = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            if not said.strip():
                break
            if run_chat_line(state, said):
                quitting = True
                break
    finally:
        kb.resume()
    return quitting


def run():
    state = new_state()
    load_grid(state)
    load_history(state)
    moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    with Keyboard() as kb:
        while True:
            draw(state)
            time.sleep(0.05)
            key = kb.pressed()
            if key == "quit":
                break
            elif key == "chat":
                if chat_break(kb, state):
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
