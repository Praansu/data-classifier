# Vehicle Labeling Tool

I had thousands of vehicle images to label. Clicking through them one by one with a mouse was painful. So I made this — a PyQt5 app where you just press keys. 17 vehicle classes, zero mouse required.

```bash
pip install PyQt5
python reclassify_tool.py
```

| key | what it does |
|-----|-------------|
| ← → | navigate images |
| 0-9, A-G | assign class |
| U | undo |
| Z | zoom |
| Q | quit |

SQLite saves everything automatically. Built this because I was too impatient to do it manually. Sometimes the best tool is the one you build yourself.
