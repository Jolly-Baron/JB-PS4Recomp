# JB PS4Recomp

Jolly Baron (JB) static PS4 recompilation launcher + runtime.
Copyright (c) 2026 Jolly Baron.

## Run
Double-click JB-PS4Recomp.bat. Uses the bundled python\ folder; nothing to install.
Developer mode: python launcher.py

## Add a game
Press Add, enter a name and the extracted dump folder (the one with sce_sys/).
A profile JSON is created automatically under profiles\.

## Layout
launcher.py / theme.py / runtime.py  - launcher UI
assets\                              - logo and window icon (CC BY 4.0)
profiles\                            - per-game JSON, created by Add
backend\                             - run.py, scripts\, patches\, bin\ (runtime)
python\                              - bundled interpreter (PSF license)
logs\                                - per-run logs

## Rebuild (developer)
MSYS2 CLANG64: bash build.sh
Then sync-backend.cmd to refresh backend\bin.

## Supported titles
Exist Archive (CUSA04726) - ported.
Gravity Rush Remastered (CUSA01113 / CUSA01130) - profile present.

## Controls limits
Button remap only (GOW3_PAD_MAP / GOW3_KEY_MAP). Sticks, triggers and overlay
shortcuts are fixed. Changes apply on game restart.

## Licenses
Code: GPL-2.0-or-later (LICENSE).
Art: CC BY 4.0 (LICENSE-ART).
Bundled Python: PSF (LICENSE-PYTHON).

## Install a .pkg
In the launcher press Install pkg, pick the .pkg and an output folder, Extract.
CLI: python extract_pkg.py game.pkg out_dir
Then add the output folder in the launcher (Add game).

Bundled cryptography (Apache-2.0 / BSD) lives in python\Lib\site-packages;
its licenses are in licenses\cryptography\. Required by the PKG extractor.

## Source code (GPL-2.0)

The runtime binary is derived from GPL-2.0 code (shadPS4 video core + port runtime).
The complete corresponding source lives in the `source` branch of this repository:

    https://github.com/Jolly-Baron/JB-PS4Recomp/tree/source

This product repository stays lean (clone and play); the source repository carries
the full fork history and upstream credits. Build instructions are there.
