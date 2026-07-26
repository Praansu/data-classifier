# Vehicle Labeling Tool

I needed to label thousands of vehicle images for a classification project. Clicking through images one by one with a mouse? No thanks. So I built this — a keyboard-first labeling tool in PyQt5.

**17 vehicle classes. All keyboard shortcuts. Zero mouse required.**

## How it works

- Images pop up one at a time
- Hit a key (0-9 or A-G) to assign a class
- Arrow keys to navigate
- Undo if you mess up (U key)
- Zoom in if you need a closer look (Z key)
- Everything saves to SQLite automatically

## Controls

| Key | What it does |
|-----|-------------|
| `←` `→` | Previous / next image |
| `0-9`, `A-G` | Assign vehicle class |
| `U` | Undo last label |
| `Z` | Toggle zoom |
| `Q` | Quit |

## Quick start

```bash
pip install PyQt5
python reclassify_tool.py
```

## What this taught me

- PyQt5 is surprisingly capable for desktop apps
- Keyboard-first UIs are faster but harder to design well
- SQLite is perfect for local data — no server setup, just works
- Sometimes the best tool for the job is the one you build yourself

## Tech

Python, PyQt5, SQLite

## License

MIT
