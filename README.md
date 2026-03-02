# 🎨 MolNympheas: A Smart Color Palette Picker for PyMOL and ChimeraX and in between

**MolNympheas** is a  plugin designed to bring mathematically perfect, palettes to your structural biology figures.

Instead of guessing hex codes or using default PyMOL or chimeraX rainbows, this tool uses Matplotlib to let you smoothly slide through perceptually uniform palettes (like *Viridis*, *Turbo*, *Plasma*, etc.) and automatically calculates the highest-contrast complementary colors for your complexes.


PyMol
<img width="1433" height="862" alt="image" src="https://github.com/user-attachments/assets/9956af61-a892-4746-a969-0892017990ca" />


ChimeraX
<img width="1419" height="818" alt="image" src="https://github.com/user-attachments/assets/83446dff-d095-49ab-b9e1-a2bda2704d4b" />



## ✨ Features
* **Universal Cross-Compatibility:** Export your exact color scheme to a `.json` file in PyMOL and load it directly into ChimeraX (and vice versa)! The shared save format makes it effortless to keep your visual identity consistent across different software.
* **Colorblind Accessibility (CVD Matrix):** A dedicated tab calculates the RGB distance matrix between your selected colors, simulating Normal Vision, Protanopia, and Deuteranopia to ensure your figures are universally accessible.


<img width="615" height="305" alt="image" src="https://github.com/user-attachments/assets/4ebc4df2-7d08-44c8-ab10-72bf1fc2a045" />


* **Convenient Selection:** The **"Apply to"** dropdown automatically detects all loaded objects and models in your session. You can easily pick from the list, type a custom selection on the fly, and use the ↻ refresh button to instantly update the list without restarting the plugin.
* **Smart Contrast & Custom Overrides:** Click `+ Add Color` to automatically generate perfectly spaced colors from your chosen palette. Use the `⚙️` button on any generated color to lock in a specific, custom Hex code of your choice.
* **Massive Library:** Comes with the standard BIDS/Google colormaps, plus a button to unlock 80+ additional [Matplotlib palettes](https://matplotlib.org/stable/users/explain/colors/colormaps.html).

## 📥 Installation
* **Pymol**
1. Download the `MolNympheas.py` file to your computer.
2. Open PyMOL.
3. For the first time you might need to install matplotlib in pymol.

   To do so just type in the excution box at the bottom 
   ```pymol
   pip install matplotlib
   
4. In the PyMOL command line, run the script:
   ```pymol
   run /path/to/MolNympheas.py
   
* **ChimeraX**
1. Download the `MolXNympheas.py` file to your computer.
2. Open chimeraX
3. In the chimeraX command line, run the script:
   ```chimeraX
   open /path/to/MolXNympheas.py   

## Why the name?
Named in honor of Claude Monet's *Nymphéas* (Water Lilies) and his mastery of visual perception 
  
## Thanks to
* Florian Chenavier for the implementation of the colorblind (CVD) simulation matrix.
* Gemini, as i'm still a "tanche" in python
* Shyam Saladi, whose original pymol_viridis script (go visit his github) served as the starting inspiration for this project.

## Licence
Do whatever you want with the scripts and keep in mind that it has been code by a stupid biochemist (for that matter me).
