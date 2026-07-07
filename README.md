# Vehicle Labeling Tool

A desktop app for classifying vehicle images. Built with PyQt5 as a learning project to explore GUI development and data annotation workflows.

## What It Does
- Lets you browse through vehicle images from a database
- Classify each image into 1 of 17 vehicle types (car, bus, truck, motorcycle, etc.)
- All keyboard shortcuts — no mouse needed for fast labeling
- Saves labels to a SQLite database
- Supports undo, zoom, and progress tracking

## What I Learned
- Building desktop applications with PyQt5
- Working with SQLite databases
- Designing user interfaces for productivity
- Managing image data and file I/O in Python

## How to Run
```bash
pip install PyQt5
python reclassify_tool.py
```

## Controls
- Arrow keys: Navigate images
- 0-9, A-G: Assign vehicle class
- U: Undo last classification
- Q: Quit
