'''
==============================================================================
MolNympheas: A Smart Color Palette Picker for PyMOL
==============================================================================

DESCRIPTION
    MolNympheas is a PyMOL plugin designed to bring mathematically perfect, 
    palettes to your structural biology figures. 
    Named in honor of Claude Monet's "Nymphéas" (Water Lilies), this tool 
    uses Matplotlib to generate perceptually uniform colors (Viridis, Turbo, 
    Plasma, etc.) and automatically calculates high-contrast complementary 
    colors for complex assemblies.

FEATURES
    - PyQt5 Graphical User Interface (GUI)
    - Dynamic high-contrast color generation
    - Custom Hex code input with automatic hue-shifting
    - Save & Load palette configurations via JSON
    - Access to 80+ Matplotlib scientific colormaps

USAGE
    In the PyMOL command line, run:
        run /path/to/molnympheas.py
   First time you might need to install matplotlib directly in pymol
       pip install matplotlib
   
v2: 02/03/26
- Colorblind Accessibility (CVD Matrix) thanks to Florain Chenavier
- modify button to allow to use your own color or to remove the color (Thx Flo) from the palette or put back the default one 

INSPIRATION
    Initially inspired by the `pymol_viridis` script by Shyam Saladi.
==============================================================================
'''

import pymol
from pymol import cmd

try:
    from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, 
                                 QComboBox, QLineEdit, QPushButton, QLabel, 
                                 QSlider, QFrame, QGridLayout, QFileDialog, 
                                 QTableWidget, QTableWidgetItem, QTabWidget)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QPalette
except ImportError:
    from PyQt5.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, 
                                 QComboBox, QLineEdit, QPushButton, QLabel, 
                                 QSlider, QFrame, QGridLayout, QFileDialog, 
                                 QTableWidget, QTableWidgetItem, QTabWidget)
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QPalette

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import colorsys
import json
import numpy as np


# --- SIMULATION MATRIX FOR PROTANOPIA AND DEUTERANOPIA ---
PROTANOPIA_MATRIX = np.array([
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281,  0.099216],
    [-0.003882, -0.048116, 1.051998]
])

DEUTERANOPIA_MATRIX = np.array([
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501,  0.047413],
    [-0.011820, 0.042940, 0.968881]
])

# --- WIDGET FOR COLORED MATRIX HEADER ---
class ColorHeaderWidget(QWidget):
    def __init__(self, hex_color):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        color_box = QLabel()
        color_box.setFixedSize(16, 16)
        color_box.setStyleSheet(f"""
            background-color: {hex_color};
            border: 1px solid #444;
            border-radius: 3px;
        """)
        label = QLabel(hex_color)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)

        layout.addWidget(color_box)
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)

# --- DIALOG TO ADD EXTRA PALETTES ---
class AddPaletteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Matplotlib Palette")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        link_lbl = QLabel('<a href="https://matplotlib.org/stable/users/explain/colors/colormaps.html">🌐 View Matplotlib Colormap Reference Online</a>')
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)
        layout.addWidget(link_lbl)
        
        layout.addWidget(QLabel("Select a palette to add to your list:"))
        self.combo = QComboBox()
        self.combo.addItems(sorted(plt.colormaps()))
        layout.addWidget(self.combo)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Add Palette")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_selected(self):
        return self.combo.currentText()

# --- NEW DIALOG TO MODIFY INDIVIDUAL BLOCKS ---
class ModifyColorDialog(QDialog):
    def __init__(self, current_hex, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modify Color Block")
        self.action = None
        self.new_hex = current_hex
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Set Custom Hex for this block:"))
        self.hex_input = QLineEdit(current_hex)
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)
        layout.addWidget(self.hex_input)
        
        btn_update = QPushButton("✅ Lock Custom Hex")
        btn_update.clicked.connect(self.do_update)
        layout.addWidget(btn_update)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine if hasattr(QFrame, 'Shape') else QFrame.HLine)
        layout.addWidget(line)
        
        btn_auto = QPushButton("🔄 Revert to Auto (Follow Slider)")
        btn_auto.clicked.connect(self.do_auto)
        layout.addWidget(btn_auto)
        
        btn_remove = QPushButton("❌ Remove this Color")
        btn_remove.setStyleSheet("background-color: #ffdddd; color: #aa0000;")
        btn_remove.clicked.connect(self.do_remove)
        layout.addWidget(btn_remove)
        
        self.setLayout(layout)

    def do_update(self):
        self.action = "update"
        self.new_hex = self.hex_input.text()
        self.accept()

    def do_auto(self):
        self.action = "auto"
        self.accept()

    def do_remove(self):
        self.action = "remove"
        self.accept()

# --- MAIN APPLICATION DIALOG ---
class ColorPickerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MolNympheas - PyMOL")
        self.setMinimumWidth(400)
        
        self.custom_hex_mode = False
        self.custom_main_hex = "#000000"

        # --- TOP LEVEL LAYOUT ---
        main_dialog_layout = QVBoxLayout()
        
        # Save / Load Menu
        file_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Palette")
        self.save_btn.clicked.connect(self.save_palette)
        self.load_btn = QPushButton("📂 Load Palette")
        self.load_btn.clicked.connect(self.load_palette)
        file_layout.addWidget(self.save_btn)
        file_layout.addWidget(self.load_btn)
        main_dialog_layout.addLayout(file_layout)

        # --- TAB WIDGET ---
        self.tabs = QTabWidget()
        main_dialog_layout.addWidget(self.tabs)
        
        self.tab_palette = QWidget()
        self.tab_matrix = QWidget()
        
        self.tabs.addTab(self.tab_palette, "🎨 Palette Builder")
        self.tabs.addTab(self.tab_matrix, "👁️ CVD Matrix")

        # ==========================================
        # TAB 1: PALETTE BUILDER
        # ==========================================
        pal_tab_layout = QVBoxLayout()

        # Selection Input
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Apply to:"))
        self.sel_combo = QComboBox()
        self.sel_combo.setEditable(True)
        self.update_selection_list()
        sel_layout.addWidget(self.sel_combo)
        
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedWidth(35)
        self.refresh_btn.clicked.connect(self.update_selection_list)
        sel_layout.addWidget(self.refresh_btn)
        pal_tab_layout.addLayout(sel_layout)

        # Palette Dropdown
        pal_layout = QHBoxLayout()
        pal_layout.addWidget(QLabel("Palette:"))
        self.pal_combo = QComboBox()
        self.pal_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'cividis', 'turbo'])
        self.pal_combo.currentIndexChanged.connect(self.on_palette_changed)
        pal_layout.addWidget(self.pal_combo)
        
        self.add_pal_btn = QPushButton("➕ Add More...")
        self.add_pal_btn.clicked.connect(self.add_custom_palette)
        pal_layout.addWidget(self.add_pal_btn)
        pal_tab_layout.addLayout(pal_layout)

        # Visual Gradient Bar
        pal_tab_layout.addWidget(QLabel("Pick shade (or enter custom Hex below):"))
        self.gradient_bar = QLabel()
        self.gradient_bar.setFixedHeight(12)
        pal_tab_layout.addWidget(self.gradient_bar)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal if hasattr(Qt, 'Orientation') else Qt.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.valueChanged.connect(self.on_slider_moved)
        pal_tab_layout.addWidget(self.slider)

        # Preview & Hex
        preview_layout = QHBoxLayout()
        self.hex_input = QLineEdit()
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)
        self.hex_input.setFixedWidth(80)
        self.hex_input.editingFinished.connect(self.on_hex_entered)
        
        self.preview = QLabel()
        self.preview.setFixedSize(120, 50)
        self.preview.setAutoFillBackground(True)
        
        preview_layout.addStretch()
        preview_layout.addWidget(self.hex_input)
        preview_layout.addWidget(self.preview)
        preview_layout.addStretch()
        pal_tab_layout.addLayout(preview_layout)
        
        # Apply Main Button
        self.apply_btn = QPushButton("Apply Main Color")
        self.apply_btn.clicked.connect(self.apply_main_color)
        pal_tab_layout.addWidget(self.apply_btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine if hasattr(QFrame, 'Shape') else QFrame.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken if hasattr(QFrame, 'Shadow') else QFrame.Sunken)
        pal_tab_layout.addWidget(line)

        # Suggestions Header
        sugg_header_layout = QHBoxLayout()
        sugg_header_layout.addWidget(QLabel("Suggested Distinct Colors:"))
        self.add_sugg_btn = QPushButton("+ Add Color")
        self.add_sugg_btn.setFixedWidth(100)
        self.add_sugg_btn.clicked.connect(lambda: self.add_suggestion_block(update_ui=True))
        sugg_header_layout.addWidget(self.add_sugg_btn)
        pal_tab_layout.addLayout(sugg_header_layout)

        # Suggestions Grid
        self.sugg_grid = QGridLayout()
        pal_tab_layout.addLayout(self.sugg_grid)
        self.sugg_blocks = []
        self.sugg_labels = []
        self.current_sugg_vals = []
        self.sugg_custom_hex = [] 
        
        self.tab_palette.setLayout(pal_tab_layout)

        # ==========================================
        # TAB 2: CVD MATRIX
        # ==========================================
        matrix_tab_layout = QVBoxLayout()
        self.cvd_mode = QComboBox()
        self.cvd_mode.addItems(["Normal Vision", "Protanopia", "Deuteranopia"])
        self.cvd_mode.currentIndexChanged.connect(self.update_matrix_table)
        matrix_tab_layout.addWidget(QLabel("Select Vision Simulation:"))
        matrix_tab_layout.addWidget(self.cvd_mode)
        
        matrix_tab_layout.addWidget(QLabel("RGB Distance Matrix (Values < 0.15 are too similar):"))        
        self.matrix_table = QTableWidget()
        self.matrix_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers if hasattr(QTableWidget, 'EditTrigger') else QTableWidget.NoEditTriggers)
        self.matrix_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection if hasattr(QTableWidget, 'SelectionMode') else QTableWidget.NoSelection)
        self.matrix_table.setAlternatingRowColors(True)
        self.matrix_table.setShowGrid(True)     

        self.matrix_table.setStyleSheet("""
        QTableWidget { border: 2px solid #444; border-radius: 6px; background-color: #ffffff; gridline-color: #cccccc; }
        """)        
        matrix_tab_layout.addWidget(self.matrix_table)
        self.tab_matrix.setLayout(matrix_tab_layout)

        # Initialize Default State
        self.setLayout(main_dialog_layout)
        
        for _ in range(3):
            self.add_suggestion_block(update_ui=False)
            
        self.update_gradient_bar()
        self.update_preview()
        
        self.tabs.currentChanged.connect(self.update_matrix_table)

    # --- MATRIX LOGIC ---
    def simulate_cvd(self, rgb, matrix):
        sim = matrix.dot(rgb)
        sim = np.clip(sim, 0, 1)
        return sim

    def compute_rgb_distance_matrix(self, mode="normal"):
        hex_colors = []
        if self.custom_hex_mode:
            hex_colors.append(self.custom_main_hex)
        else:
            _, main_hex = self.get_color_from_val(self.slider.value())
            hex_colors.append(main_hex)

        for val in self.current_sugg_vals:
            if isinstance(val, str):
                hex_colors.append(val)
            else:
                _, h = self.get_color_from_val(val)
                hex_colors.append(h)

        rgbs = [np.array(mcolors.to_rgb(h)) for h in hex_colors]
        if mode == "protanopia":
            rgbs = [self.simulate_cvd(rgb, PROTANOPIA_MATRIX) for rgb in rgbs]
        elif mode == "deuteranopia":
            rgbs = [self.simulate_cvd(rgb, DEUTERANOPIA_MATRIX) for rgb in rgbs]

        n = len(rgbs)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                matrix[i, j] = np.linalg.norm(rgbs[i] - rgbs[j])

        return matrix, hex_colors

    def update_matrix_table(self):
        mode_map = {0: "normal", 1: "protanopia", 2: "deuteranopia"}
        matrix, hex_colors = self.compute_rgb_distance_matrix(mode=mode_map[self.cvd_mode.currentIndex()])

        n = len(hex_colors)
        self.matrix_table.setRowCount(n + 1)
        self.matrix_table.setColumnCount(n + 1)
        self.matrix_table.horizontalHeader().setVisible(False)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.setItem(0, 0, QTableWidgetItem(""))

        for i, hex_color in enumerate(hex_colors):
            self.matrix_table.setCellWidget(0, i + 1, ColorHeaderWidget(hex_color))
            self.matrix_table.setCellWidget(i + 1, 0, ColorHeaderWidget(hex_color))

        for i in range(n):
            for j in range(n):
                value = matrix[i, j]
                item = QTableWidgetItem(f"{value:.3f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)

                if i == j:
                    item.setBackground(QColor("#eeeeee"))
                elif value < 0.15:
                    item.setBackground(QColor("#ff9999")) # Too close
                elif value < 0.30:
                    item.setBackground(QColor("#ffe599")) # Caution
                else:
                    item.setBackground(QColor("#b6fcb6")) # Good contrast

                self.matrix_table.setItem(i + 1, j + 1, item)

        self.matrix_table.resizeColumnsToContents()
        self.matrix_table.resizeRowsToContents()

    # --- PALETTE UI LOGIC ---
    def add_custom_palette(self):
        dlg = AddPaletteDialog(self)
        if dlg.exec() if hasattr(dlg, 'exec') else dlg.exec_() == QDialog.DialogCode.Accepted if hasattr(QDialog, 'DialogCode') else QDialog.Accepted:
            new_pal = dlg.get_selected()
            idx = self.pal_combo.findText(new_pal)
            if idx == -1:
                self.pal_combo.addItem(new_pal)
                idx = self.pal_combo.count() - 1
            self.pal_combo.setCurrentIndex(idx)

    def save_palette(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Palette", "my_palette", "JSON Files (*.json);;All Files (*)")
        if file_name:
            if not file_name.endswith('.json'): file_name += '.json'
            data = {
                "custom_hex_mode": self.custom_hex_mode,
                "custom_main_hex": self.custom_main_hex,
                "palette_name": self.pal_combo.currentText(),
                "slider_value": self.slider.value(),
                "num_suggestions": len(self.sugg_blocks),
                "sugg_custom_hex": self.sugg_custom_hex # Save locked colors!
            }
            try:
                with open(file_name, 'w') as f: json.dump(data, f, indent=4)
                print(f"MolNympheas: Palette saved successfully to {file_name}")
            except Exception as e:
                print(f"Error saving file: {e}")

    def load_palette(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Palette", "", "JSON Files (*.json);;All Files (*)")
        if file_name:
            try:
                with open(file_name, 'r') as f: data = json.load(f)
                self.custom_hex_mode = data.get("custom_hex_mode", False)
                self.custom_main_hex = data.get("custom_main_hex", "#000000")
                self.pal_combo.blockSignals(True)
                self.slider.blockSignals(True)
                
                saved_pal = data.get("palette_name", "viridis")
                if self.pal_combo.findText(saved_pal) == -1: self.pal_combo.addItem(saved_pal)
                self.pal_combo.setCurrentText(saved_pal)
                self.slider.setValue(data.get("slider_value", 0))
                
                self.pal_combo.blockSignals(False)
                self.slider.blockSignals(False)
                
                self.remove_all_suggestion_blocks()
                target_num = data.get("num_suggestions", 3)
                loaded_custom_hex = data.get("sugg_custom_hex", [None]*target_num)
                
                for i in range(target_num): 
                    self.add_suggestion_block(update_ui=False)
                    self.sugg_custom_hex[i] = loaded_custom_hex[i]
                    
                self.update_gradient_bar()
                self.update_preview()
            except Exception as e:
                print(f"Error loading file: {e}")

    # FIXED: A robust, recursive function to fully obliterate layouts
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.hide()           # Visually remove immediately
                    widget.deleteLater()    # Schedule memory clear
                    widget.setParent(None)  # Detach from hierarchy
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self.clear_layout(sub_layout) # Recursion!
                        sub_layout.deleteLater()
                        sub_layout.setParent(None)

    def remove_all_suggestion_blocks(self):
        self.clear_layout(self.sugg_grid) # Fully nukes the grid and everything inside it
        self.sugg_blocks.clear()
        self.sugg_labels.clear()
        self.current_sugg_vals.clear()
        self.sugg_custom_hex.clear()

    def update_selection_list(self):
        current_text = self.sel_combo.currentText()
        self.sel_combo.clear()
        names = ['all'] + cmd.get_names('public')
        self.sel_combo.addItems(names)
        if current_text:
            self.sel_combo.setCurrentText(current_text)
        else:
            self.sel_combo.setCurrentText("all")

    def get_color_from_val(self, val):
        norm_val = val / 255.0 
        cmap = cm.get_cmap(self.pal_combo.currentText())
        rgba = cmap(norm_val) 
        return rgba, mcolors.to_hex(rgba)

    def on_palette_changed(self):
        self.update_gradient_bar()
        if not self.custom_hex_mode: self.update_preview()

    def on_slider_moved(self):
        self.custom_hex_mode = False
        self.update_preview()

    def on_hex_entered(self):
        text = self.hex_input.text().strip()
        if not text.startswith('#'): text = '#' + text
        if mcolors.is_color_like(text):
            self.custom_hex_mode = True
            self.custom_main_hex = mcolors.to_hex(text).upper()
            self.hex_input.blockSignals(True)
            self.hex_input.setText(self.custom_main_hex)
            self.hex_input.blockSignals(False)
            self.update_preview()
        else:
            self.custom_hex_mode = False
            self.update_preview()

    def update_gradient_bar(self):
        cmap = cm.get_cmap(self.pal_combo.currentText())
        stops = [f"stop:{i/10.0} {mcolors.to_hex(cmap(i/10.0))}" for i in range(11)]
        gradient = f"qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, {', '.join(stops)})"
        self.gradient_bar.setStyleSheet(f"background: {gradient}; border: 1px solid #aaa; border-radius: 3px;")

    def add_suggestion_block(self, update_ui=True):
        idx = len(self.sugg_blocks)
        vbox = QVBoxLayout()
        lbl = QLabel("#000000")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)
        self.sugg_labels.append(lbl)
        vbox.addWidget(lbl)
        
        blk = QLabel()
        blk.setFixedSize(80, 40)
        blk.setAutoFillBackground(True)
        self.sugg_blocks.append(blk)
        vbox.addWidget(blk)
        
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(lambda checked, i=idx: self.apply_color(self.current_sugg_vals[i]))
        
        btn_modify = QPushButton("⚙️")
        btn_modify.setFixedWidth(25)
        btn_modify.setToolTip("Modify or Remove Color")
        btn_modify.clicked.connect(lambda checked, i=idx: self.modify_suggestion_block(i))
        
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_modify)
        vbox.addLayout(btn_layout) # This nested layout was the culprit!
        
        self.current_sugg_vals.append(0)
        self.sugg_custom_hex.append(None) # Not locked by default
        
        self.sugg_grid.addLayout(vbox, idx // 4, idx % 4)
        if update_ui: self.update_preview()

    def modify_suggestion_block(self, index):
        current_hex = self.sugg_labels[index].text()
        dlg = ModifyColorDialog(current_hex, self)
        res = dlg.exec() if hasattr(dlg, 'exec') else dlg.exec_()
        
        accepted_code = QDialog.DialogCode.Accepted if hasattr(QDialog, 'DialogCode') else QDialog.Accepted
        if res == accepted_code:
            if dlg.action == "remove":
                self.remove_suggestion_block(index)
            elif dlg.action == "auto":
                self.sugg_custom_hex[index] = None
                self.update_preview()
            elif dlg.action == "update":
                hx = dlg.new_hex.strip()
                if not hx.startswith('#'): hx = '#' + hx
                if mcolors.is_color_like(hx):
                    self.sugg_custom_hex[index] = mcolors.to_hex(hx).upper()
                    self.update_preview()

    def update_preview(self):
        num_colors = len(self.sugg_blocks) + 1
        
        # Determine Base HLS
        if self.custom_hex_mode:
            main_hex = self.custom_main_hex
            pal = self.preview.palette()
            pal.setColor(QPalette.ColorRole.Window if hasattr(QPalette, 'ColorRole') else QPalette.Window, QColor(main_hex))
            self.preview.setPalette(pal)
            h, l, s = colorsys.rgb_to_hls(*mcolors.to_rgb(main_hex))
            step_size = 1.0 / num_colors
            
            for i in range(len(self.sugg_blocks)):
                if self.sugg_custom_hex[i] is not None:
                    # Locked custom hex overrides auto-math
                    s_hex = self.sugg_custom_hex[i]
                else:
                    new_rgb = colorsys.hls_to_rgb((h + step_size * (i + 1)) % 1.0, l, s)
                    s_hex = mcolors.to_hex(new_rgb).upper()
                    
                self.current_sugg_vals[i] = s_hex 
                self.sugg_labels[i].setText(s_hex)
                s_pal = self.sugg_blocks[i].palette()
                s_pal.setColor(QPalette.ColorRole.Window if hasattr(QPalette, 'ColorRole') else QPalette.Window, QColor(s_hex))
                self.sugg_blocks[i].setPalette(s_pal)
        else:
            slider_val = self.slider.value()
            _, main_hex = self.get_color_from_val(slider_val)
            self.hex_input.blockSignals(True)
            self.hex_input.setText(main_hex.upper())
            self.hex_input.blockSignals(False)
            pal = self.preview.palette()
            pal.setColor(QPalette.ColorRole.Window if hasattr(QPalette, 'ColorRole') else QPalette.Window, QColor(main_hex))
            self.preview.setPalette(pal)
            step_size = 256 / num_colors
            
            for i in range(len(self.sugg_blocks)):
                if self.sugg_custom_hex[i] is not None:
                    # Locked custom hex overrides auto-math
                    s_hex = self.sugg_custom_hex[i]
                    self.current_sugg_vals[i] = s_hex 
                else:
                    sugg_val = int((slider_val + (step_size * (i + 1))) % 256)
                    self.current_sugg_vals[i] = sugg_val 
                    _, s_hex = self.get_color_from_val(sugg_val)
                    
                self.sugg_labels[i].setText(s_hex.upper())
                s_pal = self.sugg_blocks[i].palette()
                s_pal.setColor(QPalette.ColorRole.Window if hasattr(QPalette, 'ColorRole') else QPalette.Window, QColor(s_hex))
                self.sugg_blocks[i].setPalette(s_pal)
                
        if self.tabs.currentIndex() == 1:
            self.update_matrix_table()

    def remove_suggestion_block(self, index):
        if index >= len(self.sugg_blocks):
            return  

        # 1. Back up data minus the removed element
        old_count = len(self.sugg_blocks)
        old_vals = self.current_sugg_vals.copy()
        old_custom = self.sugg_custom_hex.copy()

        old_vals.pop(index)
        old_custom.pop(index)

        # 2. Fully clear the grid
        self.remove_all_suggestion_blocks()

        # 3. Rebuild the exact number of blocks needed
        for _ in range(old_count - 1):
            self.add_suggestion_block(update_ui=False)  

        # 4. Restore the saved values/custom hexes
        for i in range(len(old_vals)):
            self.current_sugg_vals[i] = old_vals[i] 
            self.sugg_custom_hex[i] = old_custom[i]

        # 5. Update GUI
        self.update_preview()

    def apply_main_color(self):
        self.apply_color(self.custom_main_hex if self.custom_hex_mode else self.slider.value())

    def apply_color(self, val_or_hex):
        # Handle custom Hex strings vs mapped Slider Ints
        if isinstance(val_or_hex, str) and val_or_hex.startswith('#'):
            hex_color = val_or_hex
            rgba = mcolors.to_rgba(hex_color)
            rgb = rgba[:3]
            color_name = f"custom_{hex_color.lstrip('#').lower()}"
        else:
            rgba, hex_color = self.get_color_from_val(val_or_hex)
            rgb = rgba[:3] 
            pal_name = self.pal_combo.currentText()
            color_name = f"{pal_name}_{val_or_hex}"
            
        sele = self.sel_combo.currentText()
        
        # PyMOL coloring commands
        cmd.set_color(color_name, list(rgb))
        cmd.color(color_name, sele)
        print(f"MolNympheas: Applied custom color '{color_name}' ({hex_color.upper()}) to '{sele}'.")

_color_dialog = None

def launch_color_picker():
    global _color_dialog
    if _color_dialog is None:
        _color_dialog = ColorPickerDialog()
    else:
        _color_dialog.update_selection_list()
    _color_dialog.show()
    _color_dialog.raise_()

cmd.extend('MolNympheas', launch_color_picker)

if __name__ == 'pymol':
    launch_color_picker()
