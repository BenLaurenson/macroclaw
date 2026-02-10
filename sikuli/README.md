# MacroClaw SikuliX Automation

SikuliX scripts that automate data export from the MacroFactor iOS app running
as "Designed for iPhone" on Apple Silicon Macs.  These scripts use image-based
UI recognition to navigate the app and trigger exports without manual
interaction.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Install Java 17](#install-java-17)
3. [Install SikuliX 2.0.6](#install-sikulix-206)
4. [macOS Permissions](#macos-permissions)
5. [Capture Reference Screenshots](#capture-reference-screenshots)
6. [Configuration](#configuration)
7. [Running the Scripts](#running-the-scripts)
8. [Testing Manually](#testing-manually)
9. [Scheduling with launchd](#scheduling-with-launchd)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13 Ventura or later
- MacroFactor app installed from the App Store ("Designed for iPhone")
- Homebrew (for Java installation)
- An active MacroFactor account with data to export

---

## Install Java 17

SikuliX 2.0.x requires Java 11 or later.  Java 17 (LTS) is recommended.

```bash
# Install OpenJDK 17 via Homebrew
brew install openjdk@17

# Symlink so macOS can find it
sudo ln -sfn "$(brew --prefix openjdk@17)/libexec/openjdk.jdk" \
  /Library/Java/JavaVirtualMachines/openjdk-17.jdk

# Verify
java -version
# Expected: openjdk version "17.x.x"
```

If you already have a different Java version installed, you can use
`/usr/libexec/java_home -V` to list all installed JVMs and set
`JAVA_HOME` explicitly:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

---

## Install SikuliX 2.0.6

Download the SikuliX IDE jar from the official site:

```bash
# Create a directory for SikuliX
mkdir -p ~/tools/sikulix
cd ~/tools/sikulix

# Download SikuliX 2.0.6 IDE (includes Jython)
curl -L -o sikulixide-2.0.6.jar \
  "https://launchpad.net/sikuli/sikulix/2.0.6/+download/sikulixide-2.0.6.jar"
```

Verify the jar runs:

```bash
java -jar ~/tools/sikulix/sikulixide-2.0.6.jar -h
```

You should see SikuliX help output.  If you get an error about
`libtesseract` or OpenCV, install the native dependencies:

```bash
brew install tesseract opencv
```

### Apple Silicon Notes

SikuliX 2.0.6 includes native libraries for arm64 macOS.  If you
encounter `UnsatisfiedLinkError` messages, ensure you are using an
arm64-native Java, not an x86_64 version running under Rosetta:

```bash
file $(which java)
# Should show: Mach-O 64-bit executable arm64
```

---

## macOS Permissions

SikuliX needs two specific privacy permissions to interact with the screen:

### Accessibility

Required for SikuliX to send clicks and keystrokes to other apps.

1. Open **System Settings** (or System Preferences on older macOS).
2. Go to **Privacy & Security** -> **Accessibility**.
3. Click the lock icon and authenticate.
4. Add `java` (or `Terminal.app` if running from the terminal).

### Screen Recording

Required for SikuliX to capture screenshots and find UI elements.

1. Go to **Privacy & Security** -> **Screen Recording**.
2. Add `java` (or `Terminal.app`).
3. Restart your terminal/Java process after granting this permission.

If you skip these steps, SikuliX will either fail to find any images
(because screenshots are blank) or fail to click anything.

---

## Capture Reference Screenshots

**This is the most critical setup step.**

The `sikuli/images/` directory ships empty.  You MUST capture your own
reference screenshots because:

- MacroFactor renders differently depending on screen resolution, macOS
  version, and display scaling.
- "Designed for iPhone" apps have a fixed window size, but the exact
  pixel rendering varies by display.
- iOS app updates may change button labels, colors, or layout.

See **`sikuli/images/CAPTURE_GUIDE.md`** for a detailed, image-by-image
guide.  The required screenshots are:

| Filename                  | What to Capture                                      |
|---------------------------|------------------------------------------------------|
| `more_tab.png`            | "More" tab in the bottom navigation bar              |
| `data_management.png`     | "Data Management" row in the More menu               |
| `data_export.png`         | "Data Export" row in Data Management                  |
| `quick_export.png`        | "Quick Export" option on the export screen            |
| `granular_export.png`     | "Granular Export" option on the export screen         |
| `export_button.png`       | The primary "Export" action button                    |
| `confirm_export.png`      | Confirmation button (if the app shows one)            |
| `last_7_days.png`         | "Last 7 Days" time range option                      |
| `all_time.png`            | "All Time" time range option                         |
| `nutrition_checkbox.png`  | Nutrition data-type checkbox or toggle                |
| `workouts_checkbox.png`   | Workouts data-type checkbox or toggle                 |
| `exercises_checkbox.png`  | Exercises data-type checkbox or toggle                |
| `weight_checkbox.png`     | Weight data-type checkbox or toggle                   |
| `macrofactor_icon.png`    | (Optional) App icon for visual verification          |
| `back_button.png`         | (Optional) Back/navigation button for recovery       |
| `close_button.png`        | (Optional) Close button for recovery                 |

### Quick Capture Method (SikuliX IDE)

1. Launch SikuliX IDE:
   ```bash
   java -jar ~/tools/sikulix/sikulixide-2.0.6.jar
   ```
2. Open MacroFactor and navigate to the screen containing the element.
3. In the SikuliX IDE, press the camera icon or use **Cmd+Shift+2**.
4. Drag a rectangle around the target element.
5. Save the captured image to `sikuli/images/` with the correct filename.

### Quick Capture Method (macOS Screenshot)

Alternatively, use the macOS built-in screenshot tool:

1. Open MacroFactor and navigate to the target screen.
2. Press **Cmd+Shift+4** to enter selection mode.
3. Drag to select ONLY the target element (button, label, checkbox).
4. The screenshot saves to your Desktop by default.
5. Move and rename it to `sikuli/images/<filename>.png`.

---

## Configuration

Create (or edit) `config/sikuli_config.yaml`:

```yaml
# Similarity threshold for image matching (0.0 to 1.0).
# Lower = more forgiving, higher = stricter.
# Start at 0.80 and tune from there.
similarity: 0.80

# Timing configuration (all values in seconds).
wait_times:
  app_launch: 8          # Wait for MacroFactor to launch
  between_actions: 1.5   # Pause between UI interactions
  element_timeout: 10    # Max wait for a UI element to appear
  download_timeout: 30   # Max wait for .xlsx to appear in Downloads
  post_click: 1.0        # Brief pause after each click

# Directory where exported .xlsx files are deposited.
imports_dir: ~/projects/macroclaw/data/imports

# macOS Downloads folder (where MacroFactor drops the export).
downloads_dir: ~/Downloads

# App name as it appears to macOS.
app_name: MacroFactor

# Log file location.
log_file: ~/projects/macroclaw/logs/sikuli_export.log

# Reference images directory (usually auto-detected).
# image_dir: ~/projects/macroclaw/sikuli/images
```

---

## Running the Scripts

### Daily Export (Quick Export, Last 7 Days)

```bash
java -jar ~/tools/sikulix/sikulixide-2.0.6.jar \
  -r ~/projects/macroclaw/sikuli/scripts/daily_export.py
```

### Bulk Export (Granular Export, All Time)

```bash
java -jar ~/tools/sikulix/sikulixide-2.0.6.jar \
  -r ~/projects/macroclaw/sikuli/scripts/bulk_export.py
```

### With a Custom Config File

```bash
java -jar ~/tools/sikulix/sikulixide-2.0.6.jar \
  -r ~/projects/macroclaw/sikuli/scripts/daily_export.py \
  -- ~/projects/macroclaw/config/sikuli_config.yaml
```

---

## Testing Manually

Before scheduling the scripts, run through each step manually to verify
your reference screenshots work:

### Step 1: Open SikuliX IDE

```bash
java -jar ~/tools/sikulix/sikulixide-2.0.6.jar
```

### Step 2: Test Individual Actions

In the SikuliX IDE's interactive console, test each image match:

```python
# Add your images directory to the image path
import sys
sys.path.insert(0, "/Users/you/projects/macroclaw/sikuli/scripts")
from common import *

config = load_config()
logger = setup_logging()

# Test: can SikuliX find the "More" tab?
pattern = make_pattern("more_tab", config)
result = exists(pattern, 5)
print("Found more_tab:", result is not None)
```

### Step 3: Tune Similarity

If images are not found:
- Try lowering similarity to 0.70 or 0.65.
- Re-capture screenshots if the app was updated.

If false positives occur (wrong element clicked):
- Raise similarity to 0.85 or 0.90.
- Capture a more specific crop of the target element.

### Step 4: Run the Full Script

Once individual actions work, run the full daily_export.py and watch.
Keep your hands off the mouse and keyboard while SikuliX is running.

---

## Scheduling with launchd

Once scripts work reliably, schedule them with macOS launchd.  A sample
plist is provided in `config/launchd/`.

Key considerations:

- The Mac must be unlocked with the screen awake for SikuliX to work.
  Use `caffeinate` to prevent sleep during the export window.
- Schedule at a time when you will not be actively using the computer,
  as SikuliX takes control of the mouse.
- Set a narrow execution window (e.g. 5:00 AM) when the machine is
  typically idle.

---

## Troubleshooting

### "FindFailed" -- SikuliX cannot locate a UI element

**Most common causes:**

1. **Missing or stale reference screenshots.**  Re-capture the image from
   the current version of the app at your current screen resolution.

2. **Similarity threshold too high.**  Lower `similarity` in your config
   from 0.80 to 0.70 or 0.65.

3. **Screen resolution changed.**  If you captured screenshots on a Retina
   display and then run on an external monitor (or vice versa), the images
   will not match.  Re-capture at the resolution you intend to run at.

4. **App window is obscured.**  Ensure no other windows cover MacroFactor
   and that no macOS notifications are overlaying the target element.

5. **macOS Screen Recording permission not granted.**  SikuliX captures a
   blank screen without this permission.  Check System Settings.

### Download timeout -- .xlsx never appears

- MacroFactor may need network access to generate the export.  Check your
  internet connection.
- For bulk exports with years of data, increase `download_timeout` to
  120-300 seconds.
- Check ~/Downloads manually to see if the file appeared with an
  unexpected name.

### App does not launch or focus

- Verify the app name matches exactly: run `osascript -e 'tell app "System Events" to get name of every process'` to see running process names.
- Update `app_name` in your config to match the exact process name.

### SikuliX crashes with UnsatisfiedLinkError

- Ensure you are running arm64-native Java, not Rosetta x86_64.
- Reinstall Java 17 via Homebrew.
- Verify with: `file $(which java)` -- should show `arm64`.

### Scripts work in IDE but not from command line

- Ensure `JAVA_HOME` is set in your shell profile.
- Ensure the `-r` flag path is absolute, not relative.
- Check that the SikuliX jar version matches what you tested with.

### Debug screenshots

When a script fails, it automatically saves a screenshot to
`logs/screenshots/`.  Check these to see what the screen looked like
at the moment of failure.

### Log files

All actions are logged to the file specified in your config (default:
`logs/sikuli_export.log`).  Review this for detailed step-by-step
information about what happened during a run.
