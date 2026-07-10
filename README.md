# CNDS Data Validation App

This repository contains the initial Windows-focused GUI application for validating CNDS fixed-width CNDS input files.

## Quick start

You can launch the app in either of these simple ways:

- double-click `run_app.bat`
- run this PowerShell command from the project folder:

```powershell
.\run_app.ps1
```

## Build a Windows executable

The validator can be packaged as a Windows executable without changing the app code.

Build prerequisites:

- Python 3.11 or newer installed on the build machine
- internet access once to install the build dependency `PyInstaller`

Build the app into a fresh timestamped output folder:

```powershell
.\build_exe.ps1
```

Create a packaged release zip as well:

```powershell
.\build_exe.ps1 -Package
```

Clean build caches before building:

```powershell
.\build_exe.ps1 -Clean
```

Override the release version label if needed:

```powershell
.\build_exe.ps1 -Package -ReleaseVersion 0.1.1
```

Output behavior:

- application builds go to `.build\dist-<timestamp>\CNDS Data Validation`
- temporary PyInstaller work files go to `.build\work-<timestamp>`
- packaged releases go to `releases\`
- the most recent app folder is also written to `dist_latest.txt`

Notes:

- The generated executable is intended for Windows users who should not need Python installed.
- The build uses the project version from `pyproject.toml` by default and writes matching Windows EXE metadata before packaging.
- The build uses fresh timestamped folders to avoid rebuild failures from OneDrive or Explorer file locks.
- The packaged release zip includes a small `README.txt` for end users.
- If you add an icon at `assets\app.ico`, the executable will automatically use it.
- Windows version metadata is generated into `windows_version_info.txt` during the build.

## Current scope

Version 1 / early Phase 2 supports:

- selecting one or more fixed-width input files from a GUI
- validating all selected files together in one review session
- choosing the duplicate comparison rule before validation
- optionally ignoring validation for selected fields before validation
- separating valid, invalid, duplicate, and duplicate-plus-invalid outputs into dedicated export files
- sorting the display and exported files by the selected duplicate rule so duplicate groups stay together, even across files
- exporting valid CNDS records into `CCIPR60I` Person Create format
- writing `CCIPR60I` output as either UTF-8 text preview, EBCDIC CP037 binary upload, or both
- building `CCIPR60I` binary output with absolute-position metadata, raw-byte writing, and strict 1000-byte validation

## Interface behavior

The interface now includes:

- multi-file selection with duplicate comparison across all selected files
- source-file visibility in Record Status and Defects
- a duplicate-rule selector for `Last + First + DOB` or `Last + First + DOB + Sex`
- checkboxes to ignore validation for selected fields before clicking `Validate`
- a darker gray application theme for readability
- a scrollable field-by-field preview panel for the selected record
- a defects pane that shows only the selected record's defects
- a Record Status filter for `All Records`, `Valid Records`, `Invalid Records`, and `Duplicate Records`
- record labels that distinguish `Duplicate + Invalid` from duplicate-only rows
- summary statistics for total files, total records, duplicate count, and duplicate percentage
- a `CCIPR60I...` conversion dialog with file-level constants for:
  - Accounting Info
  - Testing Comment
  - Last Changed Program ID
  - Last Changed User ID
