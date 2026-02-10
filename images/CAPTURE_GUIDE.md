# Reference Image Capture Guide

This directory (`sikuli/images/`) is intentionally shipped empty.  You must
capture your own reference screenshots from your MacroFactor installation
because UI rendering varies by:

- Screen resolution and scaling (Retina vs. non-Retina, external monitors)
- macOS version (font rendering, window chrome)
- MacroFactor app version (layout changes with updates)
- "Designed for iPhone" window size on your specific display

This guide walks through every image you need to capture, what it should
contain, and tips for making the captures work reliably with SikuliX's
image-matching engine.

---

## Table of Contents

1. [General Capture Tips](#general-capture-tips)
2. [Capture Methods](#capture-methods)
3. [Required Images](#required-images)
4. [Optional Images](#optional-images)
5. [Verifying Your Captures](#verifying-your-captures)
6. [Re-Capturing After App Updates](#re-capturing-after-app-updates)

---

## General Capture Tips

### DO

- Capture ONLY the target element (button, label, checkbox).  Tight crops
  match more reliably than loose ones.
- Capture at the SAME screen resolution you will use when running the
  automated scripts.  If you use a Retina display, capture on Retina.
- Include enough unique visual context to avoid false positives.  A plain
  white "Export" label might match other "Export" text elsewhere in the app;
  include the button border or background color.
- Capture with the app in its normal state -- no hover effects, no pressed
  states, no tooltips covering elements.
- Save all images as PNG files.  Do not use JPEG (lossy compression causes
  matching failures).

### DO NOT

- Do not capture large regions of the screen.  The more pixels in your
  reference image, the harder it is to match and the more sensitive it
  becomes to minor rendering changes.
- Do not include dynamic content (timestamps, counters, avatars) in your
  captures.  These change between runs and will cause FindFailed errors.
- Do not include the mouse cursor in your captures.
- Do not include macOS window title bars or traffic-light buttons unless
  they are the intended target.
- Do not capture screenshots on one display resolution and then run scripts
  on a different one.

### Recommended Crop Sizes

Most reference images should be approximately:
- **Buttons and tabs:** 80-200 pixels wide, 30-60 pixels tall
- **Checkboxes/toggles:** 60-120 pixels wide, 30-50 pixels tall
- **Menu rows:** 150-300 pixels wide, 40-60 pixels tall (include the label
  text and any icon on the left)

These are rough guidelines.  The exact size depends on your display.

---

## Capture Methods

### Method A: SikuliX IDE (Recommended)

The SikuliX IDE has a built-in screenshot capture tool that saves images
in the correct format and lets you preview matching results immediately.

1. Launch the SikuliX IDE:
   ```bash
   java -jar ~/tools/sikulix/sikulixide-2.0.6.jar
   ```
2. Click the **camera icon** in the toolbar (or press Cmd+Shift+2).
3. The screen dims and a crosshair cursor appears.
4. Click and drag to select the target element.
5. The capture is stored internally.  To save it as a file:
   - Right-click the captured image in the IDE.
   - Choose "Save Image" or "Copy to File".
   - Save to `~/projects/macroclaw/sikuli/images/` with the correct
     filename from the list below.

### Method B: macOS Screenshot Tool

1. Open MacroFactor and navigate to the screen with the target element.
2. Press **Cmd+Shift+4**.
3. Drag to select ONLY the target element.
4. The PNG is saved to your Desktop (or configured screenshots location).
5. Move and rename it:
   ```bash
   mv ~/Desktop/Screenshot*.png ~/projects/macroclaw/sikuli/images/more_tab.png
   ```

### Method C: Preview.app Crop

If you have a full-screen screenshot and want to extract a region:

1. Open the screenshot in Preview.
2. Use the selection tool to draw a rectangle around the target.
3. Press **Cmd+K** to crop.
4. Save as PNG to the images directory with the correct filename.

---

## Required Images

Each entry below describes one reference image that the automation scripts
depend on.  The **Filename** must match exactly (the scripts look up images
by these names).

---

### 1. more_tab.png

**What:** The "More" tab in MacroFactor's bottom navigation bar.

**Where to find it:** Open MacroFactor.  Look at the bottom of the window.
The navigation bar has tabs for Dashboard, Nutrition, Training, and More.
"More" is typically the rightmost tab.

**What to capture:** The "More" label and its icon.  Include a small
amount of the tab's background to provide visual context, but do not
include adjacent tabs.

**Crop area:** Approximately the width of the "More" text plus icon,
and the full height of the bottom tab bar.

---

### 2. data_management.png

**What:** The "Data Management" menu item on the More screen.

**Where to find it:** Tap the More tab.  Scroll through the list of
options.  "Data Management" should appear as a row in the settings/options
list.

**What to capture:** The full row -- the "Data Management" text label and
any icon to its left.  Include the row's left edge to the right-arrow
chevron (if present).

**Crop area:** Full row width, single row height.

---

### 3. data_export.png

**What:** The "Data Export" option inside the Data Management screen.

**Where to find it:** From the More tab, tap Data Management.  Look for
"Data Export" as a menu row.

**What to capture:** The "Data Export" text label and any accompanying
icon or chevron.  Same approach as data_management.png.

---

### 4. quick_export.png

**What:** The "Quick Export" option on the Data Export screen.

**Where to find it:** From Data Management, tap Data Export.  The export
screen presents options for different export types.  "Quick Export" is
typically the first option.

**What to capture:** The "Quick Export" button, card, or row.  Include
enough of the visual treatment (background, border, icon) to distinguish
it from "Granular Export."

---

### 5. granular_export.png

**What:** The "Granular Export" option on the Data Export screen.

**Where to find it:** Same screen as Quick Export, typically the second
option.

**What to capture:** The "Granular Export" button, card, or row.  Similar
approach to quick_export.png.

---

### 6. export_button.png

**What:** The primary action button that triggers the actual export.

**Where to find it:** After configuring export options (data types and
time range), this button appears at the bottom of the export configuration
screen.  It is typically labeled "Export", "Export Data", or similar.

**What to capture:** The full button -- label text and button background.
Capture the rounded rectangle boundary of the button.  This is the most
important image since it triggers the actual file generation.

**Tip:** This button may look the same across Quick Export and Granular
Export screens.  Capture it once and reuse for both scripts.

---

### 7. confirm_export.png

**What:** A confirmation button in a dialog that may appear after tapping
the Export button.

**Where to find it:** Some MacroFactor versions show a "Are you sure?"
or "Confirm Export" dialog.  If yours does not, you can skip this image.

**What to capture:** The "Confirm" or "Yes" or "Export" button within
the modal dialog.  Include the button background.

**Note:** If your version does not show a confirmation dialog, create an
empty file (or skip it).  The scripts handle the case where this image
is not found gracefully.

---

### 8. last_7_days.png

**What:** The "Last 7 Days" time range option.

**Where to find it:** On the Quick Export configuration screen, there is
a time-range picker.  It may be a segmented control (a row of buttons
like "Today | Last 7 Days | Last 30 Days | All Time") or a dropdown.

**What to capture:** Just the "Last 7 Days" segment or option.  If it is
a segmented control, capture only the "Last 7 Days" portion -- do not
include adjacent segments.

**Tip:** Capture this in the UNSELECTED state (before tapping it), since
the script needs to find and tap it.  If the selected and unselected
states look very different, capture the unselected version.

---

### 9. all_time.png

**What:** The "All Time" time range option.

**Where to find it:** Same time-range picker as last_7_days.png, but
this time capture the "All Time" option.

**What to capture:** Just the "All Time" segment or option.

**Tip:** Same guidance as last_7_days.png -- capture in the unselected
state.

---

### 10. nutrition_checkbox.png

**What:** The Nutrition data-type checkbox or toggle.

**Where to find it:** On the export configuration screen (both Quick
Export and Granular Export), there is a list of data types to include.
"Nutrition" is one of them.

**What to capture:** The checkbox/toggle AND the "Nutrition" label next
to it.  Including the label helps avoid confusion with other checkboxes
that look identical.

**Crop area:** From the left edge of the checkbox/toggle through the end
of the "Nutrition" text.  Single row height.

**Important:** If checkboxes have distinct checked vs. unchecked
appearances, capture the UNCHECKED state for the default scripts.  If you
need both states, also create `nutrition_checked.png` and update the
scripts accordingly (see the TEMPLATE NOTES in the script files).

---

### 11. workouts_checkbox.png

**What:** The Workouts data-type checkbox or toggle.

**Where to find it:** Same data-type list as Nutrition.

**What to capture:** Same approach as nutrition_checkbox.png but for
"Workouts."

---

### 12. exercises_checkbox.png

**What:** The Exercises data-type checkbox or toggle.

**Where to find it:** Same data-type list.  This may only appear on the
Granular Export screen (not Quick Export).

**What to capture:** Same approach -- checkbox/toggle plus "Exercises"
label.

---

### 13. weight_checkbox.png

**What:** The Weight (or "Body Weight") data-type checkbox or toggle.

**Where to find it:** Same data-type list.  This may only appear on the
Granular Export screen.

**What to capture:** Same approach -- checkbox/toggle plus "Weight" label.

---

## Optional Images

These images are not required for the core export flow but help with
error recovery and navigation robustness.

---

### 14. macrofactor_icon.png

**What:** The MacroFactor app icon, either in the Dock or in the window
title area.

**Use:** Visual verification that the app is in the foreground.

**What to capture:** The app icon, approximately 48x48 to 64x64 pixels.

---

### 15. back_button.png

**What:** The back-navigation button (typically a left-arrow or chevron
at the top of the screen).

**Use:** If the script gets lost, it can tap Back repeatedly to return to
a known screen and retry navigation.

**What to capture:** The back arrow/chevron.  Include just enough to avoid
matching other left-arrows in the UI.

---

### 16. close_button.png

**What:** A close button or "X" for dismissing modals or dialogs.

**Use:** Error recovery -- dismiss unexpected dialogs that block
navigation.

**What to capture:** The close icon (X or circle-X).

---

## Verifying Your Captures

After capturing all required images, verify each one works before running
the full automation:

### Using the SikuliX IDE Console

```python
from sikuli import *

# Point SikuliX to your images directory
addImagePath("/Users/you/projects/macroclaw/sikuli/images")

# Open MacroFactor and navigate to the relevant screen, then:
result = exists(Pattern("more_tab.png").similar(0.80), 5)
if result:
    print("PASS: more_tab.png found with similarity 0.80")
    result.highlight(2)  # Highlight the match for 2 seconds
else:
    print("FAIL: more_tab.png not found")
```

Repeat for each image.  The `highlight()` call draws a red rectangle
around the matched region so you can visually confirm it found the
correct element.

### Adjusting Similarity

If an image is not found at 0.80 similarity:
- Try 0.70, then 0.65.
- If even 0.60 fails, the image probably needs to be re-captured.
- If 0.60 matches but matches the WRONG element, the crop is too generic.
  Re-capture with more unique context.

If an image matches at 0.80 but matches the wrong element:
- Raise similarity to 0.85 or 0.90.
- Re-capture with a more specific crop.

---

## Re-Capturing After App Updates

When MacroFactor updates, buttons and layouts may change.  If scripts
start failing:

1. Open MacroFactor and navigate through the export flow manually.
2. Compare each screen to your existing reference images.
3. Re-capture any images where the UI has changed.
4. Test with the SikuliX IDE console (see above) before running full
   automation.

Keep old images in a backup directory for reference:

```bash
mkdir -p ~/projects/macroclaw/sikuli/images/archive/$(date +%Y%m%d)
cp ~/projects/macroclaw/sikuli/images/*.png \
   ~/projects/macroclaw/sikuli/images/archive/$(date +%Y%m%d)/
```

Then capture fresh images into the main `images/` directory.
