# 🎨 MolNympheas: A Smart Color Palette Picker for PyMOL and ChimeraX and in between

**MolNympheas** is a  plugin designed to bring mathematically perfect, palettes to your structural biology figures.

Instead of guessing hex codes or using default PyMOL or chimeraX rainbows, this tool uses Matplotlib to let you smoothly slide through perceptually uniform palettes (like *Viridis*, *Turbo*, *Plasma*, etc.) and automatically calculates the highest-contrast complementary colors for your complexes.

**PyMol**

<img width="956" height="385" alt="image" src="https://github.com/user-attachments/assets/781a7d31-6f5e-4045-b53c-1d4b15e0f564" />

**ChimeraX**

<img width="956" height="385" alt="image" src="https://github.com/user-attachments/assets/d79351f0-14cb-4b06-b1c3-23e928bbdb49" />


## Version

**v3.1.0**

            * - add a color picker tool
            
            * - add a gradient generator for custom color

**V4.0.0** 

    - Refactored into three independent workspaces (Matplotlib/Harmony/Custom).
    - Added automated Color Clash Detection (Delta-E math) in CVD Matrix.
    - Added Okabe-Ito colorblind-safe preset.
    - Added Smart-Paste functionality for Hex codes.
    - Fixed UI rendering for macOS and cross-platform Qt compatibility.
    - Added Illustrator palette export ".ase"
    
**V5.0.0** 

(The PyMeraX Integration)
    - Integrated the PyMeraX engine to bring ChimeraX-like rendering directly into PyMOL.
    - Added a dynamic "Tab D: PyMeraX" that exclusively loads in PyMOL or Standalone modes.
    - Included 1-click GUI buttons for Cartoon, Surface, Publication, and Ligand rendering presets.
 
 **V6.0.0**
 
The "Water Lily" Redesign
    - New light, flat, compact interface with one global stylesheet.
    - Colormaps: all Matplotlib maps grouped by family (incl. berlin, managua, vanimo),
      cmcrameri / cmocean when installed, search field, gradient previews,
      reverse toggle and range slider.
    - Harmony: 33 rules in 4 families (wheel, light & shade, mood, for structures),
      draggable hue wheel, spread / variation / lightness / vibrance, perceptual
      OKLCH or classic HSV engine, 4 orderings, "Vary", presets.
    - Compact tiles with hover actions, right-click menu, keyboard control and
      a label showing which target each colour was applied to.
    - Status bar with exact commands, live contrast readout, colour-vision popup.
    - Help panel for each tab. Exports to PyMOL (.pml) and ChimeraX (.cxc) scripts.
 
                   
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
 
 * **To import palette in Adobe Illustrator**
   1. Once you export your palette as an .ase file:
   2. Open Adobe Illustrator.
   3. Open your Swatches panel (Window > Swatches).
   4. Click the Menu icon in the top-right corner of the Swatches panel.
   5. Select Open Swatch Library > Other Library...
   6. Select the .ase file you just exported from MolNympheas.
  
## Why the name?
The idea came on a way back from Paris, on the train after visiting the Orsay museum. 
It has been named in honor of Claude Monet's *Nymphéas* (Water Lilies) and his mastery of visual perception 
  
## Thanks to
* Florian Chenavier for the implementation of the colorblind (CVD) simulation matrix, and the scripts unification (one script to rule them all!!).
* Gemini, as i'm still a "tanche" in python
* Shyam Saladi, whose original pymol_viridis script (go visit his github) served as the starting inspiration for this project.

## Licence
Do whatever you want with the scripts and keep in mind that it has been code by a stupid biochemist (for that matter me).
