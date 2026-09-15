# ASC

Move a cursor -- shown as an underscore -- around a fixed 16x16 grid
of ASCII squares, and type any letter to spawn it right there, under
the cursor.

Requested directly: "the game will let me spawn where there is an
underscore as my cursor any letter and place it on ASC square area of
16x16 area."

## Running it

```
python3 asc.py
```

One file, Python's own standard library only. Your grid is saved to
`grid.json`, right next to `asc.py`, every time you quit, and loaded
back automatically next time you run it.

## Controls

| Key | Does |
|---|---|
| arrows / wasd | move the cursor |
| any letter | spawns that letter on the cursor's current square |
| space | clears the cursor's current square back to empty |
| / | opens the terminal/chat line below the grid |
| q | quits (autosaves first) |

The cursor is always shown in reverse video, whether the square under
it is empty (an underscore) or already has a letter on it (the letter
itself, highlighted) -- so it never disappears once you've typed
something onto its own square.

The grid is a fixed 16x16, not derived from the terminal's own size,
per the request as given.

## The terminal/chat area

Below the grid is a running log that's never cleared for as long as
the program keeps running. Press `/` to drop into it and type a line;
a blank line closes it and goes straight back to moving the cursor
around (real-time movement keys and typed text never run at the same
time -- the same reason spark2's own chat line works this way).

Plain text just gets logged, as chat. Three recognized commands:

| Command | Does |
|---|---|
| `/clear` | wipes the whole grid |
| `/quit` | leaves ASC (autosaves first, same as pressing q) |
| `/help` | lists these |
