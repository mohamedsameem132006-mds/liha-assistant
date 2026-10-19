from __future__ import annotations

import json
import math
import os
import platform
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QIcon, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QTextEdit, QVBoxLayout, QWidget, QProgressBar, QComboBox,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG          = "#00060a"
    PANEL       = "#010d14"
    PANEL_CARD  = "#01131f"
    PANEL_HOVER = "#011c2e"
    BORDER      = "#0d3347"
    BORDER_GLOW = "#00d4ff"
    BORDER_DIM  = "#1a5c7a"
    
    CYAN        = "#00d4ff"
    CYAN_DIM    = "#007a99"
    CYAN_GHOST  = "#001f2e"
    CYAN_HOVER  = "#00e5ff"
    
    BLUE_ACCENT = "#0088ff"
    GREEN       = "#00ff88"
    GREEN_DIM   = "#00aa55"
    RED         = "#ff3366"
    
    TEXT_MAIN   = "#8ffcff"
    TEXT_DIM    = "#3a8a9a"
    TEXT_MED    = "#5ab8cc"
    WHITE       = "#ffffff"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


# ==============================================================================
# 1. HOLOGRAPHIC CORE WIDGET (CENTERPIECE)
# ==============================================================================
class HolographicCoreWidget(QWidget):
    """Animated holographic core with per-state emotional visual feedback."""

    CALM_BLUE = "#5588cc"  # softer blue for ERROR/CONFUSED (non-alarming)

    def __init__(self, logo_path: str = "face.png", parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)

        self._state = "LISTENING"
        self._angle1 = 0.0
        self._angle2 = 0.0
        self._angle3 = 0.0
        self._pulse = 1.0
        self._pulse_dir = 0.015
        self._ring_expand = 0.0
        self._breath_phase = 0.0
        self._progress_angle = 0.0
        self._listen_ring_phase = 0.0

        self._particles = []
        for _ in range(28):
            self._particles.append({
                "angle": random.uniform(0, 2 * math.pi),
                "dist": random.uniform(65, 135),
                "speed": random.uniform(0.015, 0.045),
                "size": random.uniform(2.0, 4.2),
                "alpha": random.uniform(100, 220),
            })

        self._logo_pixmap = None
        if os.path.exists(logo_path):
            self._logo_pixmap = QPixmap(logo_path)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(33)  # ~30 FPS

    def set_state(self, state: str):
        self._state = state.upper()
        self.update()

    def _animate(self):
        st = self._state
        speed_mult = {"THINKING": 3.0, "PROCESSING": 3.0, "SPEAKING": 1.8,
                       "LISTENING": 1.2, "HAPPY": 1.5, "POSITIVE": 1.5,
                       "IDLE": 0.4, "OFFLINE": 0.1, "ERROR": 0.6,
                       "CONFUSED": 0.6}.get(st, 1.0)

        self._angle1 = (self._angle1 + 0.8 * speed_mult) % 360
        self._angle2 = (self._angle2 - 1.2 * speed_mult) % 360
        self._angle3 = (self._angle3 + 1.5 * speed_mult) % 360

        self._pulse += self._pulse_dir * (speed_mult ** 0.5)
        if self._pulse > 1.08 or self._pulse < 0.92:
            self._pulse_dir *= -1

        self._ring_expand = (self._ring_expand + 2.5) % 80
        self._breath_phase = (self._breath_phase + 0.025) % (2 * math.pi)
        self._progress_angle = (self._progress_angle + 4.0) % 360
        self._listen_ring_phase = (self._listen_ring_phase + 0.12) % (2 * math.pi)

        for p in self._particles:
            p["angle"] += p["speed"] * speed_mult
            if p["angle"] > 2 * math.pi:
                p["angle"] -= 2 * math.pi

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) / 2.0 - 20
        st = self._state

        # ---- per-state color & glow ----
        if st in ("THINKING", "PROCESSING"):
            main_color, glow_alpha = C.BLUE_ACCENT, 65
        elif st == "SPEAKING":
            main_color, glow_alpha = C.CYAN_HOVER, 75
        elif st in ("HAPPY", "POSITIVE"):
            main_color, glow_alpha = C.GREEN, 90
        elif st in ("ERROR", "CONFUSED"):
            main_color, glow_alpha = self.CALM_BLUE, 45
        elif st == "OFFLINE":
            main_color, glow_alpha = C.TEXT_DIM, 20
        elif st == "LISTENING":
            main_color, glow_alpha = C.CYAN, 70
        elif st == "IDLE":
            main_color = C.CYAN
            glow_alpha = int(35 + 20 * math.sin(self._breath_phase))
        else:
            main_color, glow_alpha = C.CYAN, 50

        # Solid cyan radial background bloom (matching user screenshot)
        rad_grad = QRadialGradient(cx, cy, radius * 1.1)
        rad_grad.setColorAt(0.0, qcol(C.CYAN, 85))
        rad_grad.setColorAt(0.55, qcol(C.CYAN_DIM, 45))
        rad_grad.setColorAt(1.0, qcol(C.BG, 0))
        painter.fillRect(self.rect(), rad_grad)

        # ==== STATE-SPECIFIC EFFECTS ====

        # SPEAKING: smooth rhythmic expanding holographic rings
        if st == "SPEAKING":
            for offset in (0, 26, 52):
                phase = (self._ring_expand + offset) % 80
                r_exp = radius * 0.5 + phase
                alpha_exp = max(0, int(180 * (1.0 - phase / 80.0)))
                painter.setPen(QPen(qcol(main_color, alpha_exp), 2))
                painter.drawEllipse(QPointF(cx, cy), r_exp, r_exp)

        # LISTENING: audio-waveform ring around the core
        if st == "LISTENING":
            wave_r = radius * 0.88
            for i in range(48):
                theta = 2 * math.pi * i / 48
                amp = 4.0 + 6.0 * abs(math.sin(theta * 3 + self._listen_ring_phase))
                r_inner = wave_r - amp * 0.5
                r_outer = wave_r + amp
                x1, y1 = cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta)
                x2, y2 = cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta)
                a = int(140 + 80 * abs(math.sin(theta * 3 + self._listen_ring_phase)))
                painter.setPen(QPen(qcol(C.CYAN, min(255, a)), 2))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # PROCESSING: circular progress arc + data-stream trailing dots
        if st == "PROCESSING":
            arc_r = int(radius * 0.95)
            painter.setPen(QPen(qcol(C.BLUE_ACCENT, 200), 3))
            painter.drawArc(int(cx - arc_r), int(cy - arc_r),
                            arc_r * 2, arc_r * 2,
                            int(self._progress_angle * 16), 120 * 16)
            for k in range(6):
                dot_a = math.radians(self._progress_angle - k * 20)
                dx, dy = cx + arc_r * math.cos(dot_a), cy - arc_r * math.sin(dot_a)
                sz = max(1.0, 3.5 - k * 0.4)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(qcol(C.BLUE_ACCENT, max(40, 200 - k * 30)))
                painter.drawEllipse(QPointF(dx, dy), sz, sz)

        # ERROR / CONFUSED: calm warning ripple (soft blue, not alarming)
        if st in ("ERROR", "CONFUSED"):
            ripple_r = radius * 0.6 + self._ring_expand * 0.6
            ripple_a = max(0, int(100 * (1.0 - self._ring_expand / 80.0)))
            painter.setPen(QPen(qcol(self.CALM_BLUE, ripple_a), 1.5, Qt.PenStyle.DashLine))
            painter.drawEllipse(QPointF(cx, cy), ripple_r, ripple_r)

        # IDLE: gentle outer breathing ring
        if st == "IDLE":
            breath_r = radius * 0.85 + 5 * math.sin(self._breath_phase)
            breath_a = int(60 + 30 * math.sin(self._breath_phase))
            painter.setPen(QPen(qcol(C.CYAN_DIM, breath_a), 1.5))
            painter.drawEllipse(QPointF(cx, cy), breath_r, breath_r)

        # Orbiting Data Particles
        if st in ("THINKING", "PROCESSING", "HAPPY", "POSITIVE", "LISTENING", "SPEAKING"):
            for p in self._particles:
                px = cx + p["dist"] * math.cos(p["angle"])
                py = cy + p["dist"] * math.sin(p["angle"])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(qcol(main_color, int(p["alpha"])))
                painter.drawEllipse(QPointF(px, py), p["size"], p["size"])

        # ==== CONCENTRIC TECH RINGS (matching user screenshot) ====
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle1)
        painter.setPen(QPen(qcol(main_color, 180), 2, Qt.PenStyle.DashLine))
        painter.drawEllipse(QPointF(0, 0), radius * 0.9, radius * 0.9)
        painter.restore()

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle2)
        painter.setPen(QPen(qcol(C.CYAN_HOVER, 220), 1.5, Qt.PenStyle.DotLine))
        painter.drawEllipse(QPointF(0, 0), radius * 0.78, radius * 0.78)
        painter.restore()

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle3)
        painter.setPen(QPen(qcol(main_color, 200), 2.5))
        for a in [0, 90, 180, 270]:
            painter.drawArc(
                int(-radius * 0.65), int(-radius * 0.65),
                int(radius * 1.3), int(radius * 1.3),
                a * 16, 45 * 16,
            )
        painter.restore()

        # ==== CENTER HOLOGRAPHIC EMBLEM LOGO ====
        logo_radius = radius * 0.52 * self._pulse

        # 1. Cyan Glow Base Disc (matching user screenshot)
        painter.save()
        glass_grad = QRadialGradient(cx, cy, logo_radius)
        glass_grad.setColorAt(0.0, qcol("#00c4f0", 210))
        glass_grad.setColorAt(0.7, qcol("#0088aa", 170))
        glass_grad.setColorAt(1.0, qcol("#004455", 130))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glass_grad)
        painter.drawEllipse(QPointF(cx, cy), logo_radius, logo_radius)
        painter.restore()

        # 2. Draw LIHA Emblem / Text
        if self._logo_pixmap and not self._logo_pixmap.isNull():
            painter.save()
            painter.translate(cx, cy)
            path = QPainterPath()
            path.addEllipse(QPointF(0, 0), logo_radius - 2, logo_radius - 2)
            painter.setClipPath(path)
            scaled = self._logo_pixmap.scaled(
                int(logo_radius * 2), int(logo_radius * 2),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(int(-logo_radius), int(-logo_radius), scaled)
            painter.restore()
        else:
            painter.save()
            font = QFont("Segoe UI", int(logo_radius * 0.38), QFont.Weight.Black)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
            painter.setFont(font)
            text_rect = QRectF(cx - logo_radius, cy - logo_radius, logo_radius * 2, logo_radius * 2)

            painter.setPen(qcol("#000000", 220))
            painter.drawText(text_rect.translated(1.5, 1.5), Qt.AlignmentFlag.AlignCenter, "LIHA")

            painter.setPen(qcol("#ffffff", 255))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "LIHA")
            painter.restore()

        # 3. Inner Ring & Center Rim Ring (Crisp Neon Boundary)
        painter.save()
        glow_pen = QPen(qcol(main_color, 140), 3)
        painter.setPen(glow_pen)
        painter.drawEllipse(QPointF(cx, cy), logo_radius + 1, logo_radius + 1)

        rim_pen = QPen(qcol(C.CYAN_HOVER, 255), 2)
        painter.setPen(rim_pen)
        painter.drawEllipse(QPointF(cx, cy), logo_radius, logo_radius)
        painter.restore()

        # OFFLINE: dim overlay
        if st == "OFFLINE":
            painter.fillRect(self.rect(), qcol(C.BG, 120))


# ==============================================================================
# 2. AUDIO WAVEFORM VISUALIZER WIDGET
# ==============================================================================
class AudioWaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(24)
        self._active = True
        self._bars = [0.2] * 16
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(80)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def _animate(self):
        if self._active:
            self._bars = [random.uniform(0.25, 0.95) for _ in range(16)]
        else:
            self._bars = [0.15] * 16
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        n = len(self._bars)
        bar_w = 3
        spacing = (w - (n * bar_w)) / (n + 1)

        color = qcol(C.GREEN, 230) if self._active else qcol(C.RED, 180)

        for i, val in enumerate(self._bars):
            bar_h = max(4.0, h * val)
            x = spacing + i * (bar_w + spacing)
            y = (h - bar_h) / 2.0
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.5, 1.5)


# ==============================================================================
# 3. FILE DROP ZONE WIDGET
# ==============================================================================
class DropZoneWidget(QFrame):
    fileDropped = pyqtSignal(str)
    fileCleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._current_file = None
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL_CARD};
                border: 1.5px dashed {C.CYAN_DIM};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {C.CYAN};
                background: {C.PANEL_HOVER};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = QLabel("☁️")
        self._icon_lbl.setFont(QFont("Segoe UI", 22))
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(f"color: {C.CYAN}; background: transparent; border: none;")

        self._text_row = QHBoxLayout()
        self._text_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_row.setSpacing(6)

        self._text_lbl = QLabel("Drag & drop files here or click to browse")
        self._text_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_lbl.setStyleSheet(f"color: {C.TEXT_MAIN}; background: transparent; border: none;")

        self._btn_cancel = QPushButton("✕")
        self._btn_cancel.setFixedSize(22, 22)
        self._btn_cancel.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._btn_cancel.setToolTip("Cancel / Remove selected screenshot or file")
        self._btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: #330011; color: {C.RED};
                border: 1px solid {C.RED}; border-radius: 11px;
            }}
            QPushButton:hover {{
                background: {C.RED}; color: {C.WHITE};
            }}
        """)
        self._btn_cancel.clicked.connect(self.clear_file)
        self._btn_cancel.hide()

        self._text_row.addWidget(self._text_lbl)
        self._text_row.addWidget(self._btn_cancel)

        self._sub_lbl = QLabel("Supports: Images • Videos • PDF • Docs • Code • Others")
        self._sub_lbl.setFont(QFont("Segoe UI", 8))
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")

        layout.addWidget(self._icon_lbl)
        layout.addLayout(self._text_row)
        layout.addWidget(self._sub_lbl)

    def current_file(self) -> str | None:
        return self._current_file

    def set_file(self, fpath: str):
        self._current_file = fpath
        fname = os.path.basename(fpath)
        fsize = ""
        try:
            sz = os.path.getsize(fpath)
            fsize = f" ({sz / 1024:.1f} KB)"
        except Exception:
            pass
        self._text_lbl.setText(f"📄 {fname}{fsize}")
        self._text_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        self._icon_lbl.setText("✅")
        self._btn_cancel.show()

    def clear_file(self):
        self._current_file = None
        self._text_lbl.setText("Drag & drop files here or click to browse")
        self._text_lbl.setStyleSheet(f"color: {C.TEXT_MAIN}; background: transparent; border: none;")
        self._icon_lbl.setText("☁️")
        self._btn_cancel.hide()
        self.fileCleared.emit()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            fpath = urls[0].toLocalFile()
            if fpath:
                self.set_file(fpath)
                self.fileDropped.emit(fpath)

    def mousePressEvent(self, event):
        if self._btn_cancel.isVisible() and self._btn_cancel.geometry().contains(event.pos()):
            return
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Select File for LIHA", "",
            "All Files (*.*);;Images (*.png *.jpg *.jpeg *.webp);;Documents (*.pdf *.txt *.md *.py *.js)"
        )
        if fpath:
            self.set_file(fpath)
            self.fileDropped.emit(fpath)


# ==============================================================================
# 4. SYSTEM METRICS MONITOR THREAD
# ==============================================================================
class SystemMetricsThread(QObject):
    metricsUpdated = pyqtSignal(float, float, float)

    def __init__(self):
        super().__init__()
        self._running = True
        self._last_net = psutil.net_io_counters()

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                
                now_net = psutil.net_io_counters()
                net_bytes = (now_net.bytes_sent + now_net.bytes_recv) - (self._last_net.bytes_sent + self._last_net.bytes_recv)
                self._last_net = now_net
                net_kb = max(0.0, net_bytes / 1024.0 / 1.5)
                
                self.metricsUpdated.emit(cpu, mem, net_kb)
            except Exception:
                pass
            time.sleep(1.5)


# ==============================================================================
# 5. MAIN LIHA INTERFACE WINDOW
# ==============================================================================
class MainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)

    def __init__(self, logo_path: str = "face.png"):
        super().__init__()
        self._logo_path = logo_path
        self._muted     = False
        self._ready     = True
        self.on_text_command = None
        
        # Ensure Windows Taskbar uses dedicated Liha AppUserModelID instead of python.exe
        if sys.platform == "win32":
            try:
                import ctypes
                myappid = "LihaAI.LihaAssistant.Desktop.1.0"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        icon_path = BASE_DIR / "liha_icon.ico"
        if not icon_path.exists():
            icon_path = BASE_DIR / "face.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            app = QApplication.instance()
            if app:
                app.setWindowIcon(QIcon(str(icon_path)))

        self.setWindowTitle("LIHA – AI ASSISTANT")
        self.setMinimumSize(1180, 740)
        self.resize(1280, 800)
        
        self._log_sig.connect(self._append_log_impl)
        self._state_sig.connect(self._apply_state_impl)
        
        self._init_ui()
        self._start_clock()
        self._start_metrics()

    def _init_ui(self):
        # Window dark sci-fi background styling
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {C.BG};
            }}
            QWidget {{
                color: {C.TEXT_MAIN};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QScrollBar:vertical {{
                background: {C.PANEL};
                width: 6px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.CYAN_DIM};
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C.CYAN};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # ----------------------------------------------------------------------
        # A. TOP HEADER
        # ----------------------------------------------------------------------
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 8, 14, 8)

        # Top-left: LIHA Logo & Titles
        logo_mini = QLabel()
        if os.path.exists(self._logo_path):
            logo_pix = QPixmap(self._logo_path).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_mini.setPixmap(logo_pix)
        else:
            logo_mini.setText("🔷")
            logo_mini.setFont(QFont("Segoe UI", 16))
            
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        
        t_row = QHBoxLayout()
        t_row.setSpacing(8)
        lbl_liha = QLabel("LIHA")
        lbl_liha.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_liha.setStyleSheet(f"color: {C.CYAN}; font-weight: 900; letter-spacing: 2px; border: none; background: transparent;")
        
        lbl_sub = QLabel("AI ASSISTANT")
        lbl_sub.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_sub.setStyleSheet(f"color: {C.TEXT_MED}; letter-spacing: 1px; border: none; background: transparent;")
        
        lbl_divider = QLabel("|  YOUR INTELLIGENT COMPANION")
        lbl_divider.setFont(QFont("Segoe UI", 9))
        lbl_divider.setStyleSheet(f"color: {C.TEXT_DIM}; letter-spacing: 1px; border: none; background: transparent;")

        t_row.addWidget(lbl_liha)
        t_row.addWidget(lbl_sub)
        t_row.addWidget(lbl_divider)
        t_row.addStretch()

        title_box.addLayout(t_row)

        h_layout.addWidget(logo_mini)
        h_layout.addLayout(title_box)
        h_layout.addStretch()

        # Top-right: Controls & Clock
        btn_mic_top = QPushButton("🎙")
        btn_mic_top.setFixedSize(32, 32)
        btn_mic_top.setStyleSheet(self._btn_icon_style())
        btn_mic_top.clicked.connect(self._toggle_mute)
        self._btn_mic_top = btn_mic_top

        btn_settings_top = QPushButton("⚙")
        btn_settings_top.setFixedSize(32, 32)
        btn_settings_top.setStyleSheet(self._btn_icon_style())
        btn_settings_top.clicked.connect(lambda: self._nav_stack.setCurrentIndex(5))

        btn_power_top = QPushButton("⏻")
        btn_power_top.setFixedSize(32, 32)
        btn_power_top.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL_CARD}; color: {C.RED};
                border: 1px solid {C.RED}; border-radius: 16px; font-size: 14px;
            }}
            QPushButton:hover {{ background: #330011; }}
        """)
        btn_power_top.clicked.connect(self.close)

        # Digital Clock
        clock_box = QVBoxLayout()
        clock_box.setSpacing(0)
        clock_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self._lbl_clock = QLabel("12:04:25")
        self._lbl_clock.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._lbl_clock.setStyleSheet(f"color: {C.CYAN}; border: none; background: transparent;")
        
        self._lbl_date = QLabel("Thu 17 Sep 2026")
        self._lbl_date.setFont(QFont("Segoe UI", 8))
        self._lbl_date.setStyleSheet(f"color: {C.TEXT_DIM}; border: none; background: transparent;")

        clock_box.addWidget(self._lbl_clock)
        clock_box.addWidget(self._lbl_date)

        h_layout.addWidget(btn_mic_top)
        h_layout.addWidget(btn_settings_top)
        h_layout.addWidget(btn_power_top)
        h_layout.addSpacing(12)
        h_layout.addLayout(clock_box)

        root_layout.addWidget(header)

        # ----------------------------------------------------------------------
        # B. MAIN CONTENT BODY (3 COLUMNS)
        # ----------------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)

        # ======================================================================
        # COLUMN 1: LEFT SIDEBAR
        # ======================================================================
        left_sidebar = QVBoxLayout()
        left_sidebar.setSpacing(10)

        # Navigation Panel
        nav_panel = QFrame()
        nav_panel.setFixedWidth(200)
        nav_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(8, 12, 8, 12)
        nav_layout.setSpacing(6)

        self._nav_btns = []
        nav_items = [
            ("🏠  Home", 0),
            ("💬  Chat", 1),
            ("🎙️  Voice", 2),
            ("📁  Files", 3),
            ("🛠️  Tools", 4),
            ("⚙️  Settings", 5),
        ]

        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setFixedHeight(38)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            btn.clicked.connect(lambda checked, i=idx: self._switch_nav(i))
            nav_layout.addWidget(btn)
            self._nav_btns.append(btn)

        self._nav_btns[0].setChecked(True)
        self._update_nav_styles()

        nav_layout.addStretch()

        # System Status Panel
        sys_panel = QFrame()
        sys_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        sys_layout = QVBoxLayout(sys_panel)
        sys_layout.setContentsMargins(12, 10, 12, 10)
        sys_layout.setSpacing(8)

        sys_title = QLabel("⚡ SYSTEM STATUS")
        sys_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        sys_title.setStyleSheet(f"color: {C.CYAN}; border: none; background: transparent;")
        sys_layout.addWidget(sys_title)

        # CPU
        self._lbl_cpu = QLabel("CPU — 32%")
        self._lbl_cpu.setFont(QFont("Segoe UI", 8))
        self._lbl_cpu.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
        self._bar_cpu = QProgressBar()
        self._bar_cpu.setFixedHeight(6)
        self._bar_cpu.setTextVisible(False)
        self._bar_cpu.setStyleSheet(self._bar_style())
        self._bar_cpu.setValue(32)

        sys_layout.addWidget(self._lbl_cpu)
        sys_layout.addWidget(self._bar_cpu)

        # Memory
        self._lbl_mem = QLabel("MEMORY — 58%")
        self._lbl_mem.setFont(QFont("Segoe UI", 8))
        self._lbl_mem.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
        self._bar_mem = QProgressBar()
        self._bar_mem.setFixedHeight(6)
        self._bar_mem.setTextVisible(False)
        self._bar_mem.setStyleSheet(self._bar_style())
        self._bar_mem.setValue(58)

        sys_layout.addWidget(self._lbl_mem)
        sys_layout.addWidget(self._bar_mem)

        # Network
        self._lbl_net = QLabel("NETWORK — 1.2 KB/s")
        self._lbl_net.setFont(QFont("Segoe UI", 8))
        self._lbl_net.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
        self._bar_net = QProgressBar()
        self._bar_net.setFixedHeight(6)
        self._bar_net.setTextVisible(False)
        self._bar_net.setStyleSheet(self._bar_style())
        self._bar_net.setValue(15)

        sys_layout.addWidget(self._lbl_net)
        sys_layout.addWidget(self._bar_net)

        # AI CORE Status
        core_box = QFrame()
        core_box.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px;
            }}
        """)
        core_layout = QHBoxLayout(core_box)
        core_layout.setContentsMargins(10, 8, 10, 8)

        core_txt_box = QVBoxLayout()
        core_txt_box.setSpacing(0)
        lbl_core_t = QLabel("AI CORE")
        lbl_core_t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_core_t.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
        
        self._lbl_core_status = QLabel("ACTIVE")
        self._lbl_core_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._lbl_core_status.setStyleSheet(f"color: {C.GREEN}; border: none;")

        core_txt_box.addWidget(lbl_core_t)
        core_txt_box.addWidget(self._lbl_core_status)

        self._lbl_core_dot = QLabel("🟢")
        self._lbl_core_dot.setFont(QFont("Segoe UI", 10))
        self._lbl_core_dot.setStyleSheet("border: none; background: transparent;")

        core_layout.addLayout(core_txt_box)
        core_layout.addStretch()
        core_layout.addWidget(self._lbl_core_dot)

        sys_layout.addWidget(core_box)

        # Online Status Footer
        lbl_online = QLabel("🟢 LIHA v1.0.0 | Online")
        lbl_online.setFont(QFont("Segoe UI", 8))
        lbl_online.setStyleSheet(f"color: {C.GREEN_DIM}; border: none; background: transparent;")

        left_sidebar.addWidget(nav_panel, 1)
        left_sidebar.addWidget(sys_panel)
        left_sidebar.addWidget(lbl_online)

        body_layout.addLayout(left_sidebar)

        # ======================================================================
        # COLUMN 2: CENTER STACKED PAGES (HOME, CHAT, VOICE, FILES, TOOLS, SETTINGS)
        # ======================================================================
        self._nav_stack = QStackedWidget()
        self._nav_stack.setStyleSheet(f"""
            QStackedWidget {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)

        # PAGE 0: HOME VIEW (Holographic Core + Quick Actions + Command Bar)
        home_page = QWidget()
        home_layout = QVBoxLayout(home_page)
        home_layout.setContentsMargins(16, 16, 16, 16)
        home_layout.setSpacing(12)

        # Center Holographic Core
        self._holo_core = HolographicCoreWidget(logo_path=self._logo_path)
        home_layout.addWidget(self._holo_core, 1)

        # Core Labels
        core_lbl_box = QVBoxLayout()
        core_lbl_box.setSpacing(2)
        core_lbl_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_c_name = QLabel("LIHA")
        lbl_c_name.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        lbl_c_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_c_name.setStyleSheet(f"color: {C.CYAN}; font-weight: 900; letter-spacing: 4px; border: none;")

        lbl_c_sub = QLabel("AI ASSISTANT")
        lbl_c_sub.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_c_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_c_sub.setStyleSheet(f"color: {C.TEXT_MED}; letter-spacing: 2px; border: none;")

        lbl_c_motto = QLabel("THINK  •  ASSIST  •  CREATE")
        lbl_c_motto.setFont(QFont("Segoe UI", 9))
        lbl_c_motto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_c_motto.setStyleSheet(f"color: {C.TEXT_DIM}; letter-spacing: 2px; border: none;")

        core_lbl_box.addWidget(lbl_c_name)
        core_lbl_box.addWidget(lbl_c_sub)
        core_lbl_box.addWidget(lbl_c_motto)

        home_layout.addLayout(core_lbl_box)

        # Quick Actions Grid (4 Glass Cards)
        qa_layout = QHBoxLayout()
        qa_layout.setSpacing(10)

        qa_items = [
            ("💬", "Chat", "Ask anything", lambda: self._switch_nav(1)),
            ("🎙️", "Voice", "Speak naturally", lambda: self._toggle_mute()),
            ("📁", "Files", "Upload & read", lambda: self._switch_nav(3)),
            ("🛠️", "Tools", "More features", lambda: self._switch_nav(4)),
        ]

        for icon, title, desc, cb in qa_items:
            card = QPushButton()
            card.setFixedHeight(64)
            card.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PANEL_CARD};
                    border: 1px solid {C.BORDER_DIM};
                    border-radius: 8px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background: {C.PANEL_HOVER};
                    border-color: {C.CYAN};
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(6, 6, 6, 6)
            c_lay.setSpacing(2)
            c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            t_lbl = QLabel(f"{icon}  {title}")
            t_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_lbl.setStyleSheet(f"color: {C.TEXT_MAIN}; border: none; background: transparent;")
            
            d_lbl = QLabel(desc)
            d_lbl.setFont(QFont("Segoe UI", 8))
            d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            d_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; border: none; background: transparent;")

            c_lay.addWidget(t_lbl)
            c_lay.addWidget(d_lbl)
            
            card.clicked.connect(cb)
            qa_layout.addWidget(card)

        home_layout.addLayout(qa_layout)

        # Bottom Command Bar
        cmd_bar = QFrame()
        cmd_bar.setFixedHeight(46)
        cmd_bar.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.CYAN_DIM};
                border-radius: 23px;
            }}
            QFrame:hover {{
                border-color: {C.CYAN};
            }}
        """)
        cmd_lay = QHBoxLayout(cmd_bar)
        cmd_lay.setContentsMargins(14, 4, 8, 4)
        cmd_lay.setSpacing(8)

        lbl_sparkle = QLabel("✨")
        lbl_sparkle.setFont(QFont("Segoe UI", 12))
        lbl_sparkle.setStyleSheet("border: none; background: transparent;")

        self._home_input = QLineEdit()
        self._home_input.setPlaceholderText("Type a command or question...")
        self._home_input.setFont(QFont("Segoe UI", 10))
        self._home_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {C.TEXT_MAIN};
            }}
        """)
        self._home_input.returnPressed.connect(self._on_home_send)

        btn_home_send = QPushButton("✈")
        btn_home_send.setFixedSize(32, 32)
        btn_home_send.setStyleSheet(f"""
            QPushButton {{
                background: {C.CYAN}; color: {C.BG};
                border: none; border-radius: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {C.CYAN_HOVER}; }}
        """)
        btn_home_send.clicked.connect(self._on_home_send)

        btn_home_mic = QPushButton("🎙")
        btn_home_mic.setFixedSize(32, 32)
        btn_home_mic.setStyleSheet(self._btn_icon_style())
        btn_home_mic.clicked.connect(self._toggle_mute)

        cmd_lay.addWidget(lbl_sparkle)
        cmd_lay.addWidget(self._home_input, 1)
        cmd_lay.addWidget(btn_home_send)
        cmd_lay.addWidget(btn_home_mic)

        home_layout.addWidget(cmd_bar)
        self._nav_stack.addWidget(home_page)

        # PAGE 1: CHAT VIEW
        chat_page = QWidget()
        chat_lay = QVBoxLayout(chat_page)
        chat_lay.setContentsMargins(14, 14, 14, 14)
        
        lbl_chat_head = QLabel("💬 LIHA CHAT CONVERSATION")
        lbl_chat_head.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_chat_head.setStyleSheet(f"color: {C.CYAN}; border: none;")
        
        self._chat_history = QTextEdit()
        self._chat_history.setReadOnly(True)
        self._chat_history.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
                padding: 10px;
                font-size: 10pt;
                color: {C.TEXT_MAIN};
            }}
        """)
        
        chat_in_row = QHBoxLayout()
        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Ask LIHA anything...")
        self._chat_input.setFixedHeight(36)
        self._chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px;
                padding: 0 10px;
                color: {C.TEXT_MAIN};
            }}
        """)
        self._chat_input.returnPressed.connect(self._on_chat_send)

        btn_chat_send = QPushButton("Send 📤")
        btn_chat_send.setFixedHeight(36)
        btn_chat_send.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_chat_send.setStyleSheet(f"""
            QPushButton {{
                background: {C.CYAN}; color: {C.BG};
                border: none; border-radius: 6px; padding: 0 14px;
            }}
            QPushButton:hover {{ background: {C.CYAN_HOVER}; }}
        """)
        btn_chat_send.clicked.connect(self._on_chat_send)

        chat_in_row.addWidget(self._chat_input, 1)
        chat_in_row.addWidget(btn_chat_send)

        chat_lay.addWidget(lbl_chat_head)
        chat_lay.addWidget(self._chat_history, 1)
        chat_lay.addLayout(chat_in_row)
        self._nav_stack.addWidget(chat_page)

        # PAGE 2: VOICE VIEW
        voice_page = QWidget()
        voice_lay = QVBoxLayout(voice_page)
        voice_lay.setContentsMargins(16, 16, 16, 16)
        voice_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_v_title = QLabel("🎙️ REAL-TIME VOICE COMMAND")
        lbl_v_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_v_title.setStyleSheet(f"color: {C.CYAN}; border: none;")
        
        self._voice_status_lbl = QLabel("MICROPHONE ACTIVE — LISTENING")
        self._voice_status_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._voice_status_lbl.setStyleSheet(f"color: {C.GREEN}; border: none;")

        self._large_wave = AudioWaveformWidget()
        self._large_wave.setFixedSize(300, 60)

        btn_v_toggle = QPushButton("Toggle Microphone 🎙")
        btn_v_toggle.setFixedSize(200, 42)
        btn_v_toggle.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn_v_toggle.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL_CARD}; color: {C.CYAN};
                border: 1px solid {C.CYAN}; border-radius: 6px;
            }}
            QPushButton:hover {{ background: {C.PANEL_HOVER}; }}
        """)
        btn_v_toggle.clicked.connect(self._toggle_mute)

        voice_lay.addWidget(lbl_v_title, 0, Qt.AlignmentFlag.AlignCenter)
        voice_lay.addSpacing(16)
        voice_lay.addWidget(self._voice_status_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        voice_lay.addSpacing(16)
        voice_lay.addWidget(self._large_wave, 0, Qt.AlignmentFlag.AlignCenter)
        voice_lay.addSpacing(24)
        voice_lay.addWidget(btn_v_toggle, 0, Qt.AlignmentFlag.AlignCenter)
        self._nav_stack.addWidget(voice_page)

        # PAGE 3: FILES VIEW
        files_page = QWidget()
        files_lay = QVBoxLayout(files_page)
        files_lay.setContentsMargins(16, 16, 16, 16)
        
        lbl_f_title = QLabel("📁 FILE PROCESSOR & MANAGER")
        lbl_f_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_f_title.setStyleSheet(f"color: {C.CYAN}; border: none;")
        
        self._files_drop = DropZoneWidget()
        self._files_drop.fileDropped.connect(self._on_file_dropped)

        self._files_info = QTextEdit()
        self._files_info.setReadOnly(True)
        self._files_info.setPlaceholderText("Selected file details and processed analysis will appear here...")
        self._files_info.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
                padding: 10px;
                color: {C.TEXT_MAIN};
            }}
        """)

        files_lay.addWidget(lbl_f_title)
        files_lay.addWidget(self._files_drop, 1)
        files_lay.addWidget(self._files_info, 1)
        self._nav_stack.addWidget(files_page)

        # PAGE 4: TOOLS VIEW
        tools_page = QWidget()
        tools_lay = QVBoxLayout(tools_page)
        tools_lay.setContentsMargins(16, 16, 16, 16)
        
        lbl_t_title = QLabel("🛠️ LIHA ACTIVE TOOLS & CAPABILITIES")
        lbl_t_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_t_title.setStyleSheet(f"color: {C.CYAN}; border: none;")
        
        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")
        
        tools_grid_w = QWidget()
        tools_grid_lay = QVBoxLayout(tools_grid_w)
        tools_grid_lay.setSpacing(10)

        # 1. Special Interactive Card: LIHA FOOD VISION
        food_vision_card = QFrame()
        food_vision_card.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL_CARD};
                border: 1.5px solid {C.CYAN};
                border-radius: 8px;
            }}
            QFrame:hover {{
                background: {C.PANEL_HOVER};
            }}
        """)
        fv_card_lay = QVBoxLayout(food_vision_card)
        fv_card_lay.setContentsMargins(14, 12, 14, 12)
        
        fv_head_row = QHBoxLayout()
        lbl_fv_name = QLabel("📷 LIHA FOOD VISION")
        lbl_fv_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_fv_name.setStyleSheet(f"color: {C.CYAN}; border: none;")

        lbl_fv_tag = QLabel("SEE IT. UNDERSTAND IT. KNOW WHAT'S IN IT.")
        lbl_fv_tag.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_fv_tag.setStyleSheet(f"color: {C.GREEN}; border: none;")

        fv_head_row.addWidget(lbl_fv_name)
        fv_head_row.addStretch()
        fv_head_row.addWidget(lbl_fv_tag)

        lbl_fv_desc = QLabel("Analyze live camera or food photos to identify items, estimate serving sizes, and extract nutrition & OCR label details.")
        lbl_fv_desc.setFont(QFont("Segoe UI", 9))
        lbl_fv_desc.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")

        fv_btn_row = QHBoxLayout()
        btn_open_food_cam = QPushButton("📷 Launch Food Camera Scanner")
        btn_open_food_cam.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_open_food_cam.setStyleSheet(f"""
            QPushButton {{
                background: {C.CYAN}; color: {C.BG};
                border: none; border-radius: 5px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: {C.CYAN_HOVER}; }}
        """)
        btn_open_food_cam.clicked.connect(self._start_food_vision_camera)

        btn_upload_food_img = QPushButton("📁 Upload Food Photo")
        btn_upload_food_img.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_upload_food_img.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL_CARD}; color: {C.CYAN};
                border: 1px solid {C.CYAN}; border-radius: 5px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: {C.PANEL_HOVER}; }}
        """)
        btn_upload_food_img.clicked.connect(self._upload_food_vision_image)

        fv_btn_row.addWidget(btn_open_food_cam)
        fv_btn_row.addWidget(btn_upload_food_img)
        fv_btn_row.addStretch()

        # Food Vision Result Display Area inside Tools
        self._food_vision_display = QTextEdit()
        self._food_vision_display.setReadOnly(True)
        self._food_vision_display.setFixedHeight(180)
        self._food_vision_display.setPlaceholderText("📷 LIHA Food Vision results, OCR label details, and estimated nutrition breakdown will appear here...")
        self._food_vision_display.setStyleSheet(f"""
            QTextEdit {{
                background: {C.BG};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 9.5pt;
                color: {C.TEXT_MAIN};
            }}
        """)

        fv_card_lay.addLayout(fv_head_row)
        fv_card_lay.addWidget(lbl_fv_desc)
        fv_card_lay.addLayout(fv_btn_row)
        fv_card_lay.addWidget(self._food_vision_display)

        tools_grid_lay.addWidget(food_vision_card)

        # Standard Tool Definitions
        tool_defs = [
            ("🖥️  Screen & Vision Analyzer", "Captures desktop context and analyzes code, UI, or bugs via Gemini."),
            ("🌐  Web Search & Research", "Fetches real-time information, documentation, news, and technical solutions."),
            ("💻  Dev Agent (Autonomous Builder)", "Builds complete multi-file applications from scratch, runs code, and fixes errors."),
            ("📝  Code Helper", "Writes, edits, explains, and debugs code across Python, C++, JS, HTML/CSS."),
            ("📹  YouTube Video Analyzer", "Fetches transcripts and summarizes YouTube videos into key takeaways."),
            ("⚙️  System Controller", "Launches applications, checks system specs, controls desktop windows & settings."),
        ]

        for name, desc in tool_defs:
            t_card = QFrame()
            t_card.setStyleSheet(f"""
                QFrame {{
                    background: {C.PANEL_CARD};
                    border: 1px solid {C.BORDER_DIM};
                    border-radius: 6px;
                }}
            """)
            tc_lay = QVBoxLayout(t_card)
            tc_lay.setContentsMargins(12, 10, 12, 10)
            
            tn = QLabel(name)
            tn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tn.setStyleSheet(f"color: {C.CYAN}; border: none;")
            
            td = QLabel(desc)
            td.setFont(QFont("Segoe UI", 9))
            td.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
            
            tc_lay.addWidget(tn)
            tc_lay.addWidget(td)
            tools_grid_lay.addWidget(t_card)

        tools_scroll.setWidget(tools_grid_w)
        tools_lay.addWidget(lbl_t_title)
        tools_lay.addWidget(tools_scroll, 1)
        self._nav_stack.addWidget(tools_page)

        # PAGE 5: SETTINGS VIEW
        settings_page = QWidget()
        set_lay = QVBoxLayout(settings_page)
        set_lay.setContentsMargins(20, 20, 20, 20)
        set_lay.setSpacing(14)
        
        lbl_s_title = QLabel("⚙️ APPLICATION SETTINGS")
        lbl_s_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_s_title.setStyleSheet(f"color: {C.CYAN}; border: none;")
        
        # API Key Field
        lbl_key = QLabel("Gemini API Key:")
        lbl_key.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setFixedHeight(34)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px; padding: 0 10px; color: {C.TEXT_MAIN};
            }}
        """)
        self._load_api_key_into_settings()

        # Voice Selector
        lbl_voice = QLabel("Voice Model:")
        lbl_voice.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._combo_voice = QComboBox()
        self._combo_voice.setFixedHeight(34)
        self._combo_voice.addItems(["Aoede (Sweet Female)", "Kore (Calm Female)", "Fenrir (Deep Male)"])
        self._combo_voice.setStyleSheet(f"""
            QComboBox {{
                background: {C.PANEL_CARD}; color: {C.TEXT_MAIN};
                border: 1px solid {C.BORDER_DIM}; border-radius: 6px; padding: 0 10px;
            }}
        """)

        # Food Vision Settings Frame
        fv_set_frame = QFrame()
        fv_set_frame.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px;
            }}
        """)
        fv_set_lay = QVBoxLayout(fv_set_frame)
        fv_set_lay.setContentsMargins(14, 10, 14, 10)
        
        lbl_fv_set_t = QLabel("📷 FOOD VISION SETTINGS")
        lbl_fv_set_t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_fv_set_t.setStyleSheet(f"color: {C.CYAN}; border: none;")
        fv_set_lay.addWidget(lbl_fv_set_t)

        self._chk_fv_cam = QPushButton("Camera Access: ON")
        self._chk_fv_cam.setCheckable(True)
        self._chk_fv_cam.setChecked(True)
        self._chk_fv_cam.setFont(QFont("Segoe UI", 9))
        self._chk_fv_cam.setStyleSheet(f"QPushButton {{ background: {C.PANEL_HOVER}; color: {C.GREEN}; border: 1px solid {C.CYAN_DIM}; border-radius: 4px; padding: 4px; text-align: left; }}")
        self._chk_fv_cam.clicked.connect(lambda: self._chk_fv_cam.setText(f"Camera Access: {'ON' if self._chk_fv_cam.isChecked() else 'OFF'}"))

        self._chk_fv_auto = QPushButton("Auto Food Detection: ON")
        self._chk_fv_auto.setCheckable(True)
        self._chk_fv_auto.setChecked(True)
        self._chk_fv_auto.setFont(QFont("Segoe UI", 9))
        self._chk_fv_auto.setStyleSheet(f"QPushButton {{ background: {C.PANEL_HOVER}; color: {C.GREEN}; border: 1px solid {C.CYAN_DIM}; border-radius: 4px; padding: 4px; text-align: left; }}")
        self._chk_fv_auto.clicked.connect(lambda: self._chk_fv_auto.setText(f"Auto Food Detection: {'ON' if self._chk_fv_auto.isChecked() else 'OFF'}"))

        self._chk_fv_est = QPushButton("Show Nutrition Estimates: ON")
        self._chk_fv_est.setCheckable(True)
        self._chk_fv_est.setChecked(True)
        self._chk_fv_est.setFont(QFont("Segoe UI", 9))
        self._chk_fv_est.setStyleSheet(f"QPushButton {{ background: {C.PANEL_HOVER}; color: {C.GREEN}; border: 1px solid {C.CYAN_DIM}; border-radius: 4px; padding: 4px; text-align: left; }}")
        self._chk_fv_est.clicked.connect(lambda: self._chk_fv_est.setText(f"Show Nutrition Estimates: {'ON' if self._chk_fv_est.isChecked() else 'OFF'}"))

        self._chk_fv_voice = QPushButton("Voice Explanation: ON")
        self._chk_fv_voice.setCheckable(True)
        self._chk_fv_voice.setChecked(True)
        self._chk_fv_voice.setFont(QFont("Segoe UI", 9))
        self._chk_fv_voice.setStyleSheet(f"QPushButton {{ background: {C.PANEL_HOVER}; color: {C.GREEN}; border: 1px solid {C.CYAN_DIM}; border-radius: 4px; padding: 4px; text-align: left; }}")
        self._chk_fv_voice.clicked.connect(lambda: self._chk_fv_voice.setText(f"Voice Explanation: {'ON' if self._chk_fv_voice.isChecked() else 'OFF'}"))

        fv_set_lay.addWidget(self._chk_fv_cam)
        fv_set_lay.addWidget(self._chk_fv_auto)
        fv_set_lay.addWidget(self._chk_fv_est)
        fv_set_lay.addWidget(self._chk_fv_voice)

        btn_save_settings = QPushButton("Save Settings 💾")
        btn_save_settings.setFixedHeight(36)
        btn_save_settings.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn_save_settings.setStyleSheet(f"""
            QPushButton {{
                background: {C.CYAN}; color: {C.BG};
                border: none; border-radius: 6px;
            }}
            QPushButton:hover {{ background: {C.CYAN_HOVER}; }}
        """)
        btn_save_settings.clicked.connect(self._save_settings)

        set_lay.addWidget(lbl_s_title)
        set_lay.addWidget(lbl_key)
        set_lay.addWidget(self._key_input)
        set_lay.addWidget(lbl_voice)
        set_lay.addWidget(self._combo_voice)
        set_lay.addWidget(fv_set_frame)
        set_lay.addSpacing(10)
        set_lay.addWidget(btn_save_settings)
        set_lay.addStretch()

        self._nav_stack.addWidget(settings_page)

        body_layout.addWidget(self._nav_stack, 1)

        # ======================================================================
        # COLUMN 3: RIGHT SIDEBAR (ACTIVITY LOG, FILE UPLOAD, COMMAND INPUT)
        # ======================================================================
        right_sidebar = QVBoxLayout()
        right_sidebar.setSpacing(10)

        # 1. ACTIVITY LOG PANEL
        act_panel = QFrame()
        act_panel.setFixedWidth(300)
        act_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        act_lay = QVBoxLayout(act_panel)
        act_lay.setContentsMargins(10, 10, 10, 10)
        act_lay.setSpacing(6)

        act_head = QHBoxLayout()
        lbl_act_t = QLabel("⚡ ACTIVITY LOG")
        lbl_act_t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_act_t.setStyleSheet(f"color: {C.CYAN}; border: none;")
        
        btn_act_clear = QPushButton("Clear 🗑")
        btn_act_clear.setFont(QFont("Segoe UI", 8))
        btn_act_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM}; border: none;
            }}
            QPushButton:hover {{ color: {C.RED}; }}
        """)
        btn_act_clear.clicked.connect(self._clear_activity_log)

        act_head.addWidget(lbl_act_t)
        act_head.addStretch()
        act_head.addWidget(btn_act_clear)

        self._activity_log = QTextEdit()
        self._activity_log.setReadOnly(True)
        self._activity_log.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px;
                padding: 6px;
                font-size: 8.5pt;
                color: {C.TEXT_MAIN};
            }}
        """)
        # Pre-fill sample startup logs
        now_h = datetime.now().strftime("%H:%M")
        self._activity_log.append(f"🟢 {now_h} — LIHA is ready to assist you")
        self._activity_log.append(f"🔵 {now_h} — Voice module initialized")
        self._activity_log.append(f"🔵 {now_h} — File system ready")
        self._activity_log.append(f"🔵 {now_h} — Tools loaded (6)")
        self._activity_log.append(f"🟢 {now_h} — AI Core activated")
        self._activity_log.append(f"🟢 {now_h} — Application started")

        act_lay.addLayout(act_head)
        act_lay.addWidget(self._activity_log, 1)

        # 2. FILE UPLOAD PANEL
        drop_panel = QFrame()
        drop_panel.setFixedWidth(300)
        drop_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        dp_lay = QVBoxLayout(drop_panel)
        dp_lay.setContentsMargins(10, 10, 10, 10)
        
        lbl_dp_t = QLabel("☁️ FILE UPLOAD")
        lbl_dp_t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_dp_t.setStyleSheet(f"color: {C.CYAN}; border: none;")

        self._drop_zone = DropZoneWidget()
        self._drop_zone.fileDropped.connect(self._on_file_dropped)

        dp_lay.addWidget(lbl_dp_t)
        dp_lay.addWidget(self._drop_zone)

        # 3. COMMAND INPUT & MIC STATUS PANEL
        cmd_panel = QFrame()
        cmd_panel.setFixedWidth(300)
        cmd_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        cp_lay = QVBoxLayout(cmd_panel)
        cp_lay.setContentsMargins(10, 10, 10, 10)
        cp_lay.setSpacing(6)

        lbl_cp_t = QLabel(">_ COMMAND INPUT")
        lbl_cp_t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_cp_t.setStyleSheet(f"color: {C.CYAN}; border: none;")

        r_cmd_row = QHBoxLayout()
        self._right_input = QLineEdit()
        self._right_input.setPlaceholderText("Type a command or question...")
        self._right_input.setFont(QFont("Segoe UI", 9))
        self._right_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px; padding: 0 8px; color: {C.TEXT_MAIN};
            }}
        """)
        self._right_input.returnPressed.connect(self._on_right_send)

        btn_r_send = QPushButton("✈")
        btn_r_send.setFixedSize(30, 30)
        btn_r_send.setStyleSheet(f"""
            QPushButton {{
                background: {C.CYAN}; color: {C.BG};
                border: none; border-radius: 6px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {C.CYAN_HOVER}; }}
        """)
        btn_r_send.clicked.connect(self._on_right_send)

        r_cmd_row.addWidget(self._right_input, 1)
        r_cmd_row.addWidget(btn_r_send)

        # Mic Waveform Bar
        mic_status_box = QFrame()
        mic_status_box.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 6px;
            }}
        """)
        ms_lay = QHBoxLayout(mic_status_box)
        ms_lay.setContentsMargins(8, 4, 8, 4)

        self._lbl_mic_status = QLabel("🎙 MICROPHONE ACTIVE")
        self._lbl_mic_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._lbl_mic_status.setStyleSheet(f"color: {C.GREEN}; border: none;")

        self._wave_widget = AudioWaveformWidget()
        self._wave_widget.setFixedWidth(80)

        ms_lay.addWidget(self._lbl_mic_status)
        ms_lay.addStretch()
        ms_lay.addWidget(self._wave_widget)

        cp_lay.addWidget(lbl_cp_t)
        cp_lay.addLayout(r_cmd_row)
        cp_lay.addWidget(mic_status_box)

        right_sidebar.addWidget(act_panel, 1)
        right_sidebar.addWidget(drop_panel)
        right_sidebar.addWidget(cmd_panel)

        body_layout.addLayout(right_sidebar)

        root_layout.addLayout(body_layout, 1)

    # --------------------------------------------------------------------------
    # STYLES & HELPERS
    # --------------------------------------------------------------------------
    def _btn_icon_style(self) -> str:
        return f"""
            QPushButton {{
                background: {C.PANEL_CARD}; color: {C.CYAN};
                border: 1px solid {C.BORDER_DIM}; border-radius: 16px; font-size: 14px;
            }}
            QPushButton:hover {{ background: {C.PANEL_HOVER}; border-color: {C.CYAN}; }}
        """

    def _bar_style(self) -> str:
        return f"""
            QProgressBar {{
                background-color: {C.PANEL_CARD};
                border: 1px solid {C.BORDER_DIM};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {C.CYAN};
                border-radius: 2px;
            }}
        """

    def _switch_nav(self, idx: int):
        self._nav_stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._update_nav_styles()

    def _update_nav_styles(self):
        for i, btn in enumerate(self._nav_btns):
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.CYAN_GHOST};
                        color: {C.CYAN};
                        border: 1px solid {C.CYAN};
                        border-radius: 6px;
                        text-align: left;
                        padding-left: 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.TEXT_MED};
                        border: none;
                        border-radius: 6px;
                        text-align: left;
                        padding-left: 12px;
                    }}
                    QPushButton:hover {{
                        background: {C.PANEL_CARD};
                        color: {C.TEXT_MAIN};
                    }}
                """)

    def _start_clock(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        now = datetime.now()
        self._lbl_clock.setText(now.strftime("%H:%M:%S"))
        self._lbl_date.setText(now.strftime("%a %d %b %Y"))

    def _start_metrics(self):
        self._metrics_thread = SystemMetricsThread()
        self._metrics_thread.metricsUpdated.connect(self._on_metrics_updated)
        self._metrics_thread.start()

    def _on_metrics_updated(self, cpu: float, mem: float, net: float):
        self._lbl_cpu.setText(f"CPU — {int(cpu)}%")
        self._bar_cpu.setValue(int(cpu))

        self._lbl_mem.setText(f"MEMORY — {int(mem)}%")
        self._bar_mem.setValue(int(mem))

        self._lbl_net.setText(f"NETWORK — {net:.1f} KB/s")
        self._bar_net.setValue(min(100, int(net * 2.0)))

    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self._lbl_mic_status.setText("🔇 MICROPHONE MUTED")
            self._lbl_mic_status.setStyleSheet(f"color: {C.RED}; border: none;")
            self._wave_widget.set_active(False)
            self._btn_mic_top.setText("🔇")
            self.append_activity("SYS: Microphone muted.")
        else:
            self._lbl_mic_status.setText("🎙 MICROPHONE ACTIVE")
            self._lbl_mic_status.setStyleSheet(f"color: {C.GREEN}; border: none;")
            self._wave_widget.set_active(True)
            self._btn_mic_top.setText("🎙")
            self.append_activity("SYS: Microphone active.")

    def _on_home_send(self):
        txt = self._home_input.text().strip()
        if not txt: return
        self._home_input.clear()
        self._dispatch_text(txt)

    def _start_food_vision_camera(self):
        self._apply_state_impl("PROCESSING")
        self.append_activity("FoodVision: Accessing camera...")
        self._food_vision_display.setText("📷 LIHA FOOD VISION SCANNER\n" + "─"*40 + "\nLIHA FOOD VISION\nSCANNING...\n\nIDENTIFYING FOOD...\nREADING IMAGE...\nESTIMATING PORTION...\nCHECKING NUTRITION DATA...")
        
        def run_cam():
            try:
                import cv2
                import base64
                from actions.food_vision import analyze_food_image
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    self._apply_state_impl("ERROR")
                    self._food_vision_display.setText("⚠️ Camera Error: Could not access local camera device. Please grant camera permission or use photo upload.")
                    return
                for _ in range(5):
                    cap.read()
                ret, frame = cap.read()
                cap.release()
                if not ret or frame is None:
                    self._apply_state_impl("ERROR")
                    self._food_vision_display.setText("⚠️ Camera Error: Failed to capture camera frame. Please move closer or try photo upload.")
                    return
                _, buffer = cv2.imencode(".jpg", frame)
                img_b64 = base64.b64encode(buffer).decode("utf-8")
                res = analyze_food_image(img_b64, "image/jpeg")
                self._process_food_vision_result(res)
            except Exception as e:
                self._apply_state_impl("ERROR")
                self._food_vision_display.setText(f"⚠️ Food Vision Error: {e}")

        threading.Thread(target=run_cam, daemon=True).start()

    def _upload_food_vision_image(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Select Food Image for LIHA Food Vision", "",
            "Image Files (*.png *.jpg *.jpeg *.webp)"
        )
        if not fpath:
            return
        self._apply_state_impl("PROCESSING")
        self.append_activity(f"FoodVision: Analyzing {os.path.basename(fpath)}...")
        self._food_vision_display.setText(f"📷 LIHA FOOD VISION FILE ANALYZER\n" + "─"*40 + f"\nFile: {os.path.basename(fpath)}\n\nSCANNING...\nIDENTIFYING FOOD...\nREADING IMAGE / OCR LABELS...\nESTIMATING PORTION...")

        def run_file():
            try:
                from actions.food_vision import analyze_food_file
                res = analyze_food_file(fpath)
                self._process_food_vision_result(res)
            except Exception as e:
                self._apply_state_impl("ERROR")
                self._food_vision_display.setText(f"⚠️ Food Vision Error: {e}")

        threading.Thread(target=run_file, daemon=True).start()

    def _process_food_vision_result(self, res: dict):
        if res.get("error"):
            self._apply_state_impl("ERROR")
            err_msg = res.get("message", "I couldn't confidently identify the food from this image. Please move closer or provide a clearer photo.")
            self._food_vision_display.setText(f"⚠️ LIHA FOOD VISION\n" + "─"*40 + f"\n{err_msg}")
            return

        self._apply_state_impl("HAPPY")
        source = res.get("data_source", "ESTIMATED")
        conf = res.get("confidence", "HIGH")
        meal_type = res.get("meal_type", "SINGLE")
        items = res.get("detected_items", [])
        summary = res.get("overall_summary", {})
        voice_text = res.get("voice_text", "Food analysis complete.")

        lines = ["📷 LIHA FOOD VISION REPORT", "─"*45]
        lines.append(f"DATA SOURCE:  [{source}]   |   CONFIDENCE: {conf}")
        lines.append(f"MEAL TYPE:    {meal_type}")
        lines.append("─"*45)

        for i, item in enumerate(items, 1):
            lines.append(f"🔹 ITEM #{i}: {item.get('name', 'Food').upper()}")
            lines.append(f"   Category:          {item.get('category', 'Other')}")
            lines.append(f"   Portion / Serving: {item.get('portion', '1 serving')}")
            nut = item.get("nutrition", {})
            lines.append(f"   Calories:          {nut.get('calories', 'N/A')}  [{source}]")
            lines.append(f"   Protein:           {nut.get('protein', 'N/A')}  [{source}]")
            lines.append(f"   Carbohydrates:     {nut.get('carbohydrates', 'N/A')}  [{source}]")
            lines.append(f"   Total Fat:         {nut.get('fat', 'N/A')}  [{source}]")
            lines.append(f"   Saturated Fat:     {nut.get('saturated_fat', 'N/A')}  [{source}]")
            lines.append(f"   Fibre:             {nut.get('fibre', 'N/A')}  [{source}]")
            lines.append(f"   Sugar:             {nut.get('sugar', 'N/A')}  [{source}]")
            lines.append(f"   Sodium:            {nut.get('sodium', 'N/A')}  [{source}]")
            kn = item.get("key_nutrients", [])
            if kn:
                lines.append(f"   Key Nutrients:     {', '.join(kn)}")
            if item.get("analysis"):
                lines.append(f"   Note:              {item.get('analysis')}")
            lines.append("─"*45)

        if summary:
            lines.append(f"📊 COMBINED SUMMARY ({summary.get('title', 'Meal')})")
            lines.append(f"   Total Calories: {summary.get('total_calories', 'N/A')}")
            lines.append(f"   Total Protein:  {summary.get('total_protein', 'N/A')}")
            lines.append(f"   Total Carbs:    {summary.get('total_carbs', 'N/A')}")
            lines.append(f"   Total Fat:      {summary.get('total_fat', 'N/A')}")
            lines.append(f"   Total Fibre:    {summary.get('total_fibre', 'N/A')}")
            if summary.get("overall_notes"):
                lines.append(f"   Summary Notes:  {summary.get('overall_notes')}")
            lines.append("─"*45)

        lines.append("📌 ACCURACY DISCLAIMER: Image-based values are ESTIMATED. Verified package labels are marked [LABEL DATA].")

        out_text = "\n".join(lines)
        self._food_vision_display.setText(out_text)
        self.append_activity(f"FoodVision: Analyzed {summary.get('title', 'Food')} ({source})")

        # Voice explanation if callbacks attached
        if self.on_text_command and voice_text:
            self.append_activity(f"LIHA: {voice_text}")

    def _on_chat_send(self):
        txt = self._chat_input.text().strip()
        if not txt: return
        self._chat_input.clear()
        self._dispatch_text(txt)

    def _on_right_send(self):
        txt = self._right_input.text().strip()
        if not txt: return
        self._right_input.clear()
        self._dispatch_text(txt)

    def _dispatch_text(self, txt: str):
        now_h = datetime.now().strftime("%H:%M")
        self._chat_history.append(f"<b style='color:{C.CYAN}'>You ({now_h}):</b> {txt}")
        self.append_activity(f"You: {txt[:40]}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def append_activity(self, text: str):
        now_h = datetime.now().strftime("%H:%M")
        prefix = "🟢" if "ready" in text.lower() or "online" in text.lower() or "active" in text.lower() else "🔵"
        if "err" in text.lower() or "fail" in text.lower() or "muted" in text.lower():
            prefix = "🔴"
        self._activity_log.append(f"{prefix} {now_h} — {text}")

    def _clear_activity_log(self):
        self._activity_log.clear()

    def _on_file_dropped(self, fpath: str):
        self._current_file = fpath
        fname = os.path.basename(fpath)
        self.append_activity(f"File loaded: {fname}")
        self._files_info.append(f"📄 Loaded File: {fpath}\nReady for LIHA processing.")
        if self._drop_zone.current_file() != fpath:
            self._drop_zone.set_file(fpath)
        if self._files_drop.current_file() != fpath:
            self._files_drop.set_file(fpath)

    def _load_api_key_into_settings(self):
        if API_FILE.exists():
            try:
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                key = d.get("gemini_api_key", "")
                self._key_input.setText(key)
            except Exception:
                pass

    def _save_settings(self):
        key = self._key_input.text().strip()
        voice_str = self._combo_voice.currentText()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        cfg = {}
        if API_FILE.exists():
            try:
                cfg = json.loads(API_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
                
        cfg["gemini_api_key"] = key
        cfg["os_system"] = _OS
        cfg["voice_model"] = voice_str
        
        API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        self.append_activity("SYS: Settings saved successfully.")
        self._files_info.append("SYS: Settings updated.")

    def closeEvent(self, event):
        event.accept()
        # Cleanly release microphone & audio streams before exit
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        liha = getattr(self, "_liha_instance", None)
        if liha is not None:
            try:
                liha.shutdown()
            except Exception:
                pass
        import time
        time.sleep(0.15)   # brief pause so audio streams terminate
        os._exit(0)

    # --------------------------------------------------------------------------
    # PUBLIC SLOTS / API COMPATIBILITY FOR MAIN.PY
    # --------------------------------------------------------------------------
    def _append_log_impl(self, text: str):
        now_h = datetime.now().strftime("%H:%M")
        if text.startswith("You:"):
            self._chat_history.append(f"<b style='color:{C.CYAN}'>{text}</b>")
        elif text.startswith("LIHA:"):
            self._chat_history.append(f"<b style='color:{C.GREEN}'>{text}</b>")
        else:
            self._chat_history.append(f"<span style='color:{C.TEXT_DIM}'>{text}</span>")
            
        self.append_activity(text)

    def _apply_state_impl(self, state: str):
        st = state.upper()
        self._holo_core.set_state(st)

        CALM_BLUE = "#5588cc"

        if st == "SPEAKING":
            self._lbl_core_status.setText("SPEAKING")
            self._lbl_core_status.setStyleSheet(f"color: {C.CYAN}; border: none;")
            self._lbl_core_dot.setText("🔵")
            self._voice_status_lbl.setText("LIHA SPEAKING...")
            self._voice_status_lbl.setStyleSheet(f"color: {C.CYAN}; border: none;")
            self._wave_widget.set_active(True)
            self._large_wave.set_active(True)
        elif st in ("THINKING", "PROCESSING"):
            label = "PROCESSING..." if st == "PROCESSING" else "THINKING..."
            self._lbl_core_status.setText(label)
            self._lbl_core_status.setStyleSheet(f"color: {C.BLUE_ACCENT}; border: none;")
            self._lbl_core_dot.setText("🟡")
            self._voice_status_lbl.setText(f"LIHA {label}")
            self._voice_status_lbl.setStyleSheet(f"color: {C.BLUE_ACCENT}; border: none;")
            self._wave_widget.set_active(True)
            self._large_wave.set_active(True)
        elif st in ("HAPPY", "POSITIVE"):
            self._lbl_core_status.setText("READY TO HELP")
            self._lbl_core_status.setStyleSheet(f"color: {C.GREEN}; border: none;")
            self._lbl_core_dot.setText("🟢")
            self._voice_status_lbl.setText("LIHA READY")
            self._voice_status_lbl.setStyleSheet(f"color: {C.GREEN}; border: none;")
            self._wave_widget.set_active(True)
            self._large_wave.set_active(True)
        elif st in ("ERROR", "CONFUSED"):
            # Calm assist — softer blue, NOT alarming red
            self._lbl_core_status.setText("CHECKING...")
            self._lbl_core_status.setStyleSheet(f"color: {CALM_BLUE}; border: none;")
            self._lbl_core_dot.setText("🔵")
            self._voice_status_lbl.setText("CHECKING ISSUE — PLEASE WAIT")
            self._voice_status_lbl.setStyleSheet(f"color: {CALM_BLUE}; border: none;")
            self._wave_widget.set_active(False)
            self._large_wave.set_active(False)
        elif st == "OFFLINE":
            self._lbl_core_status.setText("OFFLINE")
            self._lbl_core_status.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
            self._lbl_core_dot.setText("⚪")
            self._voice_status_lbl.setText("OFFLINE — RECONNECTING...")
            self._voice_status_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
            self._wave_widget.set_active(False)
            self._large_wave.set_active(False)
        elif st == "MUTED":
            self._lbl_core_status.setText("MUTED")
            self._lbl_core_status.setStyleSheet(f"color: {C.RED}; border: none;")
            self._lbl_core_dot.setText("🔴")
            self._voice_status_lbl.setText("MICROPHONE MUTED")
            self._voice_status_lbl.setStyleSheet(f"color: {C.RED}; border: none;")
            self._wave_widget.set_active(False)
            self._large_wave.set_active(False)
        elif st == "IDLE":
            self._lbl_core_status.setText("IDLE")
            self._lbl_core_status.setStyleSheet(f"color: {C.CYAN_DIM}; border: none;")
            self._lbl_core_dot.setText("🟢")
            self._voice_status_lbl.setText("LIHA STANDING BY")
            self._voice_status_lbl.setStyleSheet(f"color: {C.CYAN_DIM}; border: none;")
            self._wave_widget.set_active(False)
            self._large_wave.set_active(False)
        elif st == "LISTENING":
            self._lbl_core_status.setText("LISTENING")
            self._lbl_core_status.setStyleSheet(f"color: {C.CYAN}; border: none;")
            self._lbl_core_dot.setText("🟢")
            self._voice_status_lbl.setText("MICROPHONE ACTIVE — LISTENING")
            self._voice_status_lbl.setStyleSheet(f"color: {C.GREEN}; border: none;")
            self._wave_widget.set_active(True)
            self._large_wave.set_active(True)
        else:  # ACTIVE / ONLINE / default
            self._lbl_core_status.setText("ACTIVE")
            self._lbl_core_status.setStyleSheet(f"color: {C.GREEN}; border: none;")
            self._lbl_core_dot.setText("🟢")
            self._voice_status_lbl.setText("MICROPHONE ACTIVE — LISTENING")
            self._voice_status_lbl.setStyleSheet(f"color: {C.GREEN}; border: none;")
            self._wave_widget.set_active(True)
            self._large_wave.set_active(True)


# ==============================================================================
# 6. ROOT SHIM & LIHAUI BACKWARD-COMPATIBLE WRAPPER
# ==============================================================================
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class LIHAUI:
    def __init__(self, face_path: str = "face.png", size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def _liha_instance(self):
        return getattr(self._win, "_liha_instance", None)

    @_liha_instance.setter
    def _liha_instance(self, inst):
        self._win._liha_instance = inst

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return getattr(self._win, "_current_file", None) or self._win._drop_zone.current_file() or self._win._files_drop.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        # Immediately proceed if API key already set
        while not API_FILE.exists():
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")