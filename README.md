# 🎨 MolNympheas: A Smart Color Palette Picker for PyMOL and ChimeraX and in between

**MolNympheas** is a  plugin designed to bring mathematically perfect, colorblind-friendly palettes to your structural biology figures.

Instead of guessing hex codes or using default PyMOL or chimeraX rainbows, this tool uses Matplotlib to let you smoothly slide through perceptually uniform palettes (like *Viridis*, *Turbo*, *Plasma*, etc.) and automatically calculates the highest-contrast complementary colors for your complexes.

<img width="512" height="681" alt="image" src="https://github.com/user-attachments/assets/e3956c37-c476-4f52-a2b6-120c23a8ed8f" />

# ✨ Features
* **Universal Cross-Compatibility:** Export your exact color scheme to a `.json` file in PyMOL and load it directly into ChimeraX (and vice versa)! The shared save format makes it effortless to keep your visual identity consistent across different software.
* **Selection:** The **"Apply to"** dropdown automatically detects all loaded objects and models in your session. You can easily pick from the list, type a custom selection on the fly, and use the ↻ refresh button to instantly update the list without restarting the plugin.
* **Smart Contrast:** Click `+ Add Color` to automatically generate perfectly spaced, highly contrasting colors from your chosen palette.
* **Custom Hex:** Have a specific brand or lab color? Type it in, and the plugin will build a mathematically contrasting palette around it.
* **Massive Library:** Comes with the standard BIDS/Google colormaps, plus a button to unlock 80+ additional [Matplotlib palettes](https://matplotlib.org/stable/users/explain/colors/colormaps.html)

## 📥 Installation
* **Pymol**
1. Download the `MolNympheas.py` file to your computer.
2. Open PyMOL.
3. In the PyMOL command line, run the script:
   ```pymol
   run /path/to/molnympheas.py
   
* **ChimeraX**
1. Download the `MolXNympheas.py` file to your computer.
2. Open chimeraX
3. In the chimeraX command line, run the script:
   ```chimeraX
   open /path/to/MolXNympheas.py   

## Why the name?
Named in honor of Claude Monet's *Nymphéas* (Water Lilies) and his mastery of visual perception 
  
## Thanks to
* Gemini, as i'm still a "tanche" in python
* Shyam Saladi, whose original pymol_viridis script (go visit his github) served as the starting inspiration for this project.

## Licence
Do whatever you want with the scripts and keep in mind that it has been code by a stupid biochemist (for that matter me).
