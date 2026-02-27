'''
==============================================================================
MolNympheas: A Smart Color Palette Picker for PyMOL
==============================================================================

DESCRIPTION
    MolNympheas is a PyMOL plugin designed to bring mathematically perfect, 
    colorblind-friendly palettes to your structural biology figures. 
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
    
    If the window is closed, reopen it by typing:
        molnympheas

INSPIRATION
    Initially inspired by the `pymol_viridis` script by Shyam Saladi.
==============================================================================
'''
import pymol
from pymol import cmd

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QPushButton, QLabel, QSlider, QFrame, QGridLayout, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt # Added for universal colormap fetching
import colorsys
import json

# --- NEW DIALOG FOR ADDING EXTRA PALETTES ---
class AddPaletteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Matplotlib Palette")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Clickable link to see examples
        link_lbl = QLabel('<a href="https://matplotlib.org/stable/users/explain/colors/colormaps.html">🌐 View Matplotlib Colormap Reference Online</a>')
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(link_lbl)
        
        layout.addWidget(QLabel("Select a palette to add to your list:"))
        
        self.combo = QComboBox()
        
        # BUG FIX: Use pyplot's universal function to get colormaps safely across all versions
        all_cmaps = plt.colormaps()
            
        # Sort them alphabetically for easier finding
        self.combo.addItems(sorted(all_cmaps))
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

# --- MAIN APPLICATION DIALOG ---
class ColorPickerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MolNympheas")
        self.setMinimumWidth(400)
        
        self.custom_hex_mode = False
        self.custom_main_hex = "#000000"

        layout = QVBoxLayout()
        
        # 0. Save / Load Menu
        file_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Palette")
        self.save_btn.clicked.connect(self.save_palette)
        self.load_btn = QPushButton("📂 Load Palette")
        self.load_btn.clicked.connect(self.load_palette)
        file_layout.addWidget(self.save_btn)
        file_layout.addWidget(self.load_btn)
        layout.addLayout(file_layout)

        # --- Divider ---
        line0 = QFrame()
        line0.setFrameShape(QFrame.HLine)
        line0.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line0)

        # 1. Selection Input
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Apply to:"))
        
        self.sel_combo = QComboBox()
        self.sel_combo.setEditable(True)
        self.update_selection_list()
        sel_layout.addWidget(self.sel_combo)
        
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedWidth(35)
        self.refresh_btn.setToolTip("Refresh list of objects/selections")
        self.refresh_btn.clicked.connect(self.update_selection_list)
        sel_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(sel_layout)

        # 2. Palette Dropdown & "Add More" Button
        pal_layout = QHBoxLayout()
        pal_layout.addWidget(QLabel("Palette:"))
        
        self.pal_combo = QComboBox()
        self.pal_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'cividis', 'turbo'])
        self.pal_combo.currentIndexChanged.connect(self.on_palette_changed)
        pal_layout.addWidget(self.pal_combo)
        
        self.add_pal_btn = QPushButton("➕ Add More...")
        self.add_pal_btn.setToolTip("Browse and add more Matplotlib palettes")
        self.add_pal_btn.clicked.connect(self.add_custom_palette)
        pal_layout.addWidget(self.add_pal_btn)
        
        layout.addLayout(pal_layout)

        # 3. Visual Gradient Bar
        layout.addWidget(QLabel("Pick shade (or enter custom Hex below):"))
        self.gradient_bar = QLabel()
        self.gradient_bar.setFixedHeight(12)
        layout.addWidget(self.gradient_bar)

        # 4. Slider for Color Index
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.valueChanged.connect(self.on_slider_moved)
        layout.addWidget(self.slider)

        # 5. Main Color Preview Box & Editable Hex Input
        preview_layout = QHBoxLayout()
        
        self.hex_input = QLineEdit()
        self.hex_input.setAlignment(Qt.AlignCenter)
        self.hex_input.setFixedWidth(80)
        self.hex_input.setToolTip("Type a custom Hex code and press Enter")
        self.hex_input.editingFinished.connect(self.on_hex_entered)
        
        self.preview = QLabel()
        self.preview.setFixedSize(120, 50)
        self.preview.setAutoFillBackground(True)
        
        preview_layout.addStretch()
        preview_layout.addWidget(self.hex_input)
        preview_layout.addWidget(self.preview)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)
        
        # 6. Apply Main Button
        self.apply_btn = QPushButton("Apply Main Color")
        self.apply_btn.clicked.connect(self.apply_main_color)
        layout.addWidget(self.apply_btn)

        # --- Divider ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 7. Suggested Distinct Colors Header
        sugg_header_layout = QHBoxLayout()
        sugg_header_layout.addWidget(QLabel("Suggested Distinct Colors:"))
        
        self.add_sugg_btn = QPushButton("+ Add Color")
        self.add_sugg_btn.setFixedWidth(100)
        self.add_sugg_btn.clicked.connect(lambda: self.add_suggestion_block(update_ui=True))
        sugg_header_layout.addWidget(self.add_sugg_btn)
        
        layout.addLayout(sugg_header_layout)

        # 8. Grid Layout for Suggestions
        self.sugg_grid = QGridLayout()
        layout.addLayout(self.sugg_grid)
        
        self.sugg_blocks = []
        self.sugg_labels = []
        self.current_sugg_vals = []
        
        # Initialize with 3 suggestions
        for _ in range(3):
            self.add_suggestion_block(update_ui=False)
            
        self.setLayout(layout)
        self.update_gradient_bar()
        self.update_preview()

    # --- ADD CUSTOM PALETTE ---
    def add_custom_palette(self):
        dlg = AddPaletteDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            new_pal = dlg.get_selected()
            
            idx = self.pal_combo.findText(new_pal)
            if idx == -1:
                self.pal_combo.addItem(new_pal)
                idx = self.pal_combo.count() - 1
                
            self.pal_combo.setCurrentIndex(idx)

    # --- SAVE / LOAD FUNCTIONALITY ---
    def save_palette(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Palette", "my_palette", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            if not file_name.endswith('.json'):
                file_name += '.json'
                
            data = {
                "custom_hex_mode": self.custom_hex_mode,
                "custom_main_hex": self.custom_main_hex,
                "palette_name": self.pal_combo.currentText(),
                "slider_value": self.slider.value(),
                "num_suggestions": len(self.sugg_blocks)
            }
            try:
                with open(file_name, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"PyMOL Color Picker: Palette saved successfully to {file_name}")
            except Exception as e:
                print(f"PyMOL Color Picker Error saving file: {e}")

    def load_palette(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Palette", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)
                
                self.custom_hex_mode = data.get("custom_hex_mode", False)
                self.custom_main_hex = data.get("custom_main_hex", "#000000")
                
                self.pal_combo.blockSignals(True)
                self.slider.blockSignals(True)
                
                saved_pal = data.get("palette_name", "viridis")
                if self.pal_combo.findText(saved_pal) == -1:
                    self.pal_combo.addItem(saved_pal)
                
                self.pal_combo.setCurrentText(saved_pal)
                self.slider.setValue(data.get("slider_value", 0))
                
                self.pal_combo.blockSignals(False)
                self.slider.blockSignals(False)
                
                target_num = data.get("num_suggestions", 3)
                self.remove_all_suggestion_blocks()
                for _ in range(target_num):
                    self.add_suggestion_block(update_ui=False)
                
                self.update_gradient_bar()
                self.update_preview()
                print(f"PyMOL Color Picker: Palette loaded successfully from {file_name}")
                
            except Exception as e:
                print(f"PyMOL Color Picker Error loading file: {e}")

    def remove_all_suggestion_blocks(self):
        for i in reversed(range(self.sugg_grid.count())):
            item = self.sugg_grid.itemAt(i)
            if item.layout():
                vbox = item.layout()
                while vbox.count():
                    child = vbox.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                vbox.deleteLater()
        
        self.sugg_blocks.clear()
        self.sugg_labels.clear()
        self.current_sugg_vals.clear()

    # --- STANDARD FUNCTIONALITY ---
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
        pal_name = self.pal_combo.currentText()
        norm_val = val / 255.0 
        cmap = cm.get_cmap(pal_name)
        rgba = cmap(norm_val) 
        hex_color = mcolors.to_hex(rgba) 
        return rgba, hex_color

    def on_palette_changed(self):
        self.update_gradient_bar()
        if not self.custom_hex_mode:
            self.update_preview()

    def on_slider_moved(self):
        self.custom_hex_mode = False
        self.update_preview()

    def on_hex_entered(self):
        text = self.hex_input.text().strip()
        if not text.startswith('#'):
            text = '#' + text
            
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
        pal_name = self.pal_combo.currentText()
        cmap = cm.get_cmap(pal_name)
        stops = []
        for i in range(11):
            val = i / 10.0
            rgba = cmap(val)
            hex_c = mcolors.to_hex(rgba)
            stops.append(f"stop:{val} {hex_c}")
            
        gradient = f"qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, {', '.join(stops)})"
        self.gradient_bar.setStyleSheet(f"background: {gradient}; border: 1px solid #aaa; border-radius: 3px;")

    def add_suggestion_block(self, update_ui=True):
        idx = len(self.sugg_blocks)
        vbox = QVBoxLayout()
        
        lbl = QLabel("#000000")
        lbl.setAlignment(Qt.AlignCenter)
        self.sugg_labels.append(lbl)
        vbox.addWidget(lbl)
        
        blk = QLabel()
        blk.setFixedSize(80, 40)
        blk.setAutoFillBackground(True)
        self.sugg_blocks.append(blk)
        vbox.addWidget(blk)
        
        btn = QPushButton("Apply")
        btn.clicked.connect(lambda checked, i=idx: self.apply_color(self.current_sugg_vals[i]))
        vbox.addWidget(btn)
        
        self.current_sugg_vals.append(0)
        
        row = idx // 4
        col = idx % 4
        self.sugg_grid.addLayout(vbox, row, col)
        
        if update_ui:
            self.update_preview()

    def update_preview(self):
        num_colors = len(self.sugg_blocks) + 1

        if self.custom_hex_mode:
            main_hex = self.custom_main_hex
            pal = self.preview.palette()
            pal.setColor(QPalette.Window, QColor(main_hex))
            self.preview.setPalette(pal)
            
            rgb = mcolors.to_rgb(main_hex)
            h, l, s = colorsys.rgb_to_hls(*rgb)
            step_size = 1.0 / num_colors

            for i in range(len(self.sugg_blocks)):
                new_h = (h + step_size * (i + 1)) % 1.0
                new_rgb = colorsys.hls_to_rgb(new_h, l, s)
                s_hex = mcolors.to_hex(new_rgb).upper()
                
                self.current_sugg_vals[i] = s_hex 
                
                self.sugg_labels[i].setText(s_hex)
                s_pal = self.sugg_blocks[i].palette()
                s_pal.setColor(QPalette.Window, QColor(s_hex))
                self.sugg_blocks[i].setPalette(s_pal)
                
        else:
            slider_val = self.slider.value()
            _, main_hex = self.get_color_from_val(slider_val)
            
            self.hex_input.blockSignals(True)
            self.hex_input.setText(main_hex.upper())
            self.hex_input.blockSignals(False)
            
            pal = self.preview.palette()
            pal.setColor(QPalette.Window, QColor(main_hex))
            self.preview.setPalette(pal)

            step_size = 256 / num_colors
            
            for i in range(len(self.sugg_blocks)):
                sugg_val = int((slider_val + (step_size * (i + 1))) % 256)
                
                self.current_sugg_vals[i] = sugg_val 
                
                _, s_hex = self.get_color_from_val(sugg_val)
                self.sugg_labels[i].setText(s_hex.upper())
                
                s_pal = self.sugg_blocks[i].palette()
                s_pal.setColor(QPalette.Window, QColor(s_hex))
                self.sugg_blocks[i].setPalette(s_pal)

    def apply_main_color(self):
        if self.custom_hex_mode:
            self.apply_color(self.custom_main_hex)
        else:
            self.apply_color(self.slider.value())

    def apply_color(self, val_or_hex):
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
        
        cmd.set_color(color_name, list(rgb))
        cmd.color(color_name, sele)
        print(f"Applied custom color '{color_name}' ({hex_color.upper()}) to '{sele}'.")

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
