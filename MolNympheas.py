'''
==============================================================================
MolNympheas: A Smart Color Palette Picker for ChimeraX & PyMOL
==============================================================================

DESCRIPTION
    MolNympheas is a universal plugin designed to bring mathematically "perfect", 
    palettes to your structural biology figures. 
    Named in honor of Claude Monet's "Nymphéas" (Water Lilies), this tool 
    uses Matplotlib to generate perceptually uniform colors (Viridis, Magma, 
    etc.) and automatically calculates harmonious color schemes.
    It automatically detects whether it is running inside PyMOL or ChimeraX 
    and adapts its commands accordingly.

FEATURES
    - Universal Environment Detection (PyMOL / ChimeraX). (Thanks To Florian Chenavier)
    - Independent Workspaces: 
        A: Matplotlib Scientific Colormaps
        B: Harmony-based Color Generation
        C: Custom Free-form Canvas
    - Colorblind Accessibility:
        - Integrated Okabe-Ito Colorblind Safe Preset.
        - Real-time CVD (Color Vision Deficiency) Compatibility Matrix.
        - Automated Clash Detection (Delta-E based) for accessibility warnings.
    - Smart Editing:
        - Clickable color blocks with independent Paste/Copy/Pick functions.
        - Smart Hex parsing (handles missing '#' automatically).
        - Undo/Redo memory per workspace.
    - Save & Load configurations via JSON (Cross-software compatible).
    - Auto-detection of models/selections in PyMOL or ChimeraX GUI.

USAGE
    In ChimeraX: open /path/to/MolNympheas.py
    
    In PyMOL:   run /path/to/MolNympheas.py
    (Note: Matplotlib must be installed in your PyMOL environment via: pip install matplotlib)

INSPIRATION
    Initially inspired by the `pymol_viridis` script by Shyam Saladi. 
    Orsay Museum Paris for the fantastic collections.

VERSIONING:

03-03-2026: v3.0.0 
    One script to rule them all !! ChimeraX and PyMol.

13-03-2026: V3.1.0   
    Added Color picker for the main color, gradient generator.

22-06-2026: V4.0.0 (The "Universal Workspace" Update)
    - Refactored into three independent workspaces (Matplotlib/Harmony/Custom).
    - Added automated Color Clash Detection (Delta-E math) in CVD Matrix.
    - Added Okabe-Ito colorblind-safe preset.
    - Added Smart-Paste functionality for Hex codes.
    - Fixed UI rendering for macOS and cross-platform Qt compatibility.
    - Added Illustrator palette export .ase

04-07-2026: V5.0.0 (The PyMeraX Integration)
    - Integrated the PyMeraX engine to bring ChimeraX-like rendering directly into PyMOL.
    - Added a dynamic "Tab D: PyMeraX" that exclusively loads in PyMOL or Standalone modes.
    - Included 1-click GUI buttons for Cartoon, Surface, Publication, and Ligand rendering presets.
==============================================================================
'''
import sys
import json
import os
import colorsys
import struct

# --- ENVIRONMENT DETECTION ---
ENV = "standalone"
try:
    import pymol
    from pymol import cmd
    ENV = "pymol"
except ImportError:
    pass

try:
    from chimerax.core.commands import run
    ENV = "chimerax"
except ImportError:
    pass

# Try importing matplotlib for Tab A
HAS_MATPLOTLIB = False
# --- DYNAMIC QT IMPORT (PyQt5 for PyMOL, PyQt6 for ChimeraX) ---
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                                 QTabWidget, QComboBox, QCheckBox, QSpinBox, 
                                 QFrame, QColorDialog, QFileDialog, QSlider,
                                 QDialog, QGridLayout,QMenu)
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtGui import QColor
    QT_VERSION = 5
except ImportError:
    try:
        from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                     QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                                     QTabWidget, QComboBox, QCheckBox, QSpinBox, 
                                     QFrame, QColorDialog, QFileDialog, QSlider,
                                     QDialog, QGridLayout,QMenu)
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QColor
        QT_VERSION = 6
    except ImportError:
        print("MolNympheas Error: Neither PyQt5 nor PyQt6 was found.")
        sys.exit(1)
   # Try importing matplotlib for Tab A
    HAS_MATPLOTLIB = False
try:
    import matplotlib
    try:
        # Force Matplotlib to run in the background.
        # Isolated in try/except: if ChimeraX/PyMOL already initialized it, we safely ignore the error!
        matplotlib.use('Agg') 
    except:
        pass 
        
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except Exception as e:
    print(f"MolNympheas Warning: Matplotlib disabled. Reason: {e}")

# ==========================================
# MATH ENGINES (Harmony & CVD Simulation)
# ==========================================
def hex_to_hsv(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)

def hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02X}{:02X}{:02X}".format(int(r*255), int(g*255), int(b*255))

def generate_harmony(base_hex, rule, num_colors):
    """Generates a list of hex colors based on a color theory rule."""
    h, s, v = hex_to_hsv(base_hex)
    colors = [base_hex]
    
    for i in range(1, num_colors):
        if rule == "Complementary":
            new_h = (h + (0.5 * (i % 2)) + (0.05 * i)) % 1.0 # Alternates and slight shifts
        elif rule == "Analogous":
            new_h = (h + (0.08 * i)) % 1.0
        elif rule == "Triadic":
            new_h = (h + (0.33 * i)) % 1.0
        else: # Monochromatic
            new_h = h
            v = max(0.2, (v - (0.15 * i))) # Darken progressively
            
        colors.append(hsv_to_hex(new_h, s, v))
    return colors

def simulate_cvd(hex_color, cvd_type):
    """Approximates Color Vision Deficiency for UI preview."""
    # Simplified approximation for fast UI feedback
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    if cvd_type == "Protanopia":
        new_r = 0.567 * r + 0.433 * g
        new_g = 0.558 * r + 0.442 * g
        new_b = 0 * r + 0.242 * g + 0.758 * b
    elif cvd_type == "Deuteranopia":
        new_r = 0.625 * r + 0.375 * g
        new_g = 0.7 * r + 0.3 * g
        new_b = 0 * r + 0.3 * g + 0.7 * b
    elif cvd_type == "Tritanopia":
        new_r = 0.95 * r + 0.05 * g
        new_g = 0 * r + 0.433 * g + 0.567 * b
        new_b = 0 * r + 0.475 * g + 0.525 * b
    else:
        return f"#{hex_color}"
        
    return "#{:02X}{:02X}{:02X}".format(
        min(255, int(new_r*255)), min(255, int(new_g*255)), min(255, int(new_b*255))
    )
# ==========================================
# PYMERAX ENGINE (PyMOL Only)
# ==========================================

def _pmx_set_bg():
    cmd.set_color("pymerax_bg", [0.84, 0.84, 0.84])
    cmd.bg_color("pymerax_bg")

def _pmx_base():
    settings = {
        "orthoscopic": 1,
        "antialias": 2,
        "ray_trace_mode": 0,
        "ray_trace_gain": 0.12,
        "ray_trace_fog": 0,
        "ray_opaque_background": 0,
        "depth_cue": 0,
        "hash_max": 300,
    }
    for k, v in settings.items():
        cmd.set(k, v)

def _pmx_lights():
    settings = {
        "ambient": 0.40,
        "direct": 0.40,
        "reflect": 0.20,
        "specular": 0.08,
        "shininess": 8,
        "spec_direct": 0,
        "light_count": 8,
    }
    for k, v in settings.items():
        cmd.set(k, v)

    # Manual lights
    cmd.set("light", (-0.4, -0.3, -1.0))
    cmd.set("light2", (-0.8, -0.2, 0.2))
    cmd.set("light3", (0.6, -0.7, -0.1))

def _pmx_ao_cartoon():
    try:
        cmd.set("ambient_occlusion_mode", 1)
        cmd.set("ambient_occlusion_scale", 10)
        cmd.set("ambient_occlusion_smooth", 8)
    except:
        pass

def _pmx_ao_surface():
    try:
        cmd.set("ambient_occlusion_mode", 2)
        cmd.set("ambient_occlusion_scale", 14)
        cmd.set("ambient_occlusion_smooth", 14)
    except:
        pass

def _pmx_cartoon():
    cmd.hide("everything")
    cmd.show("cartoon")
    
    settings = {
        "cartoon_fancy_helices": 1,
        "cartoon_oval_length": 1.2,
        "cartoon_oval_width": 1.1,
        "cartoon_sampling": 20,
        "cartoon_smooth_loops": 1,
        "cartoon_flat_sheets": 0,
        "cartoon_highlight_color": -1,
    }
    for k, v in settings.items():
        cmd.set(k, v)
    _pmx_ao_cartoon()

def _pmx_surface():
    cmd.hide("everything")
    
    settings = {
        "surface_quality": 1, # Qualité à 1 pour la vitesse !
        "surface_smooth_edges": 1,
        "surface_solvent": 0,
        "transparency": 0,
        "transparency_mode": 2,
        "two_sided_lighting": 1,
        
        # Lighting (less extreme)
        "ambient": 0.46,
        "direct": 0.30,
        "reflect": 0.34,
        "specular": 0.02,
        "shininess": 2,
        
        "ray_shadows": 1,
        "ray_shadow_decay_factor": 0.08,
        "ray_shadow_decay_range": 4.5,
    }
    for k, v in settings.items():
        cmd.set(k, v)

    # Better grazing-angle lights for surfaces
    cmd.set("light", (-0.3, -0.2, -1.0))
    cmd.set("light2", (-1.0, 0.0, 0.4))
    cmd.set("light3", (0.8, -0.5, 0.2))

    _pmx_ao_surface()
    
    # Affichage en dernier pour éviter le double calcul
    cmd.show("surface", "polymer") 

def _pmx_ligand():
    cmd.hide("everything")
    cmd.show("cartoon")
    cmd.show("sticks", "organic")
    
    # --- LES NOUVEAUTÉS LIGAND ---
    cmd.set("cartoon_transparency", 0.6)  # Rend la protéine fantomatique/transparente
    
    try:
        # Centre automatiquement la caméra sur les petites molécules avec une marge de 4 Angströms
        cmd.zoom("organic", buffer=4.0, animate=-1) 
    except: 
        pass
    
    # Réglages d'origine pour rendre le ligand brillant et joli
    settings = {
        "stick_radius": 0.18,
        "stick_ball": 1,
        "stick_ball_ratio": 1.5,
        "valence": 1,
        "specular": 0.20,
        "shininess": 18,
    }
    for k, v in settings.items():
        cmd.set(k, v)



# ============================================================
# Main PyMeraX Apply Function
# ============================================================
def pymerax_apply(mode="cartoon"):
    if ENV != "pymol":
        print("MolNympheas: PyMeraX features are only active inside PyMOL.")
        return

    cmd.reinitialize("settings")
    mode = mode.lower().strip()

    _pmx_set_bg()
    _pmx_base()
    _pmx_lights()

    if mode == "cartoon":
        _pmx_cartoon()

    elif mode == "surface":
        _pmx_surface()

    elif mode == "publication":
        _pmx_cartoon()
        cmd.bg_color("white")
        
        # --- LES NOUVEAUTÉS PUBLICATION ---
        cmd.set("ray_trace_mode", 1)       # Active les contours (Outlines)
        cmd.set("ray_trace_color", "black") # Force les contours en noir absolu
        cmd.set("ray_trace_gain", 0.08)    # Trait légèrement plus épais et visible
        
        # Éclairage optimisé pour le papier (moins d'ombres dures)
        cmd.set("ambient", 0.55)
        cmd.set("direct", 0.25)

    elif mode == "ligand":
        # Applique les réglages cartoon pour le contexte, puis les réglages ligands
        _pmx_cartoon() 
        _pmx_ligand()

    print(f"MolNympheas: PyMeraX [{mode.upper()}] mode applied!")

# ==========================================
# PHASE 1: STATE MANAGER
# ==========================================
class PaletteStateManager:
    def __init__(self):
        # We now store independent memory for each Tab Workspace!
        self.workspaces = {
            "A": {"colors": ["#440154", "#3B528B", "#21908C", "#5DC863", "#FDE725"], "undo": [], "redo": []},
            "B": {"colors": ["#FF5733", "#C70039", "#900C3F"], "undo": [], "redo": []}, # Default size 3
            "C": {"colors": ["#FF5733", "#FFC300", "#DAF7A6", "#33FF57", "#33C1FF"], "undo": [], "redo": []}
        }
        
        self.default_colors = ["#FF5733", "#FFC300", "#DAF7A6", "#33FF57", "#33C1FF", 
                               "#FF33A1", "#A133FF", "#33FFCC", "#FF8C33", "#C70039"]

    def update_colors(self, tab_key, new_colors, record_history=True):
        ws = self.workspaces[tab_key]
        if ws["colors"] == new_colors: return

        if record_history:
            if ws["undo"] and ws["undo"][-1] == ws["colors"]:
                pass 
            else:
                ws["undo"].append(list(ws["colors"]))
            ws["redo"].clear()
            
        ws["colors"] = list(new_colors)

    def undo(self, tab_key):
        ws = self.workspaces[tab_key]
        if ws["undo"]:
            ws["redo"].append(list(ws["colors"]))
            ws["colors"] = ws["undo"].pop()
            return True
        return False

    def redo(self, tab_key):
        ws = self.workspaces[tab_key]
        if ws["redo"]:
            ws["undo"].append(list(ws["colors"]))
            ws["colors"] = ws["redo"].pop()
            return True
        return False
    
# ==========================================
# PHASE 2 & 3: UI COMPONENTS & WIDGETS
# ==========================================
class ColorBlockWidget(QWidget):
    # We added 'apply_cb' here!
# Added 'is_editable' flag to hide buttons when needed
    def __init__(self, initial_hex="#CCCCCC", block_index=0, update_cb=None, apply_cb=None, is_editable=True):
        super().__init__()
        self.block_index = block_index
        self.update_cb = update_cb
        self.apply_cb = apply_cb
        self.current_hex = initial_hex
        
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.color_patch = QPushButton()
        self.color_patch.setFixedSize(70, 70)
        self.color_patch.setCursor(Qt.PointingHandCursor) 
        self.color_patch.setToolTip("Click to apply THIS color to your selection!")
        self.color_patch.clicked.connect(self.patch_clicked)
        
        self.hex_display = QLineEdit()
        self.hex_display.setAlignment(Qt.AlignCenter)
        self.hex_display.setStyleSheet("border: 1px solid #ccc; background: transparent; font-weight: bold;")
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        # --- SMART EDITABILITY ---
        if is_editable:
            self.hex_display.setReadOnly(False)
            self.hex_display.returnPressed.connect(self.manual_hex_entered)
            
            self.pipette_btn = QPushButton("Pick")
            self.pipette_btn.clicked.connect(self.pick_color)
            self.paste_btn = QPushButton("Paste")
            self.paste_btn.clicked.connect(self.paste_from_clipboard)
            
            btn_layout.addWidget(self.pipette_btn)
            btn_layout.addWidget(self.paste_btn)
        else:
            self.hex_display.setReadOnly(True)
            self.hex_display.setStyleSheet("border: none; background: transparent; font-weight: bold;")

        btn_layout.addWidget(self.copy_btn)
        
        layout.addWidget(self.color_patch, alignment=Qt.AlignCenter)
        layout.addWidget(self.hex_display)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        self.set_color(initial_hex)

    def paste_from_clipboard(self):
        """Smart Paste: Auto-formats the # and validates before applying."""
        text = QApplication.clipboard().text().strip().upper()
        
        # Add the # if the user forgot it
        if not text.startswith('#'):
            text = '#' + text
            
        # Only apply if it is a mathematically valid hex code
        if len(text) == 7 and all(c in '0123456789ABCDEF#' for c in text):
            self.hex_display.setText(text)
            self.manual_hex_entered() # Trigger the existing update logic
            
    def set_color(self, hex_val, display_hex=None):
        self.current_hex = hex_val
        visual_hex = display_hex if display_hex else hex_val
        self.hex_display.setText(self.current_hex)
        # Even though it's a button, we style it flat so it looks exactly like a color block
        self.color_patch.setStyleSheet(f"background-color: {visual_hex}; border-radius: 5px; border: 1px solid #aaa;")

    def patch_clicked(self):
        """Fires when the user clicks the big color square."""
        if self.apply_cb:
            self.apply_cb(self.current_hex)
            
    # ... keep your existing manual_hex_entered, pick_color, and copy_to_clipboard ...
    def manual_hex_entered(self):
        """Fires when the user types a hex code and hits Enter."""
        new_hex = self.hex_display.text().strip().upper()
        if not new_hex.startswith('#'):
            new_hex = '#' + new_hex
            
        # Basic validation to ensure it's a real hex code before updating
        if len(new_hex) == 7 and all(c in '0123456789ABCDEF#' for c in new_hex):
            if self.update_cb and new_hex != self.current_hex:
                self.update_cb(self.block_index, new_hex)
        else:
            # Revert to the last valid color if they typed nonsense
            self.hex_display.setText(self.current_hex)

    # ... keep your existing set_color, pick_color, and copy_to_clipboard functions exactly the same!
    def set_color(self, hex_val, display_hex=None):
        self.current_hex = hex_val
        visual_hex = display_hex if display_hex else hex_val
        self.hex_display.setText(self.current_hex)
        self.color_patch.setStyleSheet(f"background-color: {visual_hex}; border-radius: 5px; border: 1px solid #aaa;")

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.current_hex), self)
        if color.isValid() and self.update_cb:
            self.update_cb(self.block_index, color.name().upper())
    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.current_hex)
        self.copy_btn.setText("✅")
        
        # Create a timer attached to this specific widget (self)
        # If the widget is deleted, Qt safely deletes this timer too!
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self.reset_copy_text)
        self._reset_timer.start(1000)

    def reset_copy_text(self):
        # We use a standard function instead of a lambda
        self.copy_btn.setText("📋")

# ==========================================
# MAIN APPLICATION WINDOW
# ==========================================
# ==========================================
# CVD MATRIX DIALOG
# ==========================================
class CVDMatrixDialog(QDialog):
    def __init__(self, current_colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CVD Compatibility Matrix")
        self.colors = current_colors
        
        # Main layout
        layout = QGridLayout(self)
        layout.setSpacing(10)
        
        # Calculate clashes once for the whole dialog
        self.clashes = self.get_clashing_indexes(current_colors)
        
        modes = ["Normal Vision", "Protanopia", "Deuteranopia", "Tritanopia"]
        
        # Build the grid row by row
        for row, mode in enumerate(modes):
            # Row Label
            label = QLabel(f"<b>{mode}</b>")
            layout.addWidget(label, row * 2, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
            
            # Color Blocks
            for col, hex_val in enumerate(self.colors):
                sim_hex = hex_val if mode == "Normal Vision" else simulate_cvd(hex_val, mode)
                
                # The Color Patch
                patch = QFrame()
                patch.setFixedSize(60, 60)
                patch.setStyleSheet(f"background-color: {sim_hex}; border-radius: 5px; border: 1px solid #aaa;")
                layout.addWidget(patch, row * 2, col + 1)
                
                # Add Warning Text ONLY in the Normal Vision row (row 0)
                # so we don't clutter the other rows
                if row == 0 and col in self.clashes:
                    warning = QLabel("⚠️ Clash")
                    warning.setStyleSheet("color: red; font-size: 9px; font-weight: bold;")
                    layout.addWidget(warning, (row * 2) + 1, col + 1, alignment=Qt.AlignCenter)

    def get_clashing_indexes(self, colors):
        """Standard Delta-E approximation to check for color clashes."""
        clashing = set()
        for i in range(len(colors)):
            for j in range(i + 1, len(colors)):
                # Convert hex to RGB integers
                c1 = [int(colors[i].lstrip('#')[k:k+2], 16) for k in (0, 2, 4)]
                c2 = [int(colors[j].lstrip('#')[k:k+2], 16) for k in (0, 2, 4)]
                # Euclidean distance check
                dist = sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
                if dist < 80: 
                    clashing.update([i, j])
        return clashing


class MolNympheasUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MolNympheas - {ENV.upper()}")
        self.setMinimumWidth(700)
        
        # FIX: Removed default_size=5
        self.state = PaletteStateManager() 
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        
        self.setup_toolbar()
        self.setup_tabs()

        
    def setup_toolbar(self):
            toolbar = QHBoxLayout()
            
            self.target_combo = QComboBox()
            self.target_combo.setEditable(True) 
            self.target_combo.setToolTip("Select or type a PyMOL/ChimeraX selection")
            
            self.refresh_btn = QPushButton("🔄")
            self.refresh_btn.setToolTip("Refresh Object/Selection List")
            self.refresh_btn.clicked.connect(self.refresh_targets)

            toolbar.addWidget(QLabel("Target Object/Selection:"))
            toolbar.addWidget(self.target_combo)
            toolbar.addWidget(self.refresh_btn) 
            toolbar.addStretch() # Pushes everything neatly to the left
            
            self.main_layout.addLayout(toolbar)
            self.main_layout.addWidget(self.create_divider())
            self.refresh_targets()

    def refresh_targets(self):
        """Fetches the current objects and selections from the active environment."""
        self.target_combo.clear()
        
        if ENV == "pymol":
            try:
                # 'public' gets both objects and user-defined selections
                names = cmd.get_names("public")
                self.target_combo.addItems(["all"] + names)
            except Exception as e:
                self.target_combo.addItems(["all"])
                
        elif ENV == "chimerax":
            try:
                self.target_combo.clear()
                # 'sel' targets the active mouse selection in ChimeraX
                model_ids = [f"#{m.id_string}" for m in session.models.list()]
                self.target_combo.addItems(["all", "sel"] + model_ids)
            except Exception as e:
                print(f"MolNympheas Warning: Could not fetch ChimeraX models. {e}")
                self.target_combo.addItems(["sel", "all", "#1", "#2"])
            
        else:
            # Standalone testing mode defaults
            self.target_combo.addItems(["all", "Selection 1", "Protein A"])

    def setup_tabs(self):
        self.tabs = QTabWidget()
        
        # We will store references to the UI elements for each tab here
        self.tab_uis = {"A": {}, "B": {}, "C": {}}
        
        # Build the 3 Tabs
        self.tabs.addTab(self.build_tab_A(), "A: Matplotlib")
        self.tabs.addTab(self.build_tab_B(), "B: Auto-Harmony")
        self.tabs.addTab(self.build_tab_C(), "C: Custom Canvas")
        if ENV in ["pymol", "standalone"]:
            self.tabs.addTab(self.build_tab_D(), "D: PyMeraX")
        
        self.main_layout.addWidget(self.tabs)
        
        
        # Draw the initial blocks
        self.render_tab_blocks("A", is_editable=False)
        self.render_tab_blocks("B", is_editable=False)
        self.render_tab_blocks("C", is_editable=True)

    def build_workspace_frame(self, tab_key, top_controls_layout):
        """Builds a standardized workspace layout for a tab."""
        wrapper = QWidget()
        main_lay = QVBoxLayout(wrapper)
        
        # 1. Top Controls
        main_lay.addLayout(top_controls_layout)
        main_lay.addWidget(self.create_divider())
        
        # 2. Shared Workspace Controls
        ctrl_lay = QHBoxLayout()
        spin = QSpinBox()
        spin.setRange(2, 30) # Increased max range so you can make huge palettes!
        spin.setValue(len(self.state.workspaces[tab_key]["colors"]))
        spin.valueChanged.connect(lambda v, k=tab_key: self.resize_palette(k, v))
        self.tab_uis[tab_key]["spin"] = spin
        
        btn_undo = QPushButton("Undo")
        btn_undo.setMinimumWidth(60)
        btn_undo.clicked.connect(lambda _, k=tab_key: self.trigger_history(k, self.state.undo))
        
        btn_redo = QPushButton("Redo")
        btn_redo.setMinimumWidth(60)
        btn_redo.clicked.connect(lambda _, k=tab_key: self.trigger_history(k, self.state.redo))
        
        ctrl_lay.addWidget(QLabel("Colors:"))
        ctrl_lay.addWidget(spin)
        ctrl_lay.addStretch()
        ctrl_lay.addWidget(btn_undo)
        ctrl_lay.addWidget(btn_redo)
        main_lay.addLayout(ctrl_lay)
        
        # 3. The Color Blocks Area (NOW A GRID SO IT WRAPS)
        blocks_lay = QGridLayout()
        blocks_lay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        blocks_lay.setSpacing(5)
        self.tab_uis[tab_key]["blocks_lay"] = blocks_lay
        main_lay.addLayout(blocks_lay)
        main_lay.addStretch()
        
        # 4. Bottom Controls (RESTORED CVD BUTTON)
        bot_lay = QHBoxLayout()
        btn_cvd = QPushButton("👁️ View CVD Matrix")
        btn_cvd.clicked.connect(lambda _, k=tab_key: self.show_cvd_matrix(k))
        # The new Export Menu Button
        btn_export = QPushButton("💾 Export...")
        menu = QMenu(self)
        
        # Add options to the menu
        action_json = menu.addAction("Export as JSON")
        action_json.triggered.connect(lambda: self.save_json(tab_key))
        
        action_ase = menu.addAction("Export as Adobe ASE")
        action_ase.triggered.connect(lambda: self.export_to_ase(tab_key))
        
        btn_export.setMenu(menu)
        
        bot_lay.addWidget(btn_cvd)
        bot_lay.addStretch()
        bot_lay.addWidget(btn_export)
        main_lay.addLayout(bot_lay)
        
        return wrapper
    
    def build_tab_A(self):
        lay = QHBoxLayout()
        self.cmap_combo = QComboBox()
        
        # --- ADDED OKABE-ITO ---
        self.okabe_ito = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]
        self.cmap_combo.addItem("Okabe-Ito (Colorblind Safe)")
        
        if HAS_MATPLOTLIB:
            try: all_cmaps = [c for c in plt.colormaps() if not c.endswith('_r')]
            except: all_cmaps = [c for c in plt.cm.cmap_d.keys() if not c.endswith('_r')]
            self.cmap_combo.addItems(all_cmaps)
        
        # --- SET DEFAULT ---
        self.cmap_combo.setCurrentText('viridis') 
            
        # Connect AFTER setting the default so you don't trigger unnecessary updates
        self.cmap_combo.currentTextChanged.connect(self.generate_from_matplotlib)
        
        lay.addWidget(QLabel("Colormap:"))
        lay.addWidget(self.cmap_combo)
        lay.addStretch()
        return self.build_workspace_frame("A", lay)
    
    def build_tab_B(self):
        lay = QHBoxLayout()
        self.seed_input = QLineEdit("#FF5733")
        self.seed_input.setFixedWidth(70)
        self.seed_input.returnPressed.connect(self.generate_from_harmony)
        
        self.seed_picker_btn = QPushButton("Pick")
        self.seed_picker_btn.clicked.connect(self.pick_seed)
        self.seed_paste_btn = QPushButton("Paste")
        self.seed_paste_btn.clicked.connect(self.paste_seed)
        
        self.rule_combo = QComboBox()
        self.rule_combo.addItems(["Complementary", "Analogous", "Triadic", "Monochromatic"])
        self.rule_combo.currentTextChanged.connect(self.generate_from_harmony)
        
        lay.addWidget(QLabel("Seed:"))
        lay.addWidget(self.seed_input)
        lay.addWidget(self.seed_picker_btn)
        lay.addWidget(self.seed_paste_btn)
        lay.addWidget(QLabel("Rule:"))
        lay.addWidget(self.rule_combo)
        lay.addStretch()
        return self.build_workspace_frame("B", lay)

    def build_tab_C(self):
        lay = QHBoxLayout()
        lay.addWidget(QLabel("<i>Use the tools below to build a custom palette block by block.</i>"))
        
        btn_load = QPushButton("📂 Load JSON")
        btn_load.clicked.connect(self.load_json)
        lay.addStretch()
        lay.addWidget(btn_load) # Only Tab C needs a Load button
        return self.build_workspace_frame("C", lay)
    def build_tab_D(self):
        wrapper = QWidget()
        lay = QVBoxLayout(wrapper)
        
        # En-tête informatif
        info = QLabel("<b>PyMeraX Engine:</b> Appliquez instantanément un rendu haute qualité (façon ChimeraX) à votre session PyMOL.<br><i>Note: Cela réinitialisera vos paramètres d'éclairage actuels.</i>")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addWidget(self.create_divider())
        
        # Grille de boutons pour les 4 modes
        grid = QGridLayout()
        grid.setSpacing(10)
        
        btn_cartoon = QPushButton("🧬 Mode Cartoon")
        btn_cartoon.setMinimumHeight(40)
        btn_cartoon.clicked.connect(lambda: pymerax_apply("cartoon"))
        
        btn_surf = QPushButton("☁️ Mode Surface")
        btn_surf.setMinimumHeight(40)
        btn_surf.clicked.connect(lambda: pymerax_apply("surface"))
        
        btn_pub = QPushButton("📄 Mode Publication\n(Fond blanc)")
        btn_pub.setMinimumHeight(40)
        btn_pub.clicked.connect(lambda: pymerax_apply("publication"))
        
        btn_lig = QPushButton("💊 Mode Ligand\n(Surbrillance)")
        btn_lig.setMinimumHeight(40)
        btn_lig.clicked.connect(lambda: pymerax_apply("ligand"))
        
        grid.addWidget(btn_cartoon, 0, 0)
        grid.addWidget(btn_surf, 0, 1)
        grid.addWidget(btn_pub, 1, 0)
        grid.addWidget(btn_lig, 1, 1)
        
        lay.addLayout(grid)
        
        # Conseil d'utilisation en bas
        tip = QLabel("💡 <b>Astuce :</b> Une fois le mode Publication sélectionné, tapez <code>ray</code> dans la console PyMOL pour obtenir l'image finale.")
        tip.setStyleSheet("color: #666;")
        lay.addStretch()
        lay.addWidget(tip)
        
        return wrapper

    # --- WORKSPACE LOGIC ---
    def render_tab_blocks(self, tab_key, is_editable):
        blocks_lay = self.tab_uis[tab_key]["blocks_lay"]
        while blocks_lay.count():
            item = blocks_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
                
        colors = self.state.workspaces[tab_key]["colors"]
        max_cols = 6
        
        for i, hex_val in enumerate(colors):
            block = ColorBlockWidget(hex_val, i, 
                                     update_cb=lambda idx, h, k=tab_key: self.on_block_changed(k, idx, h), 
                                     apply_cb=self.apply_single_color, 
                                     is_editable=is_editable)
            
           
            row, col = i // max_cols, i % max_cols
            blocks_lay.addWidget(block, row, col)

    def on_block_changed(self, tab_key, index, new_hex):
        new_colors = list(self.state.workspaces[tab_key]["colors"])
        new_colors[index] = new_hex
        self.state.update_colors(tab_key, new_colors)
        self.render_tab_blocks(tab_key, is_editable=True)



    def trigger_history(self, tab_key, action):
        if action(tab_key): 
            spin = self.tab_uis[tab_key]["spin"]
            spin.blockSignals(True)
            spin.setValue(len(self.state.workspaces[tab_key]["colors"]))
            spin.blockSignals(False)
            
            is_edit = True if tab_key == "C" else False
            self.render_tab_blocks(tab_key, is_editable=is_edit)

    # ✅ KEEP THIS NEW ONE
    def show_cvd_matrix(self, tab_key):
        """Pops up the CVD Matrix for the specific workspace's palette."""
        colors = self.state.workspaces[tab_key]["colors"]
        dialog = CVDMatrixDialog(colors, self)
        
        # Safe execution that works in both PyQt5 and PyQt6
        if hasattr(dialog, 'exec_'):
            dialog.exec_()
        else:
            dialog.exec()


    def apply_single_color(self, hex_color):
        """Applies ONLY the clicked color to the currently targeted selection."""
        sele = self.target_combo.currentText()
        if not sele:
            return

        if ENV == "pymol":
            # Create a unique color name in PyMOL based on the hex (e.g., custom_ff0000)
            color_name = f"molnym_{hex_color.lstrip('#').lower()}"
            
            # Convert hex to RGB values between 0.0 and 1.0 for PyMOL
            r, g, b = tuple(int(hex_color.lstrip('#')[j:j+2], 16)/255.0 for j in (0, 2, 4))
            
            cmd.set_color(color_name, [r, g, b])
            cmd.color(color_name, sele)
            print(f"MolNympheas: Applied {hex_color} to PyMOL selection '{sele}'")
            
        elif ENV == "chimerax":
            try:
                # ChimeraX automatically provides the 'session' variable to scripts
                run(session, f"color {sele} {hex_color}")
                print(f"MolNympheas: Applied {hex_color} to ChimeraX '{sele}'")
            except Exception as e:
                print(f"MolNympheas Error: Could not apply to ChimeraX. {e}")
            
        else:
            print(f"MolNympheas (Standalone): Clicked {hex_color} to apply to '{sele}'")
    
    def on_block_changed(self, tab_key, index, new_hex):
        new_colors = list(self.state.workspaces[tab_key]["colors"])
        new_colors[index] = new_hex
        self.state.update_colors(tab_key, new_colors)
        self.render_tab_blocks(tab_key, is_editable=True)

    def resize_palette(self, tab_key, new_size):
        """Resizes the palette for a specific tab's workspace."""
        curr_colors = list(self.state.workspaces[tab_key]["colors"])
        
        # If growing, add vibrant colors from the default list
        if new_size > len(curr_colors):
            for i in range(new_size - len(curr_colors)):
                new_col = self.state.default_colors[(len(curr_colors) + i) % len(self.state.default_colors)]
                curr_colors.append(new_col)
        # If shrinking, cut the list down
        else:
            curr_colors = curr_colors[:new_size]
            
        self.state.update_colors(tab_key, curr_colors)
        
        # Automatically update the correct UI for the tab you are currently in
        if tab_key == "A": 
            self.generate_from_matplotlib()
        elif tab_key == "B": 
            self.generate_from_harmony()
        else: 
            self.render_tab_blocks("C", is_editable=True)


    # --- MATH GENERATORS ---
    def generate_from_matplotlib(self):
        if not HAS_MATPLOTLIB: return
        name = self.cmap_combo.currentText()
        n = self.tab_uis["A"]["spin"].value()
        
        # Check if we selected the Okabe-Ito preset
        if name == "Okabe-Ito (Colorblind Safe)":
            new_colors = self.okabe_ito[:n]
        else:
            cmap = plt.get_cmap(name)
            new_colors = [mcolors.to_hex(cmap(i / (n - 1))).upper() for i in range(n)]
            
        self.state.update_colors("A", new_colors)
        self.render_tab_blocks("A", is_editable=False)

    def generate_from_harmony(self):
        base = self.seed_input.text().strip().upper()
        if not base.startswith('#'): 
            base = '#' + base
            
        if len(base) != 7 or not all(c in '0123456789ABCDEF#' for c in base):
            return 
            
        rule = self.rule_combo.currentText()
        # FIX: Pull the size specifically from Tab B's spinner
        n = self.tab_uis["B"]["spin"].value() 
        new_colors = generate_harmony(base, rule, n)
        
        # FIX: Save to Workspace B and render Tab B
        self.state.update_colors("B", new_colors)
        self.render_tab_blocks("B", is_editable=False)

    def pick_seed(self):
        current_hex = self.seed_input.text()
        color = QColorDialog.getColor(QColor(current_hex), self)
        if color.isValid():
            hex_val = color.name().upper()
            self.seed_input.setText(hex_val)
            self.generate_from_harmony()
            
    def paste_seed(self):
        """Smart paste for the Harmony Seed."""
        text = QApplication.clipboard().text().strip().upper()
        
        if not text.startswith('#'):
            text = '#' + text
        
        if len(text) == 7 and all(c in '0123456789ABCDEF#' for c in text):
            self.seed_input.setText(text)
            self.generate_from_harmony()

    def apply_cvd_filter(self):
        mode = self.cvd_combo.currentText()
        for i, block in enumerate(self.block_widgets):
            true_hex = self.state.colors[i]
            if mode == "Normal Vision":
                block.set_color(true_hex)
            else:
                sim_hex = simulate_cvd(true_hex, mode)
                block.set_color(true_hex, display_hex=sim_hex)

    # --- FILE I/O ---
    def load_json(self):
        """Loads a JSON palette directly into Tab C (Custom Canvas)."""
        # FIX: Removed the Qt5-specific options to make it universal
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Palette", "", "JSON Files (*.json);;All Files (*)")
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                if "colors" in data:
                    new_colors = data["colors"]
                    
                    self.state.update_colors("C", new_colors)
                    
                    spin = self.tab_uis["C"]["spin"]
                    spin.blockSignals(True)
                    spin.setValue(len(new_colors))
                    spin.blockSignals(False)
                    
                    self.render_tab_blocks("C", is_editable=True)
                    print(f"MolNympheas: Loaded {len(new_colors)} colors into Custom Canvas.")
            except Exception as e:
                print(f"MolNympheas Error loading JSON: {e}")

    def save_json(self, tab_key):
        """Saves the active workspace's palette to a JSON file."""
        # FIX: Removed the Qt5-specific options to make it universal
        file_path, _ = QFileDialog.getSaveFileName(self, f"Save Tab {tab_key} Palette", "my_palette.json", "JSON Files (*.json);;All Files (*)")
        
        if file_path:
            try:
                colors = self.state.workspaces[tab_key]["colors"]
                data = {"colors": colors, "palette_name": f"molnympheas_tab_{tab_key}"}
                
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"MolNympheas: Saved {len(colors)} colors from Tab {tab_key} to {file_path}")
            except Exception as e:
                print(f"MolNympheas Error saving JSON: {e}")

    # --- THE BRIDGE (PHASE 4) ---
    def apply_to_environment(self):
        sele = self.target_combo.currentText()
        colors = self.state.colors
        
        if ENV == "pymol":
            # Example PyMOL logic: apply colors to chains or simply set the palette
            print(f"MolNympheas: Sending {len(colors)} colors to PyMOL selection '{sele}'")
            for i, h in enumerate(colors):
                color_name = f"molnym_{i}"
                r, g, b = tuple(int(h.lstrip('#')[j:j+2], 16)/255.0 for j in (0, 2, 4))
                cmd.set_color(color_name, [r, g, b])
            # If standard molecule, color by parts (example logic)
            cmd.color(f"molnym_0", sele) 
            
        elif ENV == "chimerax":
            print(f"MolNympheas: Applying to ChimeraX '{sele}'")
            # Example: Apply first color to selection to show it works
            # run(session, f"color {sele} {colors[0]}") 

        else:
            print(f"MolNympheas (Standalone): Would apply {colors} to {sele}")

    def create_divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line


    import struct

    def export_to_ase(self, tab_key):
        colors = self.state.workspaces[tab_key]["colors"]
        if not colors:
            print("MolNympheas: No colors to export.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export as Adobe Swatch (.ase)",
            "",
            "ASE Files (*.ase)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".ase"):
            file_path += ".ase"
        try:
            blocks = b''
            for hex_col in colors:
                # Validate color format
                if not isinstance(hex_col, str) or not hex_col.startswith("#") or len(hex_col) != 7:
                    print(f"Skipping invalid color: {hex_col}")
                    continue

                # Convert HEX → RGB float (0–1)
                r = int(hex_col[1:3], 16) / 255.0
                g = int(hex_col[3:5], 16) / 255.0
                b = int(hex_col[5:7], 16) / 255.0

                # Swatch name (UTF-16BE + null terminator)
                swatch_name = f"MolNympheas_{hex_col}"
                name_bytes = swatch_name.encode("utf-16be") + b'\x00\x00'

                # Number of UTF-16 characters INCLUDING null terminator
                name_len = len(name_bytes) // 2

                # Color data:
                # 4 bytes = color model ('RGB ')
                # 12 bytes = 3 floats
                # 2 bytes = color type
                color_data = (
                    b'RGB ' +
                    struct.pack(">fff", r, g, b) +
                    struct.pack(">H", 0)   # 0 = global
                )

                # Block payload
                block_payload = (
                    struct.pack(">H", name_len) +
                    name_bytes +
                    color_data
                )

                # Full block
                block = (
                    struct.pack(">H", 0x0001) +                # block type = color entry
                    struct.pack(">I", len(block_payload)) +    # payload length
                    block_payload
                )

                blocks += block

            # ASE Header
            header = (
                b'ASEF' +
                struct.pack(">H", 1) +    # version major
                struct.pack(">H", 0) +    # version minor
                struct.pack(">I", len(colors))
            )

            with open(file_path, "wb") as f:
                f.write(header + blocks)

            print(f"MolNympheas: ASE file saved successfully to {file_path}")

        except Exception as e:
            print(f"MolNympheas: ASE export failed: {e}")
# ==========================================
# LAUNCHER
# ==========================================

# ==========================================
def launch_app():
    app = QApplication.instance()
    is_standalone = False
    if app is None:
        app = QApplication(sys.argv)
        is_standalone = True

    global main_window 
    main_window = MolNympheasUI()
    
    # THE FIX: Attach the window to the running application so 
    # ChimeraX's garbage collector doesn't instantly destroy it!
    app._molnym_window = main_window 
    
    main_window.show()

    if is_standalone:
        if QT_VERSION == 5:
            sys.exit(app.exec_())
        else:
            sys.exit(app.exec())

# Force launch in ChimeraX, or check if main in PyMOL/Standalone
if __name__ in ("__main__", "pymol") or ENV == "chimerax":
    launch_app()

# Bind for PyMOL Plugin menu
if ENV == "pymol":
    def __init_plugin__(app=None):
        from pymol.plugins import addmenuitemqt
        addmenuitemqt('MolNympheas Pro', launch_app)
