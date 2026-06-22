# 🎨 MolNympheas: A Smart Color Palette Picker for PyMOL and ChimeraX and in between

**MolNympheas** is a  plugin designed to bring mathematically perfect, palettes to your structural biology figures.

Instead of guessing hex codes or using default PyMOL or chimeraX rainbows, this tool uses Matplotlib to let you smoothly slide through perceptually uniform palettes (like *Viridis*, *Turbo*, *Plasma*, etc.) and automatically calculates the highest-contrast complementary colors for your complexes.

**PyMol**

<img width="1425" height="856" alt="image" src="https://github.com/user-attachments/assets/17421195-30e9-410c-ad8c-b9fefa92d0d1" />

**ChimeraX**

<img width="1424" height="834" alt="image" src="https://github.com/user-attachments/assets/d8025e20-06e6-48cf-8ca2-9d8970dc965b" />


## Version
13-03-26: 
           **v3.1.0**

            * - add a color picker tool
            
            * - add a gradient generator for custom color
22-06-2026: 
**V4.0.0** 

          The "Universal Workspace" Update
              - Refactored into three independent workspaces (Matplotlib/Harmony/Custom).
              - Added automated Color Clash Detection (Delta-E math) in CVD Matrix.
              - Added Okabe-Ito colorblind-safe preset.
              - Added Smart-Paste functionality for Hex codes.
              - Fixed UI rendering for macOS and cross-platform Qt compatibility.
                   
## ✨ Features
* **Universal Cross-Compatibility:** Export your exact color scheme to a `.json` file in PyMOL and load it directly into ChimeraX (and vice versa)! The shared save format makes it effortless to keep your visual identity consistent across different software.
* 
* **Colorblind Accessibility (CVD Matrix):** A dedicated tab calculates the RGB distance matrix between your selected colors, simulating Normal Vision, Protanopia, and Deuteranopia to ensure your figures are universally accessible.


<img width="703" height="813" alt="image" src="https://github.com/user-attachments/assets/bcc74e5b-9f63-4409-bb98-ad3772440394" />



* **Convenient Selection:** The **"Apply to"** dropdown automatically detects all loaded objects and models in your session. You can easily pick from the list, type a custom selection on the fly, and use the ↻ refresh button to instantly update the list without restarting the plugin.
* **Smart Contrast & Custom Overrides:** Click `+ Add Color` to automatically generate perfectly spaced colors from your chosen palette. Use the `⚙️` button on any generated color to lock in a specific, custom Hex code of your choice.
* **Massive Library:** Comes with the standard BIDS/Google colormaps, plus a button to unlock 80+ additional [Matplotlib palettes](https://matplotlib.org/stable/users/explain/colors/colormaps.html).

## 📥 Installation
* **Pymol**
1. Download the `MolNympheas.py` file to your computer.
2. Open PyMOL.
3. In the PyMOL command line, run the script:
   ```pymol
   run /path/to/MolNympheas.py

* NOTE :
  For the first time with PyMol you might need to install matplotlib in PyMol.
  To do so just type in the command line box at the bottom of the GUI (after "PyMol>") 

   ```pymol
   pip install matplotlib
     
* **ChimeraX**
1. Download the `MolNympheas.py` file to your computer.
2. Open chimeraX
3. In the chimeraX command line, run the script:
   ```chimeraX
   open /path/to/MolNympheas.py   

## Usage
* **Choose your palette**
   1. Either in the default list
   2. Or in the 80+ list from matplotlib
   3. Pick the shade
       
* **To apply the color**
  1. In the "Apply to" section choose the selection
  2. Click on the color box of your choice.
  3. If you make new selection or new object in the "Apply to" section click on the arrow to refresh the list.
  
## Why the name?
The idea came on a way back from Paris, on the train after visiting the Orsay museum. 
It has been named in honor of Claude Monet's *Nymphéas* (Water Lilies) and his mastery of visual perception 
  
## Thanks to
* Florian Chenavier for the implementation of the colorblind (CVD) simulation matrix, and the scripts unification (one script to rule them all!!).
* Gemini, as i'm still a "tanche" in python
* Shyam Saladi, whose original pymol_viridis script (go visit his github) served as the starting inspiration for this project.

## Licence
Do whatever you want with the scripts and keep in mind that it has been code by a stupid biochemist (for that matter me).
