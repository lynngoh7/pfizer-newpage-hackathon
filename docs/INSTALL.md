# Install the app

There are two ways to get the app:

- **A. Use a ready-made installer** (easiest). Get it from GitHub: **Actions** tab → **Build app** → open the latest green run → **Artifacts** at the bottom.
- **B. Build it yourself** from the code. You can only build for the computer you're on: build the Mac app on a Mac, the Windows app on Windows, and the Linux app on Linux.

Whichever way you choose, install **Ollama** first and download the models (see the [README](../README.md), step 1.4). The app needs Ollama running.

---

## Mac

**A. From an installer**
1. Download the artifact for your Mac:
   - Apple Silicon (M1–M4): `app-macos-14`
   - Intel: `app-macos-13`

   Not sure which you have? Apple menu → About This Mac → Chip/Processor.
2. Open the `.dmg` and drag **Haystack** into **Applications**.
3. The first time, right-click the app → **Open** → **Open**. The app isn't signed, so a double-click is blocked the first time.

**B. Build it yourself**
1. Install the tools in [README](../README.md) step 1.
2. In Terminal, from the project folder:
   ```sh
   npm install
   sh scripts/build-app.sh
   ```
3. The app is now in **Applications** (and in Launchpad and Spotlight).

---

## Windows

**A. From an installer**
1. Download the artifact `app-windows-latest`, unzip it, and run `…-setup.exe`.
2. If Windows shows **"Windows protected your PC"**: click **More info** → **Run anyway**. The app isn't signed.
3. Open **Haystack** from the Start menu.

**B. Build it yourself**
1. Install:
   - **Git for Windows** (includes Git Bash): https://git-scm.com/download/win
   - **Node.js 20+** and **Python 3.10+**: when installing Python, tick **"Add python.exe to PATH"**
   - **Rust**: download and run `rustup-init.exe` from https://rustup.rs. If it asks, let it install the Visual Studio C++ build tools.
2. Open **Git Bash** in the project folder and run:
   ```sh
   npm install
   sh scripts/build-app.sh
   ```
3. Open **Haystack** from the Start menu.

---

## Linux (Ubuntu / Debian / Fedora)

**A. From an installer**
1. Download the artifact `app-ubuntu-22.04` and unzip it.
2. Install the file for your system:
   - Ubuntu / Debian: `sudo apt install ./Local*.deb`
   - Fedora: `sudo dnf install ./Local*.rpm`
   - Anything else: `chmod +x Local*.AppImage` then run it. An AppImage doesn't appear in the app menu.
3. Open **Haystack** from the app menu.

**B. Build it yourself**
1. Install the tools in [README](../README.md) step 1, plus the system packages:
   ```sh
   # Ubuntu / Debian
   sudo apt install libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
   ```
2. From the project folder:
   ```sh
   npm install
   sh scripts/build-app.sh
   ```
   It asks for your password to install the app.
3. Open **Haystack** from the app menu.

---

## Good to know

- **Already built?** `sh scripts/build-app.sh --install` installs the last build without rebuilding.
- **First launch is slow** (about 15 s) before the engine dot turns green. Later launches are faster.
- **Engine dot stays grey?** Check that Ollama is running.
