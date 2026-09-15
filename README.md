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
back automatically next time you run it. The chat log (below) saves
itself to `chat.log` the moment each line is typed, not just on quit.

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

Plain text just gets logged, as chat. Recognized commands:

| Command | Does |
|---|---|
| `/clear` | wipes the whole grid |
| `/set <name> <number>` | stores a variable |
| `/vars` | lists your variables and the current target |
| `/target` | marks the cursor's own square as the target |
| `/target <x> <y>` | marks that square instead |
| `/calc <a> <op> <b>` | computes `a op b` and places the result on the target square, as a letter |
| `/quit` | leaves ASC (autosaves first, same as pressing q) |
| `/help` | lists these |

## The calculator

Requested directly: "let me set a variable and tell it a target and
what calculator symbol to exchange the other variable or number so i
can target the asc letters on the display."

`a` and `b` in `/calc <a> <op> <b>` are each either a plain number or
a name you've already `/set`; `op` is `+`, `-`, `*`, or `/`. The
numeric result becomes a letter -- 1 is `a`, 2 is `b`, and so on,
wrapping back around past 26 (or below 1) rather than ever failing --
and that letter is placed on whichever square `/target` last marked,
independent of wherever the cursor happens to be right now. The
target square shows up underlined in yellow on the grid (unless the
cursor's sitting right on it, in which case the cursor's own
highlight takes over) so you can always see where the next `/calc`
will land.

Example:

```
/set x 3
/set y 4
/target
/calc x + y
```

Marks the cursor's current square as the target, then places `g`
there (3 + 4 = 7, the 7th letter).

## Points, links, and when-rules

Requested directly (paraphrased): set a variable with its own name on
a specific point, tie one point to another like a string between two
pins, and have an exchange fire automatically the moment a watched
variable reaches a set amount.

| Command | Does |
|---|---|
| `/point <name>` | names the cursor's own square |
| `/point <name> <x> <y>` | names that square instead |
| `/set <point>.<var> <number>` | a variable of its own, private to that point (separate from the plain global `/set <name> <number>`) |
| `/link <from> <to>` | ties a string from one point to another |
| `/when <point>.<var> == <number>` | as soon as that's true, fires |
| `/points` | lists your points, where they are, and their own variables |
| `/rules` | lists your links and when-rules |

**What firing does**: for every point `<from>` is linked to, it adds
`<from>`'s own value of that SAME variable into `<to>`'s own value of
it (`to.var = from.var + to.var` -- `to` keeps growing, `from` is left
alone) and writes the new total onto `to`'s own square as a letter, the
same 1=a/2=b/wraps-around mapping `/calc` uses. This is checked
continuously, live, not just when you type something -- "as soon as"
really means as soon as, the instant the watched variable equals its
amount, even if nothing else happened right then. It fires once on the
way in, not once per moment it stays true, and rearms itself the
moment the value moves away again, ready to fire again later.

Example, worked exactly:

```
/point A
/point B 3 3
/link A B
/set A.zax 5
/set B.zax 8
/when A.zax == 5
```

Fires immediately (A.zax is already 5): `B.zax` becomes `5 + 8 = 13`,
and the letter `m` (the 13th letter) is written onto B's own square.
Set `A.zax` to anything else and the rule quietly rearms; set it back
to `5` and it fires again, this time `5 + 13 = 18` -> `r`.
