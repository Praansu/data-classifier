# ============================================================
#  reclassify_tool.py  —  Keyboard-First Vehicle Labeler
#
#  HOW TO RUN:
#    1. venv\Scripts\activate
#    2. python reclassify_tool.py
#
#  ═══════════════════════════════════════════════
#  ALL KEYBOARD SHORTCUTS
#  ═══════════════════════════════════════════════
#
#  NAVIGATION (no mouse needed)
#  ─────────────────────────────
#  Arrow keys      → move selected image (yellow border)
#  Page Down / ]   → next page
#  Page Up  / [    → previous page
#  Home            → jump to first page
#  End             → jump to last page
#
#  CLASSIFY SELECTED IMAGE (instant, no zoom needed)
#  ──────────────────────────────────────────────────
#  0 → Multi Axle Truck      9 → Motorcycle
#  1 → Heavy Truck           A → Three Wheeler
#  2 → Light Truck           B → Tractor
#  3 → Standard Bus          C → Cycle
#  4 → Mini Bus              D → Rickshaw (Passenger)
#  5 → Micro Bus             E → Animal Drawn Vehicle
#  6 → Car                   F → Power Tiller
#  7 → Four Wheel Drive      G → Rickshaw (Hand Cart)
#  8 → Utility Vehicle
#
#  OTHER
#  ──────
#  Enter / Space   → open zoom (optional detail view)
#  Escape          → close zoom
#  U               → undo last classification
#  Q               → quit
#
#  GRID LAYOUT: 3 columns × 3 rows = 9 large images per page
#  Each image: 280×220px — large enough to classify without zoom
# ============================================================

import sys
import io
import os
import sqlite3

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QComboBox, QDialog,
    QStatusBar, QProgressBar, QFileDialog, QMessageBox,
    QShortcut
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QKeySequence


# ============================================================
# CONFIG
# ============================================================

CLASS_MAP = {
    0:  'Multi Axle Truck',
    1:  'Heavy Truck',
    2:  'Light Truck',
    3:  'Standard Bus',
    4:  'Mini Bus',
    5:  'Micro Bus',
    6:  'Car',
    7:  'Four Wheel Drive',
    8:  'Utility Vehicle',
    9:  'Motorcycle',
    10: 'Three Wheeler',
    11: 'Tractor',
    12: 'Cycle',
    13: 'Rickshaw (Passenger)',
    14: 'Animal Drawn Vehicle',
    15: 'Power Tiller',
    16: 'Rickshaw (Hand Cart)',
    22: 'DELETED'  # Added Delete option
}

KEY_MAP = {
    Qt.Key_0: 0,  Qt.Key_1: 1,  Qt.Key_2: 2,  Qt.Key_3: 3,
    Qt.Key_4: 4,  Qt.Key_5: 5,  Qt.Key_6: 6,  Qt.Key_7: 7,
    Qt.Key_8: 8,  Qt.Key_9: 9,
    Qt.Key_A: 10, Qt.Key_B: 11, Qt.Key_C: 12, Qt.Key_D: 13,
    Qt.Key_E: 14, Qt.Key_F: 15, Qt.Key_G: 16,
    Qt.Key_X: 22   # X key for delete
}

CLASS_COLORS = {
    0: '#E74C3C', 1: '#C0392B', 2: '#E67E22', 3: '#F39C12',
    4: '#F1C40F', 5: '#2ECC71', 6: '#27AE60', 7: '#1ABC9C',
    8: '#16A085', 9: '#3498DB', 10: '#2980B9', 11: '#9B59B6',
    12: '#8E44AD', 13: '#E91E63', 14: '#FF5722', 15: '#795548',
    16: '#607D8B', 22: '#FF0000' # Red for delete
}

GRID_COLS       = 3      # 3 columns
GRID_ROWS       = 3      # 3 rows
IMAGES_PER_PAGE = GRID_COLS * GRID_ROWS   # 9 per page
THUMB_W         = 260    # large thumbnails
THUMB_H         = 190    # large thumbnails


# ============================================================
# DATABASE
# ============================================================

class Database:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        # Removed _ensure_cols() call to stop adding the column

    def get_total(self, fc=None, fs=None):
        q, p = self._base_query("SELECT COUNT(*)", fc, fs)
        return self.conn.execute(q, p).fetchone()[0]

    def get_page(self, offset, limit, fc=None, fs=None):
        # We calculate "reviewed" on the fly: if new_class_name IS NOT NULL then 1 else 0
        q, p = self._base_query(
            "SELECT id, class_id, class_name, conf, "
            "new_class_name, new_class_id, "
            "(CASE WHEN new_class_name IS NOT NULL THEN 1 ELSE 0 END) as reviewed, "
            "imageBlob",
            fc, fs
        )
        q += " ORDER BY id LIMIT ? OFFSET ?"
        p += [limit, offset]
        return self.conn.execute(q, p).fetchall()

    def _base_query(self, select, fc, fs):
        q = f"{select} FROM tracking_data WHERE imageBlob IS NOT NULL"
        p = []
        if fc and fc != 'All':
            q += (" AND (new_class_name=? "
                  "OR (new_class_name IS NULL AND class_name=?))")
            p += [fc, fc]
        
        # Filter logic changed to check presence of new_class_name instead of a column
        if fs == 'Reviewed':
            q += " AND new_class_name IS NOT NULL"
        elif fs == 'Pending':
            q += " AND new_class_name IS NULL"
        return q, p

    def update_label(self, row_id, class_id, class_name):
        # Removed "reviewed=1" from the update query
        self.conn.execute(
            "UPDATE tracking_data "
            "SET new_class_id=?, new_class_name=? "
            "WHERE id=?",
            (class_id, class_name, row_id)
        )
        self.conn.commit()

    def get_reviewed_count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM tracking_data WHERE new_class_name IS NOT NULL"
        ).fetchone()[0]

    def get_classes(self):
        rows = self.conn.execute(
            "SELECT DISTINCT COALESCE(new_class_name,class_name) "
            "FROM tracking_data ORDER BY 1"
        ).fetchall()
        db_classes = set(r[0] for r in rows if r[0])
        all_classes = db_classes.union(set(CLASS_MAP.values()))
        return ['All'] + sorted(list(all_classes))

    def close(self):
        if self.conn:
            self.conn.close()


def blob_to_pixmap(blob, w, h):
    try:
        img = QImage()
        img.loadFromData(blob)
        px = QPixmap.fromImage(img)
        return px.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        return None


# ============================================================
# THUMBNAIL CARD  —  large, keyboard-selectable
# ============================================================

class Card(QFrame):
    UNSELECTED_STYLE = """
        Card {{
            background: #1E1E2E;
            border: 2px solid {border};
            border-radius: 10px;
        }}
    """
    SELECTED_STYLE = """
        Card {{
            background: #2A2840;
            border: 4px solid #F5C542;
            border-radius: 10px;
        }}
    """

    def __init__(self, idx, click_cb, parent=None):
        super().__init__(parent)
        self.idx       = idx
        self.click_cb  = click_cb
        self.row_id    = None
        self.selected  = False
        self.reviewed  = False

        # Fixed size: image + labels below
        self.setFixedSize(THUMB_W + 20, THUMB_H + 70)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Image
        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(THUMB_W, THUMB_H)
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self.img_lbl.setStyleSheet(
            "background:#11111B; border-radius:6px; color:#555;"
        )
        layout.addWidget(self.img_lbl)

        # Row ID
        self.id_lbl = QLabel()
        self.id_lbl.setAlignment(Qt.AlignCenter)
        self.id_lbl.setStyleSheet("color:#6C7086; font-size:11px;")
        layout.addWidget(self.id_lbl)

        # Class label (large, clearly readable)
        self.cls_lbl = QLabel()
        self.cls_lbl.setAlignment(Qt.AlignCenter)
        self.cls_lbl.setWordWrap(True)
        self.cls_lbl.setStyleSheet(
            "color:#CDD6F4; font-size:13px; font-weight:bold;"
        )
        layout.addWidget(self.cls_lbl)

        # Hint shown only when selected
        self.hint_lbl = QLabel()
        self.hint_lbl.setAlignment(Qt.AlignCenter)
        self.hint_lbl.setStyleSheet(
            "color:#F5C542; font-size:10px;"
        )
        layout.addWidget(self.hint_lbl)

        self._apply_style()

    def _apply_style(self):
        if self.selected:
            self.setStyleSheet(self.SELECTED_STYLE)
        else:
            color = '#A6E3A1' if self.reviewed else '#313244'
            self.setStyleSheet(self.UNSELECTED_STYLE.format(border=color))

    def set_data(self, row_id, pixmap, class_name, reviewed):
        self.row_id   = row_id
        self.reviewed = bool(reviewed)
        if pixmap:
            self.img_lbl.setPixmap(pixmap)
        else:
            self.img_lbl.setText("no image")
        self.id_lbl.setText(f"ID: {row_id}")
        self.cls_lbl.setText(class_name or "Unknown")
        self._apply_style()

    def set_selected(self, sel):
        self.selected = sel
        self._apply_style()
        self.hint_lbl.setText(
            "▶  press key to classify" if sel else ""
        )

    def mark_classified(self, class_name, color):
        self.cls_lbl.setText(class_name)
        self.cls_lbl.setStyleSheet(
            f"color:{color}; font-size:13px; font-weight:bold;"
        )
        self.reviewed = True
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_cb(self.idx)


# ============================================================
# ZOOM DIALOG  —  optional detail view (Enter key)
# ============================================================

class ZoomDialog(QDialog):
    def __init__(self, rows, idx, db, on_save, parent=None):
        super().__init__(parent)
        self.rows    = rows
        self.idx     = idx
        self.db      = db
        self.on_save = on_save
        self.setWindowTitle("Zoom View  —  Press key to classify, Esc to close")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(
            "QDialog, QLabel { background:#11111B; color:#CDD6F4; }"
        )
        self._build()
        self._load()

    def _build(self):
        L = QVBoxLayout(self)
        L.setSpacing(10)
        L.setContentsMargins(20, 16, 20, 16)

        # Nav + ID row
        top = QHBoxLayout()
        self.nav_lbl = QLabel()
        self.nav_lbl.setStyleSheet(
            "color:#89B4FA; font-size:14px; font-weight:bold;"
        )
        self.id_lbl = QLabel()
        self.id_lbl.setStyleSheet("color:#6C7086; font-size:12px;")
        top.addWidget(self.nav_lbl)
        top.addStretch()
        top.addWidget(self.id_lbl)
        L.addLayout(top)

        # Large image
        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self.img_lbl.setMinimumHeight(380)
        self.img_lbl.setStyleSheet(
            "background:#1E1E2E; border-radius:12px; padding:10px;"
        )
        L.addWidget(self.img_lbl)

        # Current label
        self.cur_lbl = QLabel()
        self.cur_lbl.setAlignment(Qt.AlignCenter)
        self.cur_lbl.setStyleSheet(
            "color:#F9E2AF; font-size:15px; font-weight:bold;"
        )
        L.addWidget(self.cur_lbl)

        # Class buttons grid
        bf = QFrame()
        bf.setStyleSheet(
            "background:#1E1E2E; border-radius:10px; padding:8px;"
        )
        bg = QGridLayout(bf)
        bg.setSpacing(5)
        
        # Keys reference
        all_keys = list('0123456789ABCDEFG') + ['X']
        for i, (cid, cn) in enumerate(CLASS_MAP.items()):
            k   = all_keys[i] if i < len(all_keys) else '?'
            col = CLASS_COLORS.get(cid, '#89B4FA')
            b   = QPushButton(f"[{k}]  {cn}")
            b.setFixedHeight(30)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:#313244; color:#CDD6F4;
                    border:1px solid {col}; border-radius:6px;
                    font-size:11px; padding:2px 6px;
                }}
                QPushButton:hover {{
                    background:{col}; color:#11111B; font-weight:bold;
                }}
            """)
            b.clicked.connect(lambda _, c=cid: self._assign(c))
            bg.addWidget(b, i // 6, i % 6)
        L.addWidget(bf)

        # Nav buttons
        nav = QHBoxLayout()
        self.pb = QPushButton("◀  Prev  [←]")
        self.nb = QPushButton("Next  ▶  [→]")
        cb      = QPushButton("Close  [Esc]")
        for b, col in [(self.pb,'#89B4FA'), (self.nb,'#89B4FA'),
                       (cb,'#F38BA8')]:
            b.setFixedHeight(34)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:#1E1E2E; color:{col};
                    border:1px solid {col}; border-radius:8px;
                    font-size:12px; padding:4px 18px;
                }}
                QPushButton:hover {{ background:{col}; color:#11111B; }}
                QPushButton:disabled {{ color:#45475A; border-color:#313244; }}
            """)
        self.pb.clicked.connect(self._prev)
        self.nb.clicked.connect(self._next)
        cb.clicked.connect(self.close)
        nav.addWidget(self.pb)
        nav.addStretch()
        nav.addWidget(cb)
        nav.addStretch()
        nav.addWidget(self.nb)
        L.addLayout(nav)

    def _load(self):
        if not self.rows or self.idx >= len(self.rows):
            return
        row  = self.rows[self.idx]
        name = row['new_class_name'] or row['class_name'] or 'Unknown'
        blob = row['imageBlob']
        self.nav_lbl.setText(f"Image {self.idx+1} of {len(self.rows)}")
        self.id_lbl.setText(f"DB ID: {row['id']}")
        self.cur_lbl.setText(f"Current label:  {name}")
        if blob:
            px = blob_to_pixmap(blob, 520, 380)
            self.img_lbl.setPixmap(px) if px else self.img_lbl.setText("No image")
        self.pb.setEnabled(self.idx > 0)
        self.nb.setEnabled(self.idx < len(self.rows) - 1)

    def _assign(self, cid):
        row  = self.rows[self.idx]
        name = CLASS_MAP[cid]
        self.db.update_label(row['id'], cid, name)
        self.on_save(row['id'], cid)
        self.cur_lbl.setText(f"✓  Saved:  {name}")
        self.cur_lbl.setStyleSheet(
            "color:#A6E3A1; font-size:15px; font-weight:bold;"
        )
        QTimer.singleShot(280, self._next)

    def _prev(self):
        if self.idx > 0:
            self.idx -= 1
            self._load()

    def _next(self):
        if self.idx < len(self.rows) - 1:
            self.idx += 1
            self._load()
        else:
            self.close()

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.close()
        elif k == Qt.Key_Left:
            self._prev()
        elif k == Qt.Key_Right:
            self._next()
        elif k in KEY_MAP:
            self._assign(KEY_MAP[k])


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Reclassification Tool  —  Keyboard Edition")
        self.setMinimumSize(1100, 900)

        self.db           = None
        self.current_page = 0
        self.current_rows = []
        self.selected_idx = 0
        self.undo_stack   = []   # (row_id, old_class_id, old_class_name)
        self.total_pages  = 1

        self.setStyleSheet("""
            QMainWindow, QWidget { background:#11111B; color:#CDD6F4; }
            QScrollArea { border:none; background:#11111B; }
            QComboBox {
                background:#1E1E2E; color:#CDD6F4;
                border:1px solid #45475A; border-radius:6px;
                padding:4px 10px; font-size:12px; min-width:130px;
            }
            QComboBox QAbstractItemView {
                background:#1E1E2E; color:#CDD6F4;
                selection-background-color:#313244;
            }
            QStatusBar { background:#181825; color:#89B4FA; font-size:12px; }
            QProgressBar {
                background:#313244; border:none;
                border-radius:4px; height:8px; color:transparent;
            }
            QProgressBar::chunk { background:#A6E3A1; border-radius:4px; }
        """)

        self._build_ui()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    # ── UI BUILD ──────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(8)

        # ── Header row ────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Vehicle Reclassification")
        title.setStyleSheet(
            "color:#CDD6F4; font-size:18px; font-weight:bold;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        self.open_btn = QPushButton("Open Database  [O]")
        self.open_btn.setFixedHeight(32)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background:#313244; color:#89B4FA;
                border:1px solid #89B4FA; border-radius:8px;
                font-size:12px; padding:3px 16px; font-weight:bold;
            }
            QPushButton:hover { background:#89B4FA; color:#11111B; }
        """)
        self.open_btn.clicked.connect(self._open_db)
        hdr.addWidget(self.open_btn)

        self.db_lbl = QLabel("No database loaded")
        self.db_lbl.setStyleSheet(
            "color:#6C7086; font-size:11px;"
            "background:#1E1E2E; border-radius:6px; padding:4px 10px;"
        )
        hdr.addWidget(self.db_lbl)
        root.addLayout(hdr)

        # ── Progress bar ──────────────────────────────────────
        prow = QHBoxLayout()
        self.prog_lbl = QLabel("Open a database to begin")
        self.prog_lbl.setStyleSheet("color:#A6E3A1; font-size:12px;")
        prow.addWidget(self.prog_lbl)
        prow.addStretch()
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedWidth(280)
        self.prog_bar.setFixedHeight(8)
        prow.addWidget(self.prog_bar)
        root.addLayout(prow)

        # ── Filter row ────────────────────────────────────────
        frow = QHBoxLayout()
        frow.addWidget(QLabel("Filter class:"))
        self.cls_cb = QComboBox()
        self.cls_cb.addItem('All')
        self.cls_cb.currentTextChanged.connect(self._on_filter)
        frow.addWidget(self.cls_cb)

        frow.addWidget(QLabel("Status:"))
        self.sts_cb = QComboBox()
        self.sts_cb.addItems(['All', 'Pending', 'Reviewed'])
        self.sts_cb.currentTextChanged.connect(self._on_filter)
        frow.addWidget(self.sts_cb)

        frow.addStretch()

        # Compact keyboard legend
        legend = QLabel(
            "Arrows = move   |   0-9/A-G = classify   |   X = DELETE   |   "
            "] = next page   |   [ = prev page   |   "
            "Home/End = first/last page   |   U = undo   |   "
            "Enter = zoom   |   Q = quit"
        )
        legend.setStyleSheet(
            "color:#6C7086; font-size:11px;"
            "background:#1E1E2E; border-radius:6px; padding:5px 10px;"
        )
        frow.addWidget(legend)
        root.addLayout(frow)

        # ── Class shortcut reference strip ────────────────────
        ref = QFrame()
        ref.setStyleSheet(
            "background:#1A1A2A; border-radius:8px;"
        )
        ref_layout = QHBoxLayout(ref)
        ref_layout.setSpacing(4)
        ref_layout.setContentsMargins(8, 5, 8, 5)
        
        shortcut_keys = list('0123456789ABCDEFG') + ['X']
        for i, (cid, cn) in enumerate(CLASS_MAP.items()):
            k   = shortcut_keys[i] if i < len(shortcut_keys) else '?'
            col = CLASS_COLORS.get(cid, '#89B4FA')
            # Short name for the strip
            short = cn.replace('Rickshaw ', 'R.').replace(
                'Animal Drawn Vehicle', 'Animal').replace(
                'Power Tiller', 'P.Tiller').replace('Delete / Trash', 'DEL')
            lbl = QLabel(f"[{k}] {short}")
            lbl.setStyleSheet(
                f"color:{col}; font-size:10px; font-weight:bold;"
                f"background:#1E1E2E; border:1px solid {col};"
                f"border-radius:4px; padding:2px 5px;"
            )
            ref_layout.addWidget(lbl)
        ref_layout.addStretch()
        root.addWidget(ref)

        # ── Grid area (3×3) ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gw = QWidget()
        self.grid = QGridLayout(gw)
        self.grid.setSpacing(14)
        self.grid.setContentsMargins(6, 6, 6, 6)
        scroll.setWidget(gw)
        root.addWidget(scroll, stretch=1)

        self.cards = []
        for i in range(IMAGES_PER_PAGE):
            c = Card(i, self._on_card_click)
            c.hide()
            self.cards.append(c)
            self.grid.addWidget(c, i // GRID_COLS, i % GRID_COLS)

        # ── Pagination row ────────────────────────────────────
        page_row = QHBoxLayout()

        btn_style = """
            QPushButton {
                background:#1E1E2E; color:#CDD6F4;
                border:1px solid #45475A; border-radius:8px;
                font-size:12px; padding:4px 16px;
            }
            QPushButton:hover { background:#89B4FA; color:#11111B; font-weight:bold; }
            QPushButton:disabled { color:#45475A; border-color:#313244; }
        """

        self.first_btn = QPushButton("⏮  First  [Home]")
        self.prev_btn  = QPushButton("◀  Prev  [[]")
        self.next_btn  = QPushButton("Next  ▶  []]")
        self.last_btn  = QPushButton("Last  ⏭  [End]")

        for b in [self.first_btn, self.prev_btn,
                  self.next_btn, self.last_btn]:
            b.setFixedHeight(34)
            b.setEnabled(False)
            b.setStyleSheet(btn_style)

        self.first_btn.clicked.connect(self._first_page)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        self.last_btn.clicked.connect(self._last_page)

        self.page_lbl = QLabel("")
        self.page_lbl.setAlignment(Qt.AlignCenter)
        self.page_lbl.setStyleSheet(
            "color:#89B4FA; font-size:13px; font-weight:bold;"
        )

        page_row.addWidget(self.first_btn)
        page_row.addWidget(self.prev_btn)
        page_row.addStretch()
        page_row.addWidget(self.page_lbl)
        page_row.addStretch()
        page_row.addWidget(self.next_btn)
        page_row.addWidget(self.last_btn)
        root.addLayout(page_row)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(
            "Press O to open a database, or click 'Open Database'"
        )

    # ── DATABASE ──────────────────────────────────────────────

    def _open_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Vehicle Database", "",
            "Database Files (*.db4 *.db *.sqlite *.sqlite3);;All Files (*)"
        )
        if not path:
            return
        if self.db:
            self.db.close()
        try:
            self.db = Database(path)
            name    = os.path.basename(path)
            self.db_lbl.setText(f"{name}")
            self.db_lbl.setStyleSheet(
                "color:#A6E3A1; font-size:11px;"
                "background:#1E1E2E; border-radius:6px; padding:4px 10px;"
            )
            self.cls_cb.blockSignals(True)
            self.cls_cb.clear()
            self.cls_cb.addItems(self.db.get_classes())
            self.cls_cb.blockSignals(False)
            self.current_page = 0
            self.selected_idx = 0
            self.undo_stack.clear()
            self._load_page()
            self.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open:\n{e}")

    # ── PAGE LOAD ─────────────────────────────────────────────

    def _load_page(self):
        if not self.db:
            return
        fc    = self.cls_cb.currentText()
        fs    = self.sts_cb.currentText()
        total = self.db.get_total(fc, fs)
        rows  = self.db.get_page(
            self.current_page * IMAGES_PER_PAGE,
            IMAGES_PER_PAGE, fc, fs
        )
        self.current_rows = [dict(row) for row in rows]
        self.total_pages  = max(1, (total + IMAGES_PER_PAGE - 1) // IMAGES_PER_PAGE)

        for c in self.cards:
            c.hide()

        for i, row in enumerate(rows):
            c    = self.cards[i]
            blob = row['imageBlob']
            name = row['new_class_name'] or row['class_name'] or 'Unknown'
            px   = blob_to_pixmap(blob, THUMB_W, THUMB_H) if blob else None
            c.set_data(row['id'], px, name, bool(row['reviewed']))
            c.set_selected(i == self.selected_idx)
            c.show()

        self.page_lbl.setText(
            f"Page  {self.current_page + 1}  /  {self.total_pages}"
            f"   ({total:,} images)"
        )

        at_first = self.current_page == 0
        at_last  = self.current_page >= self.total_pages - 1
        self.first_btn.setEnabled(not at_first)
        self.prev_btn.setEnabled(not at_first)
        self.next_btn.setEnabled(not at_last)
        self.last_btn.setEnabled(not at_last)

        self._update_progress()
        self._update_status()
        self.setFocus()

    def _update_progress(self):
        if not self.db:
            return
        total    = self.db.get_total()
        reviewed = self.db.get_reviewed_count()
        pct      = int(reviewed / total * 100) if total > 0 else 0
        self.prog_lbl.setText(
            f"Reviewed: {reviewed:,} / {total:,}  ({pct}%)"
        )
        self.prog_bar.setMaximum(max(1, total))
        self.prog_bar.setValue(reviewed)

    def _update_status(self):
        if not self.current_rows or self.selected_idx >= len(self.current_rows):
            return
        row  = self.current_rows[self.selected_idx]
        name = row['new_class_name'] or row['class_name'] or 'Unknown'
        self.status.showMessage(
            f"Selected: ID {row['id']}  |  Label: {name}"
            f"  |  Press 0-9 / A-G to classify  |  X = DELETE  |  U = undo"
        )

    # ── SELECTION ─────────────────────────────────────────────

    def _select(self, idx):
        n = len(self.current_rows)
        if idx < 0 or idx >= n:
            return
        if 0 <= self.selected_idx < len(self.cards):
            self.cards[self.selected_idx].set_selected(False)
        self.selected_idx = idx
        self.cards[idx].set_selected(True)
        self._update_status()

    def _on_card_click(self, idx):
        self._select(idx)
        self.setFocus()

    # ── CLASSIFY ──────────────────────────────────────────────

    def _classify_selected(self, class_id):
        if not self.current_rows:
            return
        idx = self.selected_idx
        if idx >= len(self.current_rows):
            return

        row      = self.current_rows[idx]
        new_name = CLASS_MAP[class_id]
        old_id   = row['new_class_id']
        old_name = row['new_class_name'] or row['class_name']

        # Save undo state
        self.undo_stack.append((row['id'], old_id, old_name))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

        # Write to DB
        self.db.update_label(row['id'], class_id, new_name)

        # Update card visually (no reload needed)
        color = CLASS_COLORS.get(class_id, '#CDD6F4')
        self.cards[idx].mark_classified(new_name, color)

        # Update local row cache
        self.current_rows[idx]['new_class_id']   = class_id
        self.current_rows[idx]['new_class_name']  = new_name
        self.current_rows[idx]['reviewed']        = 1

        self.status.showMessage(
            f"✓  ID {row['id']}  →  {new_name}  "
            f"  (U to undo)  |  Moving to next image...",
            2000
        )
        self._update_progress()

        # Auto-advance
        next_idx = idx + 1
        if next_idx < len(self.current_rows):
            QTimer.singleShot(120, lambda: self._select(next_idx))
        elif self.current_page < self.total_pages - 1:
            QTimer.singleShot(200, self._next_page)

    # ── UNDO ──────────────────────────────────────────────────

    def _undo(self):
        if not self.undo_stack:
            self.status.showMessage("  Nothing to undo.", 2000)
            return
        row_id, old_cid, old_cname = self.undo_stack.pop()
        self.db.update_label(row_id, old_cid, old_cname)

        # Find and update card if on current page
        for i, row in enumerate(self.current_rows):
            if row['id'] == row_id:
                self.current_rows[i]['new_class_id']  = old_cid
                self.current_rows[i]['new_class_name'] = old_cname
                self.current_rows[i]['reviewed']       = 0
                color = CLASS_COLORS.get(old_cid, '#CDD6F4')
                self.cards[i].mark_classified(old_cname or 'Unknown', '#CDD6F4')
                self.cards[i].reviewed = False
                self.cards[i]._apply_style()
                break

        self._update_progress()
        self.status.showMessage(
            f"  Undo — ID {row_id} restored to: {old_cname}", 2000
        )

    # ── PAGINATION ────────────────────────────────────────────

    def _first_page(self):
        self.current_page = 0
        self.selected_idx = 0
        self._load_page()

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_idx = 0
            self._load_page()

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_idx = 0
            self._load_page()

    def _last_page(self):
        self.current_page = self.total_pages - 1
        self.selected_idx = 0
        self._load_page()

    def _on_filter(self):
        self.current_page = 0
        self.selected_idx = 0
        self._load_page()

    # ── ZOOM ──────────────────────────────────────────────────

    def _open_zoom(self):
        if not self.current_rows:
            return
        dlg = ZoomDialog(
            list(self.current_rows),
            self.selected_idx,
            self.db,
            self._on_zoom_save,
            self
        )
        dlg.exec_()
        self._load_page()

    def _on_zoom_save(self, row_id, class_id):
        self._update_progress()

    # ── KEYBOARD ──────────────────────────────────────────────

    def keyPressEvent(self, event):
        k = event.key()
        n = len(self.current_rows)

        # Open DB
        if k == Qt.Key_O and not self.db:
            self._open_db()
            return

        if not self.db or n == 0:
            super().keyPressEvent(event)
            return

        # Arrow navigation
        if k == Qt.Key_Right:
            self._select(min(self.selected_idx + 1, n - 1))

        elif k == Qt.Key_Left:
            self._select(max(self.selected_idx - 1, 0))

        elif k == Qt.Key_Down:
            new = self.selected_idx + GRID_COLS
            if new < n:
                self._select(new)
            else:
                self._next_page()

        elif k == Qt.Key_Up:
            new = self.selected_idx - GRID_COLS
            if new >= 0:
                self._select(new)
            else:
                self._prev_page()

        # Page navigation — ] and [ keys
        elif k in (Qt.Key_PageDown, Qt.Key_BracketRight):
            self._next_page()

        elif k in (Qt.Key_PageUp, Qt.Key_BracketLeft):
            self._prev_page()

        elif k == Qt.Key_Home:
            self._first_page()

        elif k == Qt.Key_End:
            self._last_page()

        # Zoom (optional)
        elif k in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self._open_zoom()

        # Undo
        elif k == Qt.Key_U:
            self._undo()

        # Quit
        elif k == Qt.Key_Q:
            self.close()

        # Classify — 0-9, A-G, and X for delete
        elif k in KEY_MAP:
            self._classify_selected(KEY_MAP[k])

        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.db:
            self.db.close()
        event.accept()


# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Vehicle Reclassification Tool")

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())