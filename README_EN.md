---
🌍 **Languages / Idiomas:** [English] | [Castellano](README.md)
---

# 🎭 Match Impro Director - Ultimate Edition

![Acción Impro](https://img.shields.io/badge/Developed%20by-Acción%20Impro-blue)
![License](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey)
![Version](https://img.shields.io/badge/Version-2.1.0--stable-green)
![Tests](https://img.shields.io/badge/Tests-169%20automated-brightgreen)

Professional technical suite designed for **Improvisational Match** shows, theater competitions, and live performing arts events. Developed in Medellín, Colombia, by **Corporación Acción Impro**.

## 📸 Preview

| Audience Scoreboard | Control Panel |
| :---: | :---: |
| ![Scoreboard](boardliveview.png) | ![Panel](controlpanelboard.png) |

## ✨ Key Features

- **Dual Screen (Multimonitor):** Control everything from your laptop while the audience only sees the professional board on the projector.
- **Smart Fullscreen:** Native fullscreen (F11 or double-click) on whichever monitor holds the board. Works on Windows, Linux and macOS.
- **Flexible Design:** Supports various background ratios (16:9, 4:3, 1:1), customizable logos, and precise manual adjustment for every element.
- **Live Preview:** A thumbnail in the panel shows exactly what the audience sees, so you never turn around to check the projector.
- **Live Control:** Edit names, update scores, and manage fouls (up to 3 with "traffic light" style) without pausing the show. Up to **6 teams**, each with its own color.
- **Undo and Redo:** A point given to the wrong team is fixed with `Ctrl+Z`, not by recalculating by hand.
- **Integrated Soundbar:** 6-slot sound effect launcher (MP3/WAV/OGG) with customizable names, volume control and a mute button.
- **Accurate Timer:** Drift-free countdown, placeable at the top or bottom, with quick adjustments (±10 s, ±30 s) and a color alert in the final seconds.
- **WiFi Remote Control:** Run everything from a phone or tablet instead of staying glued to the computer.
- **Everything Is Saved:** Design, teams, colors and effects come back when you reopen the program. You can also export one preset per show.

## 🚀 Installation and Usage

### For Users (Executable)
1. Download the `MatchDirector_ByAccionImpro.zip` file from the **Releases** section.
2. Connect your projector or second screen in "Extend" mode.
3. Launch the app and drag the "Audience Scoreboard" window to the public screen.
4. **Double-click** on the board or press **F11** to enter fullscreen mode.

### For Developers (Source Code)
The code is written in **Python 3.10 or newer** (tested on 3.11 and 3.12).

```bash
git clone https://github.com/carlosestebanor/Match-Impro-Director.git
cd Match-Impro-Director
pip install -r requirements.txt
python match_director_source.py
```

## ⌨️ Keyboard Shortcuts

Designed so you can operate one-handed while the other hand runs sound. They are ignored while you type in a text box.

| Key | Action |
| :--- | :--- |
| `Space` | Start or pause the timer |
| `1` … `6` | Add a point to team N |
| `Shift` + `1` … `6` | Remove a point from team N |
| `F1` … `F6` | Flag a foul on team N |
| `Ctrl` + `Z` / `Ctrl` + `Y` | Undo / redo a play |
| `Ctrl` + `S` | Save preferences now |
| `Ctrl` + `R` | Reset the scoreboard |
| `F11` or double-click | Fullscreen board |
| `Esc` | Exit fullscreen |

## 📡 Remote Control (WiFi Handheld)

Lets an assistant (or you, from the audience floor) run the scoreboard straight from a phone browser. Nothing to install on the phone and no internet required: everything stays inside your local network.

1. Connect the computer and the phone to the **same WiFi network**.
2. In the control panel open the **📡 REMOTO** tab and press **ENCENDER** (turn on).
3. Type the displayed address into the phone's browser (e.g. `http://192.168.1.20:8770`).
4. Enter the 6-digit **PIN** shown in the panel. The phone remembers it for next time.

The handheld can add and remove points, add and clear fouls, set and nudge the timer, undo the last play, fire the 6 sound effects and mute them. The projector board updates instantly.

**Security notes**
- Anyone on that network can reach the handheld page, which is why it is PIN protected.
- On public or shared networks, generate a **new PIN** before the show with the 🔄 button.
- Turn the server off when the show ends.
- If Windows asks about the Firewall the first time, allow access on **private networks**.
- If port 8770 is taken, change it in the same tab (e.g. 8771).

## 💾 Preferences and Presets

The program saves your setup (design, teams, colors, volume and effect paths) on its own and restores it on the next launch. The exact file path is shown in the **❔ AYUDA** tab:

- Next to the program, when that folder is writable — so your presets travel with you on a USB stick.
- Otherwise, in your home folder (`~/.match_impro_director/`).

Use **💾 Guardar** and **📂 Cargar** to export a different preset per show or per company.

## 🎨 Customization
In the **DESIGN** tab you can:
- Change colors for names, scores, fouls, boxes, clock and alert.
- Select system fonts.
- Adjust padding, corner radius and positions of the containers.
- Toggle visibility of elements for "Friendly Matches" (No fouls/No timer).

## 🧱 Project Layout

| File | Contents |
| :--- | :--- |
| `match_director_source.py` | Operator panel (UI) |
| `match_state.py` | Match data, timer and persistence |
| `tablero.py` | Projection rendering engine |
| `remote_control.py` | WiFi remote control |
| `pruebas/` | Automated tests |

The last three modules must ship alongside the main one. If `remote_control.py` is missing the program still starts and only the 📡 REMOTO tab is disabled.

## 🧪 Tests

```bash
python pruebas/ejecutar.py            # everything
python pruebas/ejecutar.py --sin-gui  # only what needs no display
```

On headless Linux: `xvfb-run -a python pruebas/ejecutar.py`.

## ⚡ Performance

Version 2.0 rewrote the rendering engine. Measured with a Full HD background plus logo on the same machine:

| Operation | v1.0 | v2.0 |
| :--- | ---: | ---: |
| Full redraw (median) | 63.9 ms | 3.9 ms |
| One timer second | 63.9 ms | 0.10 ms |

See the [changelog](CHANGELOG.md) for the full detail.

## 📜 License and Credits

This software is distributed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license. See [LICENSE](LICENSE).

**Attribution:**
Developed by **Corporación Acción Impro**, Medellín, Colombia, 2026.
[https://accionimpro.com.co/](https://accionimpro.com.co/)

---

*Made by and for improvisers.* 🎭
