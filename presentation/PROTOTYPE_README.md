# RAYSENSE — how to run this on a Windows laptop

**Team Raysense · SIH26053 · DRDO · Smart India Hackathon 2026**

Written for someone who has never opened a command prompt. Follow it line by line.

---

# ⭐ IF YOU READ NOTHING ELSE

**To present tomorrow you do NOT need to install anything.**

> ### Double-click **`1_OPEN_DEMO.bat`**

The demo opens in your web browser and it is the thing you show the judges. It needs
**no Python, no internet, no setup**. It works on a laptop in aeroplane mode.

If the `.bat` file does not work, open the `DEMO` folder and **double-click `demo.html`**
instead. Same thing.

Everything below this line is optional, and is only for the moment a judge says
*"show me it actually running."*

---

# What is in this folder

| Folder | What it holds |
|---|---|
| **`1_OPEN_DEMO.bat`** | **Opens the demo. This is what you present.** |
| `2_SETUP_PYTHON.bat` | One-time install, only if you want to run the code |
| `3_RUN_TESTS.bat` | Runs the 103 automated tests |
| `4_MAKE_A_SCAN_PICTURE.bat` | Generates a fresh lidar scan image |
| `PRESENTATION\` | The PowerPoint, the speaking scripts, a backup still image |
| `DEMO\` | The demo player and all its frames |
| `code\` | The actual prototype — Python source, tests, configs |
| `results\` | Every measured number as CSV, and the figures built from them |

---

# PART 1 — Running the demo (0 minutes, no install)

### Step 1
Copy the whole `Raysense_SIH26053_Prototype` folder onto the laptop's **Desktop**.

> Do not run it from inside the ZIP. Right-click the ZIP → **Extract All** → choose
> Desktop → **Extract**. Windows will let you open files inside a ZIP without extracting,
> but the demo will not find its frames if you do.

### Step 2
Double-click **`1_OPEN_DEMO.bat`**.

Your browser opens showing two maps side by side.

### Step 3 — check it works
- Press the **play** button. The maps should animate.
- Drag the slider. The frame should change.
- **Turn off the wifi and do it again.** It still works. That is the point.

### What you are looking at

| | |
|---|---|
| **Left** | A conventional system — it reasons about heights it can see |
| **Right** | Raysense — it also reasons about gaps it *cannot* see |
| **Green** | ground the system believes is drivable |
| **Purple** | blocked |
| **Grey hatching** | **unknown — nobody looked there** |

Scrub to **frame 8**. The left panel says **"clear to drive."** The right says
**"DITCH AHEAD."** Same sensor. Same scene. Same budget. That is your moment — stop
talking and let the judges read it.

---

# PART 2 — Installing Python (about 10 minutes)

Only needed if you want to run the code live. **Do this the night before, not in the room.**

### Step 1 — download Python

1. Open your browser and go to **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python 3.x"** button
3. When it finishes downloading, click the file to run the installer

### Step 2 — THE MOST IMPORTANT CLICK

On the very first installer screen there is a small checkbox at the bottom:

> ### ☑ **Add python.exe to PATH**

**TICK IT.** It is not ticked by default.

If you miss it, every command below fails with *"python is not recognized"*, and the only
fix is to uninstall and install again. This is the single most common mistake.

Then click **Install Now** and wait. Click **Close** when it finishes.

### Step 3 — open the command prompt

1. Hold the **Windows key** and press **R**
2. Type `cmd`
3. Press **Enter**

A black window opens. That is the command prompt. You type commands and press Enter.

### Step 4 — check Python installed

Type this exactly, then press Enter:

```
python --version
```

**Good:** it prints something like `Python 3.12.4`
**Bad:** it says `'python' is not recognized...` → you missed the PATH checkbox in Step 2.
Uninstall Python and do Step 2 again.

---

# PART 3 — Setting up the prototype (about 5 minutes)

### The easy way

Double-click **`2_SETUP_PYTHON.bat`** and wait. It does everything in this part for you.
When it says *"Setup finished"*, skip to Part 4.

### The manual way, if the .bat file fails

**Step 1 — go to the code folder.** In the command prompt, type this and press Enter
(replace `YourName` with the actual Windows username):

```
cd C:\Users\YourName\Desktop\Raysense_SIH26053_Prototype\code
```

> **Shortcut if you are unsure of the path:** open the `code` folder in File Explorer,
> click once in the address bar at the top, copy the text, then type `cd ` (with a space)
> and right-click in the command prompt to paste.

Check you are in the right place — type `dir` and press Enter. You should see
`pyproject.toml`, `src`, `scripts`, `tests`.

**Step 2 — create a private Python space** (so this cannot break anything else):

```
python -m venv .venv
```

Takes about 20 seconds. Nothing is printed. That is normal.

**Step 3 — switch into it:**

```
.venv\Scripts\activate
```

Your prompt now starts with `(.venv)`. That is how you know it worked.

> Note the **backslashes** `\`. Windows uses backslashes, not forward slashes.

**Step 4 — install the prototype:**

```
pip install -e ".[dev]"
```

This downloads NumPy, matplotlib and a few others. It takes 2–5 minutes and prints a lot
of text. Wait for it to finish and return your prompt.

**Expected at the end:** `Successfully installed ...`

---

# PART 4 — Running things

**Every time you open a new command prompt**, you must first do Steps 1 and 3 again:

```
cd C:\Users\YourName\Desktop\Raysense_SIH26053_Prototype\code
.venv\Scripts\activate
```

You only need to do the install (Step 4) **once, ever**.

### A · Run the tests — 20 seconds

```
python -m pytest -q
```

**Expected:** `103 passed`

This is the strongest thing to show a judge who asks whether it really works. Two of those
tests are the safety argument in executable form: one proves an unobserved cell is never
reported as drivable, the other proves a deep ditch destroys every return.

### B · Make a lidar scan picture — 5 seconds

```
python scripts\render_scan.py --out my_scan.png
```

Then open `my_scan.png` from the `code` folder. Three panels. **The middle one is the
whole idea** — orange means *"a beam was fired and nothing came back."*

Or just double-click **`4_MAKE_A_SCAN_PICTURE.bat`**.

### C · See the map the system builds — about 40 seconds

```
python scripts\build_ground_truth.py --frames 40
```

Writes `results\m1_ground_truth.png`. The white holes inside the dashed boxes are the
trenches — **unobserved even at full budget.** That picture is the problem statement.

### D · Run the full comparison — about 90 seconds

```
python scripts\run_sweep.py --frames 40 --allocators full uniform front_roi raysense
```

Prints the comparison table and writes `results\m2_sweep.csv`.

### E · Rebuild the demo from scratch — about 3 minutes

```
python scripts\make_demo.py --fraction 0.02 --frames 40
```

Rewrites `results\demo.html`. **You do not need to do this** — the finished demo is
already in the `DEMO` folder.

---

# PART 5 — If something goes wrong

| It says | What it means | Fix |
|---|---|---|
| `'python' is not recognized` | PATH checkbox was missed | Reinstall Python, tick **Add python.exe to PATH** |
| `'pip' is not recognized` | Same cause | Same fix |
| `The system cannot find the path specified` | You are in the wrong folder | Re-do the `cd` command. Check the spelling of the username. |
| `No module named raysense` | You skipped the install, or forgot to activate | Run `.venv\Scripts\activate`, then `pip install -e ".[dev]"` |
| `No module named pytest` | Installed without `[dev]` | `pip install -e ".[dev]"` |
| Prompt has no `(.venv)` | Not activated | `.venv\Scripts\activate` |
| `.bat` file flashes and closes | It hit an error too fast to read | Open a command prompt first, then drag the `.bat` file into it and press Enter — the error stays on screen |
| Demo shows no images | You opened it from inside the ZIP | Extract the folder to the Desktop first |
| `Access is denied` | Folder is in a protected location | Move it to the Desktop |

> **PowerShell vs Command Prompt:** these instructions are for **Command Prompt** (`cmd`).
> If your window is blue and says *Windows PowerShell*, close it and open `cmd` instead
> (Windows key + R → `cmd` → Enter). PowerShell needs `.\.venv\Scripts\Activate.ps1` and
> may refuse to run scripts at all.

---

# PART 6 — The night before

- [ ] Folder extracted to the **Desktop** — not left inside the ZIP
- [ ] `1_OPEN_DEMO.bat` opens the browser and the slider works
- [ ] Tested once with **wifi turned off**
- [ ] Screen brightness at **maximum** — the grey hatching disappears on a dim projector
- [ ] `PRESENTATION\SIH2026_Raysense.pptx` opens and all 6 slides look right
- [ ] Same folder copied to a **second laptop**
- [ ] Same folder on a **USB stick**
- [ ] HDMI adapter tested
- [ ] `PRESENTATION\BACKUP_demo_still.png` open in a spare tab, in case the player fails
- [ ] Everyone has read `PRESENTATION\SPEAKING_SCRIPTS.md`

---

# The numbers, so nobody invents one

Every figure below comes from a CSV in the `results` folder. **If a number is not here,
do not say it to a judge.**

| | |
|---|---|
| Positive obstacles found, full scan | **92.9%** |
| Negative obstacles found, full scan, conventional | **11.5%** |
| Negative obstacles found by us, at a 5% budget | **91.4%** |
| Point budget reduction | **20× fewer** |
| Warning distance advantage at a 2% budget | **1.88×** — 23 m vs 12 m |
| Per-frame cost at a 5% budget | **1.5 ms** — 67× inside a 10 Hz frame |
| Precision at the chosen threshold | **73%** — not 100% |
| Maximum safe speed, 1 m ditch, stock OS1-64 | **23 km/h** |
| Automated tests | **103 passing** |
| RELLIS-3D frames processed so far | **zero — this is our honest gap** |
