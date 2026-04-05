Results for agent_23_material.txt checks
Generated: 2026-04-05T09:15:30Z

Summary: Checked each entry listed in .ai/agents/ovc/prompts/agent_23/agent_23_material.txt against official repos/releases and winget/homebrew manifests where applicable. Notes below.

1) miktex
- Repo: https://github.com/MiKTeX/miktex (official)
- License: "Various free software licenses; no single project-wide license" — VERIFIED. (MiKTeX/COPYING.md explains mixed-license distribution)
- fileNamePattern: material uses winget Id MiKTeX.MiKTeX — VERIFIED (winget manifest present). Status: OK.

2) texlive
- Repo: mirror https://github.com/TeX-Live/texlive-source (official distribution via TUG)
- License: "Various free software licenses" — VERIFIED (TUG/TeX Live copying page).
- fileNamePattern: material uses `sudo nala install texlive -y` (Linux OK for Debian-based), Windows: "texlive.ps1" (NOT MATCH; official Windows installer is install-tl-windows.exe / TUG net installer), macOS: "brew install texlive" (NOT RECOMMENDED — Mac users should use MacTeX or MacTeX cask). Status: Needs update. Recommendation: for Windows use TUG installer (install-tl-windows.exe) or official instructions; for macOS prefer MacTeX (`brew install --cask mactex`) or link to TUG MacTeX.

3) texmaker
- Repo: primary site https://www.xm1math.net/texmaker (official); GitHub forks exist but not the canonical repo.
- License: GPL (GPL-2.0-or-later) — VERIFIED.
- fileNamePattern: material uses winget Id Texmaker.Texmaker — VERIFIED (winget manifest exists). If you prefer release asset names, official downloads include "texmaker-<version>.tar.bz2". Status: OK.

4) lapce
- Repo: https://github.com/lapce/lapce — VERIFIED
- License: Apache-2.0 — VERIFIED (LICENSE file).
- fileNamePattern: material uses winget Id Lapce.Lapce — VERIFIED (winget manifest present). Status: OK.

5) tesseract
- Repo: https://github.com/tesseract-ocr/tesseract — VERIFIED
- License: Apache-2.0 — VERIFIED (LICENSE).
- fileNamePattern: material uses winget Id UB-Mannheim.TesseractOCR (UB Mannheim builds) — VERIFIED (winget manifest exists). Note: official source repo provides source releases; Windows binary builds are provided by external maintainers (UB Mannheim). Status: OK (but note distinction source vs third-party binaries).

6) perl (Strawberry Perl)
- Repo/site: https://strawberryperl.com/ (official) and packaging at https://github.com/StrawberryPerl/Perl-Dist-Strawberry
- License: "Artistic License OR GPL-1.0-or-later" — VERIFIED (matches Perl licensing used by Strawberry Perl).
- fileNamePattern: material uses winget Id StrawberryPerl.StrawberryPerl — VERIFIED (winget manifest present). Status: OK.

7) db-browser-sqlite
- Repo: https://github.com/sqlitebrowser/sqlitebrowser — VERIFIED
- License: "MPL-2.0 OR GPL-3.0-or-later" — VERIFIED (LICENSE notes bi-license MPL-2.0 / GPL-3.0+).
- fileNamePattern: material uses winget Id DBBrowserForSQLite.DBBrowserForSQLite — VERIFIED (winget manifest present). Status: OK.

8) ssms (SQL Server Management Studio)
- Repo: Not on GitHub (proprietary). Official download & release notes: Microsoft Learn (SSMS install & release history).
- License: Microsoft SQL Server Management Studio License Terms — VERIFIED (proprietary).
- fileNamePattern: material uses winget Id Microsoft.SQLServerManagementStudio — VERIFIED (winget manifest exists). Note: installer is a bootstrapper (vs_SSMS.exe). Status: OK.

9) adobe-reader
- Repo: Not on GitHub (proprietary). Official download: https://get.adobe.com/reader/
- License: Adobe Acrobat Reader Software License Agreement — VERIFIED.
- fileNamePattern: material uses winget Id Adobe.Acrobat.Reader.64-bit — VERIFIED (winget manifest exists). Status: OK.

10) julia
- Repo: https://github.com/JuliaLang/julia — VERIFIED
- License: MIT — VERIFIED (project is MIT-licensed).
- fileNamePattern: material uses winget Id Julialang.Julia — VERIFIED (winget manifest exists). Note: Julia recommends juliaup for installs; winget is acceptable. Status: OK.

Conclusions & actions:
- All listed projects are either GitHub-hosted or have official release/download pages.
- For most entries the material uses winget/brew commands; these winget IDs and manifests were found and match the material except where noted.
- Items needing update: texlive fileNamePattern for Windows/macOS: recommend switching to official TUG installers (install-tl-windows.exe / MacTeX for macOS or `brew install --cask mactex`) or explicitly reference the TUG release asset names.

If you want, I can: (a) update the material file to fix texlive entries; (b) replace winget commands with canonical release asset filename patterns for GitHub-hosted projects. Let me know which preference.
