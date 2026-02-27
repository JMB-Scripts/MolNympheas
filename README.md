# 🎨 MolNympheas: A Smart Color Palette Picker for PyMOL

**MolNympheas** is a PyMOL plugin designed to bring mathematically perfect, colorblind-friendly palettes to your structural biology figures.

Instead of guessing hex codes or using default PyMOL rainbows, this tool uses Matplotlib to let you smoothly slide through perceptually uniform palettes (like *Viridis*, *Turbo*, *Plasma*, etc.) and automatically calculates the highest-contrast complementary colors for your complexes.

<img width="512" height="681" alt="image" src="https://github.com/user-attachments/assets/e3956c37-c476-4f52-a2b6-120c23a8ed8f" />


## ✨ Features
* **Smart Contrast:** Click `+ Add Color` to automatically generate perfectly spaced, highly contrasting colors from your chosen palette.
* **Accessible:** Uses scientifically designed, colorblind-friendly colormaps.
* **Custom Hex:** Have a specific brand or lab color? Type it in, and the plugin will build a contrasting palette around it.
* **Save & Load:** Export your exact color scheme to a `.json` file and load it back instantly in future PyMOL sessions.
* **Massive Library:** Comes with the standard BIDS/Google colormaps, plus a button to unlock 80+ additional [Matplotlib palettes](https://matplotlib.org/stable/users/explain/colors/colormaps.html).

## 📥 Installation

1. Download the `molnympheas.py` file to your computer.
2. Open PyMOL.
3. In the PyMOL command line, run the script:
   ```pymol
   run /path/to/molnympheas.py

  Named in honor of Claude Monet's *Nymphéas* (Water Lilies) and his mastery of visual perception 
  
## Thanks to
* Gemini, as i'm still a "tanche" in python
* pymol_viridis` script by Shyam Saladi.
