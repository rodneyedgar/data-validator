from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .ccipr60i import (
    CCIPR60I_BINARY_FILE_NAME,
    CCIPR60I_TEXT_FILE_NAME,
    BinaryValidationSummary,
    CONVERSION_FORMAT_BINARY,
    CONVERSION_FORMAT_BOTH,
    CONVERSION_FORMAT_LABELS,
    CONVERSION_FORMAT_REVERSE,
    CONVERSION_FORMAT_TEXT,
    CONVERSION_SCOPE_LABELS,
    CONVERSION_SCOPE_REVERSE,
    CONVERSION_SCOPE_VALID_AND_CORRECTED,
    ConversionConfig,
    build_ccipr60i_record,
    validate_binary_file,
    write_ccipr60i_binary,
    write_ccipr60i_text,
)
from .exporters import export_defects_csv_records, export_records
from .overrides import (
    OVERRIDE_EXPORT_FULL_AND_SPLIT,
    OVERRIDE_EXPORT_FULL_ONLY,
    OVERRIDE_EXPORT_MODE_LABELS,
    OVERRIDE_EXPORT_MODE_REVERSE,
    OVERRIDE_EXPORT_SPLIT_ONLY,
    OVERRIDE_FIELD_NAMES,
    OVERRIDE_SCOPE_BOTH,
    OVERRIDE_SCOPE_LABELS,
    OVERRIDE_SCOPE_REVERSE,
    OverrideConfig,
    apply_overrides_to_fields,
    serialize_fields,
    should_apply_overrides,
)
from .profiles import DEFAULT_PROFILE
from .validator import (
    DUPLICATE_NAME_DOB,
    DUPLICATE_NAME_DOB_SEX,
    FileValidationResult,
    RecordResult,
    ValidationIssue,
    build_duplicate_key,
    duplicate_mode_label,
    validate_record,
    validate_files,
)

FILTER_ALL = "All Records"
FILTER_VALID = "Valid Records"
FILTER_INVALID = "Invalid Records"
FILTER_DUPLICATE = "Duplicate Records"
DUPLICATE_HIGHLIGHT_FIELDS = {"last_name", "first_name", "date_of_birth", "sex"}
DUPLICATE_MODE_LABELS = {
    "Last + First + DOB": DUPLICATE_NAME_DOB,
    "Last + First + DOB + Sex": DUPLICATE_NAME_DOB_SEX,
}
DUPLICATE_MODE_REVERSE = {value: key for key, value in DUPLICATE_MODE_LABELS.items()}
COMMON_OPTIONAL_FIELDS = {"medicaid_id", "sis_number", "application_person_id"}
OVERRIDE_FIELD_LABELS = {
    "ssn": "SSN",
    "ethnicity": "Ethnicity",
    "language": "Language",
    "race_1": "Race 1",
    "race_2": "Race 2",
    "race_3": "Race 3",
    "race_4": "Race 4",
    "race_5": "Race 5",
}
LAST_FIRST_CLEANUP_LABEL = "Last/First Cleanup"
SPACE_LABEL = "<SPACE>"
EXPORT_OUTPUT_FILE_NAMES = (
    "valid_records.txt",
    "invalid_records.txt",
    "duplicate_records.txt",
    "corrected_full_file.txt",
    "defect_report.csv",
)
CONVERSION_OUTPUT_FILE_NAMES = (
    CCIPR60I_TEXT_FILE_NAME,
    CCIPR60I_BINARY_FILE_NAME,
)


class ValidatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CNDS Data Validation")
        self.root.geometry("1420x860")
        self.root.state("zoomed")
        self.profile = DEFAULT_PROFILE
        self.selected_paths: list[Path] = []
        self.result: FileValidationResult | None = None
        self.record_index: dict[str, RecordResult] = {}

        self.file_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select one or more CNDS fixed-width files to validate.")
        self.filter_var = tk.StringVar(value=FILTER_ALL)

        self.selected_duplicate_mode = DUPLICATE_NAME_DOB
        self.selected_ignored_fields: set[str] = set()
        self.override_config = OverrideConfig()
        self.conversion_config = ConversionConfig()
        self.field_labels = {field.name: field.label for field in self.profile.fields}

        self._build()

    def _build(self) -> None:
        self._configure_theme()

        root_frame = ttk.Frame(self.root, padding=16, style="App.TFrame")
        root_frame.pack(fill="both", expand=True)

        controls = ttk.LabelFrame(root_frame, text="Input", padding=12, style="Card.TLabelframe")
        controls.pack(fill="x")

        ttk.Label(controls, text="Files", style="App.TLabel").grid(row=0, column=0, sticky="w")
        files_entry = ttk.Entry(controls, textvariable=self.file_var, width=64, state="readonly")
        files_entry.grid(row=0, column=1, padx=8, sticky="w")
        self.browse_button = ttk.Button(controls, text="Browse", command=self.choose_files, underline=0)
        self.browse_button.grid(row=0, column=2, padx=4)
        self.options_button = ttk.Button(controls, text="Options...", command=self.open_options_dialog, underline=0)
        self.options_button.grid(row=0, column=3, padx=4)
        self.overrides_button = ttk.Button(controls, text="Overrides...", command=self.open_overrides_dialog, underline=5)
        self.overrides_button.grid(row=0, column=4, padx=4)
        self.validate_button = ttk.Button(controls, text="Validate", command=self.validate_selected_files, underline=0)
        self.validate_button.grid(row=0, column=5, padx=4)
        self.summary_button = ttk.Button(controls, text="Summary...", command=self.open_summary_dialog, underline=2)
        self.summary_button.grid(row=0, column=6, padx=4)
        self.export_button = ttk.Button(controls, text="Export Results", command=self.export_results, underline=0)
        self.export_button.grid(row=0, column=7, padx=4)
        self.convert_button = ttk.Button(controls, text="CCIPR60I...", command=self.open_conversion_dialog, underline=0)
        self.convert_button.grid(row=0, column=8, padx=4)
        self.help_button = ttk.Button(controls, text="Help", command=self.open_keyboard_help_dialog, underline=0)
        self.help_button.grid(row=0, column=9, padx=4)

        profile_frame = ttk.LabelFrame(root_frame, text="Profile", padding=12, style="Card.TLabelframe")
        profile_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(profile_frame, text=f"{self.profile.name} | Expected record length: {self.profile.record_length}", style="App.TLabel").pack(anchor="w")
        ttk.Label(profile_frame, text=self.profile.notes, wraplength=1320, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))

        status_frame = ttk.Frame(root_frame, style="App.TFrame")
        status_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(status_frame, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w")

        main_pane = ttk.Panedwindow(root_frame, orient="vertical")
        main_pane.pack(fill="both", expand=True, pady=(12, 0))

        top_pane = ttk.Panedwindow(main_pane, orient="horizontal")
        main_pane.add(top_pane, weight=3)

        records_frame = ttk.Labelframe(top_pane, text="Record Status", padding=8, style="Card.TLabelframe")
        preview_frame = ttk.Labelframe(top_pane, text="Record Preview", padding=8, style="Card.TLabelframe")
        top_pane.add(records_frame, weight=3)
        top_pane.add(preview_frame, weight=3)

        defects_frame = ttk.Labelframe(main_pane, text="Defects", padding=8, style="Card.TLabelframe")
        main_pane.add(defects_frame, weight=2)

        filter_row = ttk.Frame(records_frame, style="App.TFrame")
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Show", style="App.TLabel").pack(side="left")
        self.filter_box = ttk.Combobox(filter_row, textvariable=self.filter_var, values=(FILTER_ALL, FILTER_VALID, FILTER_INVALID, FILTER_DUPLICATE), state="readonly", width=22)
        self.filter_box.pack(side="left", padx=(8, 0))
        self.filter_box.bind("<<ComboboxSelected>>", self.on_filter_changed)

        records_container = ttk.Frame(records_frame, style="App.TFrame")
        records_container.pack(fill="both", expand=True)
        self.records_tree = ttk.Treeview(records_container, columns=("source", "line", "status", "issue_count", "duplicate_count"), show="headings", height=12, selectmode="browse")
        records_column_config = {
            "source": (220, "w"),
            "line": (70, "e"),
            "status": (160, "w"),
            "issue_count": (110, "e"),
            "duplicate_count": (130, "e"),
        }
        for name, (width, anchor) in records_column_config.items():
            self.records_tree.heading(name, text=name.replace("_", " ").title(), anchor=anchor)
            self.records_tree.column(name, width=width, anchor=anchor)
        records_scroll_y = ttk.Scrollbar(records_container, orient="vertical", command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=records_scroll_y.set)
        self.records_tree.pack(side="left", fill="both", expand=True)
        records_scroll_y.pack(side="right", fill="y")
        self.records_tree.bind("<<TreeviewSelect>>", self.on_record_select)

        preview_container = ttk.Frame(preview_frame, style="App.TFrame")
        preview_container.pack(fill="both", expand=True)
        self.preview_tree = ttk.Treeview(preview_container, columns=("field", "positions", "value"), show="headings", height=12)
        preview_column_config = {
            "field": (170, 150, False, "w"),
            "positions": (95, 95, False, "e"),
            "value": (540, 260, True, "w"),
        }
        for name, (width, minwidth, stretch, anchor) in preview_column_config.items():
            self.preview_tree.heading(name, text=name.replace("_", " ").title(), anchor=anchor)
            self.preview_tree.column(name, width=width, minwidth=minwidth, stretch=stretch, anchor=anchor)
        preview_scroll_y = ttk.Scrollbar(preview_container, orient="vertical", command=self.preview_tree.yview)
        preview_scroll_x = ttk.Scrollbar(preview_container, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=preview_scroll_y.set, xscrollcommand=preview_scroll_x.set)
        self.preview_tree.pack(side="left", fill="both", expand=True)
        preview_scroll_y.pack(side="right", fill="y")
        preview_scroll_x.pack(side="bottom", fill="x")
        self.preview_tree.tag_configure("invalid", background="#fff1a8", foreground="#1f1f1f")
        self.preview_tree.tag_configure("duplicate", background="#f6c1df", foreground="#1f1f1f")
        self.preview_tree.tag_configure("duplicate_invalid", background="#f3b2a2", foreground="#1f1f1f")

        defects_container = ttk.Frame(defects_frame, style="App.TFrame")
        defects_container.pack(fill="both", expand=True)
        self.defects_tree = ttk.Treeview(defects_container, columns=("source", "line", "field", "positions", "code", "message", "supplied_value"), show="headings", height=16)
        defects_column_config = {
            "source": (220, "w"),
            "line": (70, "e"),
            "field": (160, "w"),
            "positions": (90, "e"),
            "code": (170, "w"),
            "message": (360, "w"),
            "supplied_value": (260, "e"),
        }
        for name, (width, anchor) in defects_column_config.items():
            self.defects_tree.heading(name, text=name.replace("_", " ").title(), anchor=anchor)
            self.defects_tree.column(name, width=width, anchor=anchor)
        defects_scroll_y = ttk.Scrollbar(defects_container, orient="vertical", command=self.defects_tree.yview)
        defects_scroll_x = ttk.Scrollbar(defects_container, orient="horizontal", command=self.defects_tree.xview)
        self.defects_tree.configure(yscrollcommand=defects_scroll_y.set, xscrollcommand=defects_scroll_x.set)
        self.defects_tree.pack(side="left", fill="both", expand=True)
        defects_scroll_y.pack(side="right", fill="y")
        defects_scroll_x.pack(side="bottom", fill="x")

        self._bind_alt_shortcut(self.root, "b", self.on_alt_browse)
        self._bind_alt_shortcut(self.root, "o", self.on_alt_options)
        self._bind_alt_shortcut(self.root, "i", self.on_alt_overrides)
        self._bind_alt_shortcut(self.root, "v", self.on_alt_validate)
        self._bind_alt_shortcut(self.root, "m", self.on_alt_summary)
        self._bind_alt_shortcut(self.root, "e", self.on_alt_export)
        self._bind_alt_shortcut(self.root, "c", self.on_alt_convert)
        self._bind_alt_shortcut(self.root, "f", self.on_alt_focus_filter)
        self._bind_alt_shortcut(self.root, "r", self.on_alt_focus_records)
        self._bind_alt_shortcut(self.root, "p", self.on_alt_focus_preview)
        self._bind_alt_shortcut(self.root, "d", self.on_alt_focus_defects)
        self._bind_alt_shortcut(self.root, "h", self.on_alt_help)
        self.root.bind("<F1>", self.on_alt_help)

        self.update_action_states()

    def _configure_theme(self) -> None:
        self.root.configure(bg="#44484f")
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("App.TFrame", background="#44484f")
        style.configure("Card.TLabelframe", background="#44484f", foreground="#f0f0f0")
        style.configure("Card.TLabelframe.Label", background="#44484f", foreground="#f0f0f0")
        style.configure("App.TLabel", background="#44484f", foreground="#f0f0f0")
        style.configure("Muted.TLabel", background="#44484f", foreground="#d6d6d6")
        style.configure("Treeview", background="#f7f7f7", fieldbackground="#f7f7f7", foreground="#222222", rowheight=24)
        style.configure("Treeview.Heading", background="#c7ccd1", foreground="#000000")

    def profile_field_order(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.profile.fields)

    def _bind_alt_shortcut(self, widget: tk.Misc, key: str, handler) -> None:
        widget.bind(f"<Alt-{key.lower()}>", handler)
        widget.bind(f"<Alt-{key.upper()}>", handler)

    def _normalize_uppercase_limited(self, value: str, max_length: int, *, allow_space_label: bool = False) -> str:
        text = value.upper()
        if allow_space_label and SPACE_LABEL.startswith(text):
            return text[: len(SPACE_LABEL)]
        return text[:max_length]

    def _bind_entry_var(self, variable: tk.StringVar, max_length: int, *, allow_space_label: bool = False) -> None:
        def _normalize(*_args) -> None:
            current = variable.get()
            normalized = self._normalize_uppercase_limited(current, max_length, allow_space_label=allow_space_label)
            if current != normalized:
                variable.set(normalized)

        variable.trace_add("write", _normalize)

    def _fit_dialog_to_screen(
        self,
        dialog: tk.Toplevel,
        width: int,
        height: int,
        *,
        min_width: int | None = None,
        min_height: int | None = None,
    ) -> None:
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        fitted_width = min(width, max(360, screen_width - 80))
        fitted_height = min(height, max(360, screen_height - 120))
        x_pos = max(20, (screen_width - fitted_width) // 2)
        y_pos = max(20, (screen_height - fitted_height) // 2)
        dialog.geometry(f"{fitted_width}x{fitted_height}+{x_pos}+{y_pos}")
        dialog.minsize(min_width or min(fitted_width, width), min_height or min(fitted_height, height))

    def _create_modal_dialog(
        self,
        title: str,
        width: int,
        height: int,
        *,
        resizable: tuple[bool, bool] = (True, True),
        min_width: int | None = None,
        min_height: int | None = None,
    ) -> tuple[tk.Toplevel, Callable[[], None]]:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.configure(bg="#44484f")
        dialog.resizable(*resizable)
        self._fit_dialog_to_screen(dialog, width, height, min_width=min_width, min_height=min_height)
        dialog.grab_set()

        def close_dialog() -> None:
            if not dialog.winfo_exists():
                return
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        return dialog, close_dialog

    def override_status_text(self) -> str:
        if not self.override_config.has_overrides:
            return "No export overrides set."
        parts: list[str] = [
            f"Export overrides target: {OVERRIDE_SCOPE_REVERSE[self.override_config.target_scope]}",
            f"Export mode: {OVERRIDE_EXPORT_MODE_REVERSE[self.override_config.export_mode]}",
        ]
        field_parts: list[str] = []
        for field_name in OVERRIDE_FIELD_NAMES:
            if field_name not in self.override_config.field_values:
                continue
            raw_value = self.override_config.field_values[field_name]
            display_value = SPACE_LABEL if not raw_value.strip() else raw_value.strip()
            field_parts.append(f"{OVERRIDE_FIELD_LABELS[field_name]}={display_value}")
        if field_parts:
            parts.append("Fields: " + ", ".join(field_parts))
        if self.override_config.normalize_application_person_id:
            parts.append("Normalize Application Person ID")
        cleanup_parts: list[str] = []
        if self.override_config.cleanup_name_spaces:
            cleanup_parts.append("spaces")
        if self.override_config.cleanup_name_hyphens:
            cleanup_parts.append("hyphens")
        if self.override_config.cleanup_name_apostrophes:
            cleanup_parts.append("apostrophes")
        if cleanup_parts:
            parts.append(f"{LAST_FIRST_CLEANUP_LABEL}: {', '.join(cleanup_parts)}")
        return "; ".join(parts) + "."

    def update_action_states(self) -> None:
        has_files = bool(self.selected_paths)
        has_result = self.result is not None
        self.validate_button.configure(state="normal" if has_files else "disabled")
        self.summary_button.configure(state="normal" if has_result else "disabled")
        self.export_button.configure(state="normal" if has_result else "disabled")
        self.convert_button.configure(state="normal" if has_result else "disabled")

    def on_alt_browse(self, _event: tk.Event) -> str:
        self.choose_files()
        return "break"

    def on_alt_options(self, _event: tk.Event) -> str:
        self.open_options_dialog()
        return "break"

    def on_alt_overrides(self, _event: tk.Event) -> str:
        self.open_overrides_dialog()
        return "break"

    def on_alt_validate(self, _event: tk.Event) -> str:
        if str(self.validate_button.cget("state")) != "disabled":
            self.validate_selected_files()
        return "break"

    def on_alt_summary(self, _event: tk.Event) -> str:
        if str(self.summary_button.cget("state")) != "disabled":
            self.open_summary_dialog()
        return "break"

    def on_alt_export(self, _event: tk.Event) -> str:
        if str(self.export_button.cget("state")) != "disabled":
            self.export_results()
        return "break"

    def on_alt_convert(self, _event: tk.Event) -> str:
        if str(self.convert_button.cget("state")) != "disabled":
            self.open_conversion_dialog()
        return "break"

    def on_alt_focus_filter(self, _event: tk.Event) -> str:
        self.filter_box.focus_set()
        return "break"

    def on_alt_focus_records(self, _event: tk.Event) -> str:
        self.records_tree.focus_set()
        selection = self.records_tree.selection()
        if not selection:
            children = self.records_tree.get_children()
            if children:
                self.records_tree.selection_set(children[0])
                self.records_tree.focus(children[0])
        return "break"

    def on_alt_focus_preview(self, _event: tk.Event) -> str:
        self.preview_tree.focus_set()
        return "break"

    def on_alt_focus_defects(self, _event: tk.Event) -> str:
        self.defects_tree.focus_set()
        return "break"

    def on_alt_help(self, _event: tk.Event) -> str:
        self.open_keyboard_help_dialog()
        return "break"

    def open_keyboard_help_dialog(self) -> None:
        dialog, close_dialog = self._create_modal_dialog(
            "Keyboard Commands",
            620,
            520,
            resizable=(False, False),
            min_width=620,
            min_height=520,
        )

        frame = ttk.Frame(dialog, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Keyboard Commands", style="App.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Use these shortcuts to work through the app without a mouse.", style="Muted.TLabel").pack(anchor="w", pady=(4, 12))

        help_tree = ttk.Treeview(frame, columns=("command", "action"), show="headings", height=10, takefocus=False)
        help_tree.heading("command", text="Command", anchor="w")
        help_tree.heading("action", text="Action", anchor="w")
        help_tree.column("command", width=140, anchor="w")
        help_tree.column("action", width=420, anchor="w")
        help_tree.pack(fill="both", expand=True)

        help_rows = (
            ("Alt+B", "Browse for one or more input files"),
            ("Alt+O", "Open Validation Options"),
            ("Alt+I", "Open Export Overrides"),
            ("Alt+V", "Validate selected files"),
            ("Alt+M", "Open Summary dialog"),
            ("Alt+E", "Export results"),
            ("Alt+C", "Open CCIPR60I conversion export"),
            ("Alt+F", "Move focus to the Show filter"),
            ("Alt+R", "Move focus to Record Status"),
            ("Alt+P", "Move focus to Record Preview"),
            ("Alt+D", "Move focus to Defects"),
            ("Alt+H / F1", "Open this keyboard help dialog"),
            ("Tab / Shift+Tab", "Move between controls"),
            ("Arrow Keys", "Navigate focused lists and tables"),
            ("Esc", "Close the active dialog"),
        )
        for command, action in help_rows:
            help_tree.insert("", "end", values=(command, action))

        button_row = ttk.Frame(frame, style="App.TFrame")
        button_row.pack(fill="x", pady=(12, 0))
        close_button = ttk.Button(button_row, text="Close", command=close_dialog, underline=0)
        close_button.pack(side="right")
        close_button.focus_set()

        dialog.bind("<Escape>", lambda _event: (close_dialog(), "break")[1])
        self._bind_alt_shortcut(dialog, "c", lambda _event: (close_button.invoke(), "break")[1])
        dialog.wait_window()

    def open_options_dialog(self) -> None:
        dialog, base_close_dialog = self._create_modal_dialog(
            "Validation Options",
            920,
            640,
            resizable=(True, True),
            min_width=820,
            min_height=560,
        )

        frame = ttk.Frame(dialog, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        duplicate_mode_var = tk.StringVar(value=DUPLICATE_MODE_REVERSE[self.selected_duplicate_mode])
        ignore_vars = {field.name: tk.BooleanVar(value=field.name in self.selected_ignored_fields) for field in self.profile.fields}

        ttk.Label(frame, text="Duplicate rule", style="App.TLabel").grid(row=0, column=0, sticky="w")
        duplicate_mode_box = ttk.Combobox(frame, textvariable=duplicate_mode_var, values=tuple(DUPLICATE_MODE_LABELS.keys()), state="readonly", width=28)
        duplicate_mode_box.grid(row=0, column=1, sticky="w", padx=(12, 0))

        ttk.Label(frame, text="Bypass field validation", style="App.TLabel").grid(row=1, column=0, sticky="nw", pady=(14, 0))
        bypass_area = ttk.Frame(frame, style="App.TFrame")
        bypass_area.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=(14, 0))
        ttk.Label(
            bypass_area,
            text="Checked fields are skipped during defect validation. Duplicate matching still uses the selected duplicate rule. All layout fields are available below.",
            style="Muted.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 8))

        action_row = ttk.Frame(bypass_area, style="App.TFrame")
        action_row.pack(fill="x", pady=(0, 8))

        def select_none() -> None:
            for var in ignore_vars.values():
                var.set(False)

        def select_common_optional() -> None:
            for field_name, var in ignore_vars.items():
                var.set(field_name in COMMON_OPTIONAL_FIELDS)

        select_none_button = ttk.Button(action_row, text="Select None", command=select_none, underline=7)
        select_none_button.pack(side="left")
        select_common_button = ttk.Button(action_row, text="Select Common Optional Fields", command=select_common_optional, underline=9)
        select_common_button.pack(side="left", padx=(8, 0))

        list_container = ttk.Frame(bypass_area, style="App.TFrame")
        list_container.pack(fill="both", expand=True)
        canvas = tk.Canvas(list_container, background="#44484f", highlightthickness=0, borderwidth=0, width=700, height=360)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        checklist_frame = ttk.Frame(canvas, style="App.TFrame")
        checklist_frame.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=checklist_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        def close_dialog() -> None:
            canvas.unbind_all("<MouseWheel>")
            base_close_dialog()

        column_break = (len(self.profile.fields) + 1) // 2
        for index, field in enumerate(self.profile.fields):
            column = 0 if index < column_break else 1
            row = index if index < column_break else index - column_break
            padx = (0, 40) if column == 0 else (0, 0)
            ttk.Checkbutton(checklist_frame, text=field.label, variable=ignore_vars[field.name]).grid(row=row, column=column, sticky="w", padx=padx, pady=(0, 4))

        button_row = ttk.Frame(frame, style="App.TFrame")
        button_row.grid(row=2, column=0, columnspan=2, sticky="e", pady=(18, 0))

        def apply_and_close() -> None:
            self.selected_duplicate_mode = DUPLICATE_MODE_LABELS[duplicate_mode_var.get()]
            self.selected_ignored_fields = {name for name, var in ignore_vars.items() if var.get()}
            close_dialog()
            mode_text = duplicate_mode_label(self.selected_duplicate_mode)
            if self.selected_ignored_fields:
                labels = [self.field_labels[name] for name in self.profile_field_order() if name in self.selected_ignored_fields]
                self.status_var.set(f"Options updated. Duplicate rule: {mode_text}. Bypassed fields: {', '.join(labels)}.")
            else:
                self.status_var.set(f"Options updated. Duplicate rule: {mode_text}.")

        cancel_button = ttk.Button(button_row, text="Cancel", command=close_dialog, underline=0)
        cancel_button.pack(side="right")
        apply_button = ttk.Button(button_row, text="Apply", command=apply_and_close, underline=0)
        apply_button.pack(side="right", padx=(0, 8))

        duplicate_mode_box.focus_set()
        dialog.bind("<Escape>", lambda _event: (close_dialog(), "break")[1])
        self._bind_alt_shortcut(dialog, "n", lambda _event: (select_none(), "break")[1])
        self._bind_alt_shortcut(dialog, "m", lambda _event: (select_common_optional(), "break")[1])
        self._bind_alt_shortcut(dialog, "a", lambda _event: (apply_and_close(), "break")[1])
        self._bind_alt_shortcut(dialog, "c", lambda _event: (cancel_button.invoke(), "break")[1])

        dialog.wait_window()

    def open_overrides_dialog(self) -> None:
        dialog, base_close_dialog = self._create_modal_dialog(
            "Export Overrides",
            1080,
            760,
            resizable=(True, True),
            min_width=980,
            min_height=680,
        )

        frame = ttk.Frame(dialog, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        target_scope_var = tk.StringVar(value=OVERRIDE_SCOPE_REVERSE[self.override_config.target_scope])
        export_mode_var = tk.StringVar(value=OVERRIDE_EXPORT_MODE_REVERSE[self.override_config.export_mode])
        override_vars = {field_name: tk.BooleanVar(value=field_name in self.override_config.field_values) for field_name in OVERRIDE_FIELD_NAMES}
        field_lengths = {field.name: field.length for field in self.profile.fields}
        override_value_vars = {
            field_name: tk.StringVar(
                value=(
                    SPACE_LABEL
                    if field_name in self.override_config.field_values and not self.override_config.field_values[field_name].strip()
                    else self.override_config.field_values.get(field_name, "")
                )
            )
            for field_name in OVERRIDE_FIELD_NAMES
        }
        normalize_var = tk.BooleanVar(value=self.override_config.normalize_application_person_id)
        cleanup_spaces_var = tk.BooleanVar(value=self.override_config.cleanup_name_spaces)
        cleanup_hyphens_var = tk.BooleanVar(value=self.override_config.cleanup_name_hyphens)
        cleanup_apostrophes_var = tk.BooleanVar(value=self.override_config.cleanup_name_apostrophes)
        preview_var = tk.StringVar(value="Preview counts will appear after a validation run.")
        preview_after_id: str | None = None

        scroll_container = ttk.Frame(frame, style="App.TFrame")
        scroll_container.grid(row=0, column=0, sticky="nsew")
        scroll_container.columnconfigure(0, weight=1)
        scroll_container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_container, background="#44484f", highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding=(0, 0, 8, 0), style="App.TFrame")
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        content.columnconfigure(0, weight=1)

        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(content_window, width=event.width))

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        settings_frame = ttk.LabelFrame(content, text="Scope and Output", padding=12, style="Card.TLabelframe")
        settings_frame.grid(row=0, column=0, sticky="ew")
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Apply overrides to", style="App.TLabel").grid(row=0, column=0, sticky="w")
        scope_box = ttk.Combobox(settings_frame, textvariable=target_scope_var, values=tuple(OVERRIDE_SCOPE_LABELS.keys()), state="readonly", width=28)
        scope_box.grid(row=0, column=1, sticky="w", padx=(12, 0))

        ttk.Label(settings_frame, text="Export mode", style="App.TLabel").grid(row=1, column=0, sticky="w", pady=(12, 0))
        export_mode_box = ttk.Combobox(settings_frame, textvariable=export_mode_var, values=tuple(OVERRIDE_EXPORT_MODE_LABELS.keys()), state="readonly", width=36)
        export_mode_box.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(12, 0))

        notes_frame = ttk.LabelFrame(content, text="Notes", padding=12, style="Card.TLabelframe")
        notes_frame.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        ttk.Label(notes_frame, text="Overrides are applied during export review. Duplicate records are skipped.", style="Muted.TLabel", wraplength=920).pack(anchor="w")
        ttk.Label(notes_frame, text="Records updated by overrides are revalidated before they are written out.", style="Muted.TLabel", wraplength=920).pack(anchor="w", pady=(4, 0))
        ttk.Label(notes_frame, text="Race overrides apply only when the record has a missing or invalid race condition.", style="Muted.TLabel", wraplength=920).pack(anchor="w", pady=(4, 0))
        ttk.Label(notes_frame, text="Last/First cleanup can remove spaces, hyphens, and apostrophes independently within Last Name, First Name, and First Name Filler.", style="Muted.TLabel", wraplength=920).pack(anchor="w", pady=(4, 0))

        options_frame = ttk.LabelFrame(content, text="Additional Options", padding=12, style="Card.TLabelframe")
        options_frame.grid(row=2, column=0, sticky="ew", pady=(16, 0))

        normalize_check = ttk.Checkbutton(
            options_frame,
            text="Normalize Application Person ID (15-digits)",
            variable=normalize_var,
            command=lambda: schedule_preview_counts(),
        )
        normalize_check.pack(anchor="w")

        ttk.Label(options_frame, text=LAST_FIRST_CLEANUP_LABEL, style="App.TLabel").pack(anchor="w", pady=(10, 0))

        cleanup_spaces_check = ttk.Checkbutton(
            options_frame,
            text="Remove spaces",
            variable=cleanup_spaces_var,
            command=lambda: schedule_preview_counts(),
        )
        cleanup_spaces_check.pack(anchor="w", pady=(6, 0))

        cleanup_hyphens_check = ttk.Checkbutton(
            options_frame,
            text="Remove hyphens",
            variable=cleanup_hyphens_var,
            command=lambda: schedule_preview_counts(),
        )
        cleanup_hyphens_check.pack(anchor="w", pady=(4, 0))

        cleanup_apostrophes_check = ttk.Checkbutton(
            options_frame,
            text="Remove apostrophes",
            variable=cleanup_apostrophes_var,
            command=lambda: schedule_preview_counts(),
        )
        cleanup_apostrophes_check.pack(anchor="w", pady=(4, 0))

        presets_frame = ttk.LabelFrame(content, text="Presets", padding=12, style="Card.TLabelframe")
        presets_frame.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        for index in range(4):
            presets_frame.columnconfigure(index, weight=1)

        def build_temp_override_config() -> OverrideConfig:
            field_values: dict[str, str] = {}
            for field_name in OVERRIDE_FIELD_NAMES:
                if not override_vars[field_name].get():
                    continue
                raw_value = override_value_vars[field_name].get()
                field_values[field_name] = "" if raw_value == SPACE_LABEL else raw_value
            return OverrideConfig(
                target_scope=OVERRIDE_SCOPE_LABELS[target_scope_var.get()],
                export_mode=OVERRIDE_EXPORT_MODE_LABELS[export_mode_var.get()],
                field_values=field_values,
                normalize_application_person_id=normalize_var.get(),
                cleanup_name_spaces=cleanup_spaces_var.get(),
                cleanup_name_hyphens=cleanup_hyphens_var.get(),
                cleanup_name_apostrophes=cleanup_apostrophes_var.get(),
            )

        def update_preview_counts() -> None:
            temp_config = build_temp_override_config()
            if self.result is None:
                preview_var.set("Preview counts will appear after a validation run.")
                return
            total_records, valid_count, invalid_count, duplicate_count, duplicate_percentage = self._review_summary_counts(temp_config)
            preview_var.set(
                f"Post-override preview: Total {total_records} | Valid {valid_count} | Invalid {invalid_count} | Duplicates {duplicate_count} | Duplicate % {duplicate_percentage:.2f}%"
            )

        def schedule_preview_counts(*_args) -> None:
            nonlocal preview_after_id
            if preview_after_id is not None:
                try:
                    dialog.after_cancel(preview_after_id)
                except tk.TclError:
                    preview_after_id = None
            preview_after_id = dialog.after(250, update_preview_counts)

        def set_field_override(field_name: str, value: str) -> None:
            override_vars[field_name].set(True)
            override_value_vars[field_name].set(value)
            schedule_preview_counts()

        def set_ssn_zeroes() -> None:
            set_field_override("ssn", "000000000")

        def set_ethnicity_space() -> None:
            set_field_override("ethnicity", SPACE_LABEL)

        def set_language_en() -> None:
            set_field_override("language", "EN")

        def set_race_u_only() -> None:
            set_field_override("race_1", "U")
            for field_name in ("race_2", "race_3", "race_4", "race_5"):
                set_field_override(field_name, SPACE_LABEL)

        def clear_all_overrides() -> None:
            for field_name in OVERRIDE_FIELD_NAMES:
                override_vars[field_name].set(False)
                override_value_vars[field_name].set("")
            normalize_var.set(False)
            cleanup_spaces_var.set(False)
            cleanup_hyphens_var.set(False)
            cleanup_apostrophes_var.set(False)
            schedule_preview_counts()

        preset_buttons = (
            ("Set SSN to 000000000", set_ssn_zeroes),
            ("Set Ethnicity to <space>", set_ethnicity_space),
            ("Set Language to EN", set_language_en),
            ("Set Race to U only", set_race_u_only),
            ("Clear All Overrides", clear_all_overrides),
        )
        for index, (label, command) in enumerate(preset_buttons):
            ttk.Button(presets_frame, text=label, command=command).grid(row=index // 4, column=index % 4, padx=(0, 10), pady=(0, 10), sticky="ew")

        preview_frame = ttk.LabelFrame(content, text="Preview Impact", padding=12, style="Card.TLabelframe")
        preview_frame.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        ttk.Label(preview_frame, textvariable=preview_var, style="Muted.TLabel", wraplength=920).pack(anchor="w")

        field_frame = ttk.LabelFrame(content, text="Field Overrides", padding=12, style="Card.TLabelframe")
        field_frame.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        field_frame.columnconfigure(2, weight=1)

        ttk.Label(field_frame, text="Use", style="App.TLabel", width=6).grid(row=0, column=0, sticky="w")
        ttk.Label(field_frame, text="Field", style="App.TLabel", width=18).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Label(field_frame, text="Replacement Value", style="App.TLabel").grid(row=0, column=2, sticky="w")

        first_entry: ttk.Entry | None = None
        for row_index, field_name in enumerate(OVERRIDE_FIELD_NAMES, start=1):
            ttk.Checkbutton(field_frame, variable=override_vars[field_name], command=schedule_preview_counts).grid(row=row_index, column=0, sticky="w", pady=(0, 8))
            ttk.Label(field_frame, text=OVERRIDE_FIELD_LABELS[field_name], style="App.TLabel").grid(row=row_index, column=1, sticky="w", padx=(0, 12), pady=(0, 8))
            entry_width = max(field_lengths[field_name] + 2, 14)
            entry = ttk.Entry(field_frame, textvariable=override_value_vars[field_name], width=entry_width)
            entry.grid(row=row_index, column=2, sticky="w", pady=(0, 8))
            if first_entry is None:
                first_entry = entry
            self._bind_entry_var(override_value_vars[field_name], field_lengths[field_name], allow_space_label=True)

        button_row = ttk.Frame(frame, style="App.TFrame")
        button_row.grid(row=1, column=0, sticky="e", pady=(16, 0))

        def close_dialog() -> None:
            nonlocal preview_after_id
            canvas.unbind_all("<MouseWheel>")
            if preview_after_id is not None:
                try:
                    dialog.after_cancel(preview_after_id)
                except tk.TclError:
                    pass
                preview_after_id = None
            base_close_dialog()

        def apply_and_close() -> None:
            self.override_config = build_temp_override_config()
            if self.result is not None:
                self._populate_results()
                self.status_var.set(f"Overrides updated. {self.override_status_text()} {preview_var.get()}")
            else:
                self.status_var.set(self.override_status_text())
            close_dialog()

        cancel_button = ttk.Button(button_row, text="Cancel", command=close_dialog, underline=0)
        cancel_button.pack(side="right")
        apply_button = ttk.Button(button_row, text="Apply", command=apply_and_close, underline=0)
        apply_button.pack(side="right", padx=(0, 8))

        for variable in override_value_vars.values():
            variable.trace_add("write", schedule_preview_counts)
        target_scope_var.trace_add("write", schedule_preview_counts)
        export_mode_var.trace_add("write", schedule_preview_counts)
        normalize_var.trace_add("write", schedule_preview_counts)
        cleanup_spaces_var.trace_add("write", schedule_preview_counts)
        cleanup_hyphens_var.trace_add("write", schedule_preview_counts)
        cleanup_apostrophes_var.trace_add("write", schedule_preview_counts)
        update_preview_counts()

        if first_entry is not None:
            first_entry.focus_set()
        else:
            scope_box.focus_set()
        dialog.bind("<Escape>", lambda _event: (close_dialog(), "break")[1])
        dialog.bind("<Return>", lambda _event: (apply_button.invoke(), "break")[1])
        self._bind_alt_shortcut(dialog, "a", lambda _event: (apply_button.invoke(), "break")[1])
        self._bind_alt_shortcut(dialog, "c", lambda _event: (cancel_button.invoke(), "break")[1])

        dialog.wait_window()
    def open_summary_dialog(self) -> None:
        if self.result is None:
            messagebox.showwarning("No summary available", "Validate files before opening the summary.")
            return

        review_records = self._review_records()
        duplicate_records = tuple(record for record in review_records if record.is_duplicate)
        valid_records = tuple(record for record in review_records if record.is_valid)
        invalid_records = tuple(record for record in review_records if record.is_invalid_non_duplicate)
        duplicate_count = len(duplicate_records)
        duplicate_groups = len(
            {
                build_duplicate_key(record.fields, self.result.duplicate_mode)
                for record in duplicate_records
                if build_duplicate_key(record.fields, self.result.duplicate_mode) is not None
            }
        )
        defect_field_counts: Counter[str] = Counter()
        for record in review_records:
            for issue in record.issues:
                defect_field_counts[issue.field_label] += 1

        duplicate_percentage = (duplicate_count / len(review_records) * 100.0) if review_records else 0.0
        stats_rows = (
            ("Files", str(self.result.total_files)),
            ("Total records", str(len(review_records))),
            ("Valid records", str(len(valid_records))),
            ("Invalid records", str(len(invalid_records))),
            ("Duplicate records", str(duplicate_count)),
            ("Duplicate groups", str(duplicate_groups)),
            ("Duplicate %", f"{duplicate_percentage:.2f}%"),
            ("Total defects", str(sum(len(record.issues) for record in review_records))),
        )

        dialog, close_dialog = self._create_modal_dialog(
            "Validation Summary",
            900,
            600,
            resizable=(True, True),
            min_width=820,
            min_height=520,
        )

        frame = ttk.Frame(dialog, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        stats_frame = ttk.LabelFrame(frame, text="Summary Stats", padding=8, style="Card.TLabelframe")
        stats_frame.pack(fill="x")
        stats_container = ttk.Frame(stats_frame, style="App.TFrame")
        stats_container.pack(fill="both", expand=True)
        stats_tree = ttk.Treeview(stats_container, columns=("metric", "value"), show="headings", height=8)
        stats_tree.heading("metric", text="Metric", anchor="w")
        stats_tree.heading("value", text="Value", anchor="e")
        stats_tree.column("metric", width=260, anchor="w")
        stats_tree.column("value", width=180, anchor="e")
        stats_tree.pack(fill="x", expand=True)
        for metric, value in stats_rows:
            stats_tree.insert("", "end", values=(metric, value))

        lower_frame = ttk.Frame(frame, style="App.TFrame")
        lower_frame.pack(fill="x", expand=False, pady=(12, 0))

        field_frame = ttk.Labelframe(lower_frame, text="Defect Counts By Field", padding=8, style="Card.TLabelframe")
        field_frame.pack(anchor="w")
        field_container = ttk.Frame(field_frame, style="App.TFrame")
        field_container.pack(fill="both", expand=False)
        field_tree = ttk.Treeview(field_container, columns=("field", "count"), show="headings", height=5)
        field_tree.heading("field", text="Field", anchor="w")
        field_tree.heading("count", text="Count", anchor="e")
        field_tree.column("field", width=280, anchor="w")
        field_tree.column("count", width=90, anchor="e")
        field_scroll = ttk.Scrollbar(field_container, orient="vertical", command=field_tree.yview)
        field_tree.configure(yscrollcommand=field_scroll.set)
        field_tree.pack(side="left")
        field_scroll.pack(side="right", fill="y")

        for field_label, count in sorted(defect_field_counts.items(), key=lambda item: (-item[1], item[0])):
            field_tree.insert("", "end", values=(field_label, count))

        button_row = ttk.Frame(frame, style="App.TFrame")
        button_row.pack(fill="x", expand=False, pady=(12, 0))
        close_button = ttk.Button(button_row, text="Close", command=close_dialog, underline=0)
        close_button.pack(side="right")

        stats_tree.focus_set()
        dialog.bind("<Escape>", lambda _event: (close_dialog(), "break")[1])
        self._bind_alt_shortcut(dialog, "c", lambda _event: (close_button.invoke(), "break")[1])

        dialog.wait_window()

    def open_conversion_dialog(self) -> None:
        if self.result is None:
            messagebox.showwarning("No conversion available", "Validate files before opening CCIPR60I conversion.")
            return

        dialog, close_dialog = self._create_modal_dialog(
            "CCIPR60I Conversion",
            980,
            620,
            resizable=(False, False),
            min_width=980,
            min_height=620,
        )

        frame = ttk.Frame(dialog, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        scope_var = tk.StringVar(value=CONVERSION_SCOPE_REVERSE[self.conversion_config.scope])
        format_var = tk.StringVar(value=CONVERSION_FORMAT_REVERSE[self.conversion_config.output_format])
        accounting_var = tk.StringVar(value=self.conversion_config.accounting_info)
        comment_var = tk.StringVar(value=self.conversion_config.testing_comment)
        program_var = tk.StringVar(value=self.conversion_config.last_changed_program_id)
        user_var = tk.StringVar(value=self.conversion_config.last_changed_user_id)
        preview_var = tk.StringVar()

        self._bind_entry_var(accounting_var, 6)
        self._bind_entry_var(comment_var, 12)
        self._bind_entry_var(program_var, 8)
        self._bind_entry_var(user_var, 8)

        ttk.Label(frame, text="Convert records", style="App.TLabel").grid(row=0, column=0, sticky="w")
        scope_box = ttk.Combobox(frame, textvariable=scope_var, values=tuple(CONVERSION_SCOPE_LABELS.keys()), state="readonly", width=28)
        scope_box.grid(row=0, column=1, sticky="w", padx=(12, 0))

        ttk.Label(frame, text="Output format", style="App.TLabel").grid(row=1, column=0, sticky="w", pady=(12, 0))
        format_box = ttk.Combobox(frame, textvariable=format_var, values=tuple(CONVERSION_FORMAT_LABELS.keys()), state="readonly", width=24)
        format_box.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(12, 0))

        ttk.Label(frame, text="Accounting Info", style="App.TLabel").grid(row=2, column=0, sticky="w", pady=(18, 0))
        ttk.Entry(frame, textvariable=accounting_var, width=8).grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(18, 0))

        ttk.Label(frame, text="Testing Comment", style="App.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=comment_var, width=14).grid(row=3, column=1, sticky="w", padx=(12, 0), pady=(12, 0))

        ttk.Label(frame, text="Last Changed Program ID", style="App.TLabel").grid(row=4, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=program_var, width=10).grid(row=4, column=1, sticky="w", padx=(12, 0), pady=(12, 0))

        ttk.Label(frame, text="Last Changed User ID", style="App.TLabel").grid(row=5, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=user_var, width=10).grid(row=5, column=1, sticky="w", padx=(12, 0), pady=(12, 0))

        note_frame = ttk.LabelFrame(frame, text="Notes", padding=8, style="Card.TLabelframe")
        note_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Label(
            note_frame,
            text="Text export writes a UTF-8 readable preview line per record. Binary export writes strict FB 1000 records encoded as EBCDIC CP037 for mainframe upload.",
            style="Muted.TLabel",
            wraplength=840,
        ).pack(anchor="w")
        ttk.Label(
            note_frame,
            textvariable=preview_var,
            style="Muted.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(8, 0))

        def build_temp_config() -> ConversionConfig:
            return ConversionConfig(
                scope=CONVERSION_SCOPE_LABELS[scope_var.get()],
                output_format=CONVERSION_FORMAT_LABELS[format_var.get()],
                accounting_info=accounting_var.get().strip().upper() or "DHRCCI",
                testing_comment=comment_var.get().strip().upper() or "CCICREATE",
                last_changed_program_id=program_var.get().strip().upper() or "CCIBTH60",
                last_changed_user_id=user_var.get().strip().upper(),
            )

        def refresh_preview(*_args) -> None:
            config = build_temp_config()
            eligible_records = self._conversion_source_records(config)
            preview_var.set(
                f"Eligible records for conversion: {len(eligible_records)}. "
                f"Defaults in use: Accounting Info {config.accounting_info}, Testing Comment {config.testing_comment}, "
                f"Program ID {config.last_changed_program_id}, User ID {config.last_changed_user_id or '<blank>'}."
            )

        for variable in (scope_var, format_var, accounting_var, comment_var, program_var, user_var):
            variable.trace_add("write", refresh_preview)
        refresh_preview()

        button_row = ttk.Frame(frame, style="App.TFrame")
        button_row.grid(row=7, column=0, columnspan=2, sticky="e", pady=(18, 0))

        def apply_and_export() -> None:
            self.conversion_config = build_temp_config()
            close_dialog()
            self.export_ccipr60i()

        cancel_button = ttk.Button(button_row, text="Cancel", command=close_dialog, underline=0)
        cancel_button.pack(side="right")
        export_button = ttk.Button(button_row, text="Export", command=apply_and_export, underline=1)
        export_button.pack(side="right", padx=(0, 8))

        scope_box.focus_set()
        dialog.bind("<Escape>", lambda _event: (close_dialog(), "break")[1])
        dialog.bind("<Return>", lambda _event: (export_button.invoke(), "break")[1])
        self._bind_alt_shortcut(dialog, "x", lambda _event: (export_button.invoke(), "break")[1])
        self._bind_alt_shortcut(dialog, "c", lambda _event: (cancel_button.invoke(), "break")[1])
        dialog.wait_window()

    def _record_after_overrides(self, record: RecordResult, config: OverrideConfig | None = None) -> RecordResult:
        config = config or self.override_config
        if not should_apply_overrides(record, config):
            return record
        updated_fields = apply_overrides_to_fields(record.fields, self.profile, config, record=record)
        export_raw_record = serialize_fields(updated_fields, self.profile)
        return validate_record(
            record.source_path,
            record.line_number,
            export_raw_record,
            self.profile,
            ignored_fields=self.selected_ignored_fields,
        )

    def _review_records(self, config: OverrideConfig | None = None) -> tuple[RecordResult, ...]:
        if self.result is None:
            return ()
        return tuple(self._record_after_overrides(record, config) for record in self.result.records)

    def _review_summary_counts(self, config: OverrideConfig | None = None) -> tuple[int, int, int, int, float]:
        review_records = self._review_records(config)
        total_records = len(review_records)
        valid_count = sum(1 for record in review_records if record.is_valid)
        invalid_count = sum(1 for record in review_records if record.is_invalid_non_duplicate)
        duplicate_count = sum(1 for record in review_records if record.is_duplicate)
        duplicate_percentage = (duplicate_count / total_records * 100.0) if total_records else 0.0
        return total_records, valid_count, invalid_count, duplicate_count, duplicate_percentage

    def _sort_key(self, record: RecordResult) -> tuple[tuple[str, ...], str, int]:
        mode = self.result.duplicate_mode if self.result is not None else self.selected_duplicate_mode
        duplicate_key = build_duplicate_key(record.fields, mode)
        if duplicate_key is None:
            duplicate_key = (
                record.fields["last_name"].strip(),
                record.fields["first_name"].strip(),
                record.fields["date_of_birth"].strip(),
                record.fields["sex"].strip(),
            )
        return (duplicate_key, record.source_name.lower(), record.line_number)

    def _filtered_records(self) -> tuple[RecordResult, ...]:
        records = self._review_records()
        if self.filter_var.get() == FILTER_VALID:
            records = tuple(record for record in records if record.is_valid)
        elif self.filter_var.get() == FILTER_INVALID:
            records = tuple(record for record in records if record.is_invalid_non_duplicate)
        elif self.filter_var.get() == FILTER_DUPLICATE:
            records = tuple(record for record in records if record.is_duplicate)
        return tuple(sorted(records, key=self._sort_key))

    def _format_issue_value(self, issue: ValidationIssue) -> str:
        value = issue.value
        if issue.field_name == "record":
            return value
        trimmed = value.strip()
        if trimmed:
            return trimmed
        if value:
            return "<spaces>"
        return "<blank>"

    def _format_field_value(self, value: str) -> str:
        trimmed = value.strip()
        if trimmed:
            return trimmed
        if value:
            return "<spaces>"
        return "<blank>"

    def _field_highlight_tag(self, record: RecordResult, field_name: str, start: int, end: int) -> tuple[str, ...]:
        has_invalid = any(
            issue.code != "DUPLICATE_MATCH_KEY"
            and (
                issue.field_name == field_name
                or (issue.field_name == "race_group" and field_name.startswith("race_"))
            )
            and not (issue.end < start or issue.start > end)
            for issue in record.issues
        )
        duplicate_fields = {"last_name", "first_name", "date_of_birth"}
        mode = self.result.duplicate_mode if self.result is not None else self.selected_duplicate_mode
        if mode == DUPLICATE_NAME_DOB_SEX:
            duplicate_fields = set(DUPLICATE_HIGHLIGHT_FIELDS)
        has_duplicate = record.is_duplicate and field_name in duplicate_fields
        if has_invalid and has_duplicate:
            return ("duplicate_invalid",)
        if has_invalid:
            return ("invalid",)
        if has_duplicate:
            return ("duplicate",)
        return ()

    def reset_session_settings(self) -> None:
        self.selected_duplicate_mode = DUPLICATE_NAME_DOB
        self.selected_ignored_fields = set()
        self.override_config = OverrideConfig()
        self.conversion_config = ConversionConfig()

    def choose_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Select CNDS Files", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not selected:
            return
        self.selected_paths = [Path(path) for path in selected]
        self.result = None
        self.reset_session_settings()
        self.update_action_states()
        if len(self.selected_paths) == 1:
            self.file_var.set(str(self.selected_paths[0]))
        else:
            self.file_var.set(f"{len(self.selected_paths)} files selected")
        self.status_var.set(f"{len(self.selected_paths)} file(s) selected. Validation options and overrides were reset to defaults.")
    def validate_selected_files(self) -> None:
        if not self.selected_paths:
            messagebox.showwarning("No files selected", "Choose one or more files before validating.")
            return
        missing = [str(path) for path in self.selected_paths if not path.exists()]
        if missing:
            messagebox.showerror("File not found", "Could not find:\n" + "\n".join(missing))
            return
        try:
            self.result = validate_files(
                self.selected_paths,
                self.profile,
                ignored_fields=self.selected_ignored_fields,
                duplicate_mode=self.selected_duplicate_mode,
            )
        except Exception as exc:
            self.result = None
            self.update_action_states()
            messagebox.showerror("Validation failed", str(exc))
            return
        self.update_action_states()
        self._populate_results()
        mode_text = duplicate_mode_label(self.selected_duplicate_mode)
        duplicate_text = f"Duplicate rule: {mode_text}. Duplicate %: {self.result.duplicate_percentage:.2f}%."
        message = f"Validation finished for {len(self.selected_paths)} file(s). {duplicate_text}"
        if self.selected_ignored_fields:
            labels = [self.field_labels[name] for name in self.profile_field_order() if name in self.selected_ignored_fields]
            message += f" Bypassed fields: {', '.join(labels)}."
        else:
            message += " Display and exports are sorted by that key across all selected files."
        if self.override_config.has_overrides:
            message += " " + self.override_status_text()
        self.status_var.set(message)

    def _populate_results(self) -> None:
        assert self.result is not None
        self.record_index.clear()
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        for item in self.defects_tree.get_children():
            self.defects_tree.delete(item)

        for record in self._filtered_records():
            record_id = f"{record.source_name}-{record.line_number}"
            self.record_index[record_id] = record
            self.records_tree.insert("", "end", iid=record_id, values=(record.source_name, record.line_number, record.status_label, len(record.issues), record.duplicate_group_size))

        children = self.records_tree.get_children()
        if children:
            first = children[0]
            self.records_tree.selection_set(first)
            self.records_tree.focus(first)
            self._show_selected_record(self.record_index[first])
        else:
            self.status_var.set("No records match the current filter.")

    def on_filter_changed(self, _event: tk.Event) -> None:
        if self.result is not None:
            self._populate_results()

    def on_record_select(self, _event: tk.Event) -> None:
        selection = self.records_tree.selection()
        if not selection:
            return
        record = self.record_index.get(selection[0])
        if record is not None:
            self._show_selected_record(record)

    def _show_selected_record(self, record: RecordResult) -> None:
        self._show_record_preview(record)
        self._show_record_defects(record)

    def _show_record_preview(self, record: RecordResult) -> None:
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        for field in self.profile.fields:
            value = record.fields.get(field.name, "")
            tags = self._field_highlight_tag(record, field.name, field.start, field.end)
            self.preview_tree.insert("", "end", values=(field.label, f"{field.start}-{field.end}", self._format_field_value(value)), tags=tags)

    def _show_record_defects(self, record: RecordResult) -> None:
        for item in self.defects_tree.get_children():
            self.defects_tree.delete(item)
        for issue in record.issues:
            self.defects_tree.insert("", "end", values=(issue.source_path.stem, issue.line_number, issue.field_label, f"{issue.start}-{issue.end}", issue.code, issue.message, self._format_issue_value(issue)))

    def open_export_complete_dialog(
        self,
        target_dir: Path,
        exported_paths: tuple[Path, ...],
        validation_notes: tuple[str, ...] = (),
    ) -> None:
        note_lines = max(1, len(validation_notes))
        dialog_height = 420 + (32 * min(note_lines, 4))
        dialog, close_dialog = self._create_modal_dialog(
            "Export Complete",
            680,
            min(dialog_height, 620),
            resizable=(True, True),
            min_width=620,
            min_height=420,
        )

        frame = ttk.Frame(dialog, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        folder_frame = ttk.LabelFrame(frame, text="Export Folder", padding=8, style="Card.TLabelframe")
        folder_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(folder_frame, text=str(target_dir), style="App.TLabel", wraplength=620).pack(anchor="w")

        files_frame = ttk.LabelFrame(frame, text="Created Files", padding=8, style="Card.TLabelframe")
        files_frame.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        files_tree = ttk.Treeview(files_frame, columns=("file_name",), show="headings", height=max(3, min(len(exported_paths), 4)))
        files_tree.heading("file_name", text="File Name", anchor="w")
        files_tree.column("file_name", width=620, anchor="w")
        files_tree.pack(fill="x")
        for exported_path in exported_paths:
            files_tree.insert("", "end", values=(exported_path.name,))

        if validation_notes:
            notes_frame = ttk.LabelFrame(frame, text="Validation Checks", padding=8, style="Card.TLabelframe")
            notes_frame.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
            notes_text = tk.Text(
                notes_frame,
                height=min(max(len(validation_notes), 2), 5),
                wrap="word",
                relief="flat",
                borderwidth=0,
                background="#44484f",
                foreground="#d6d6d6",
                insertbackground="#d6d6d6",
            )
            notes_text.pack(fill="both", expand=True)
            notes_text.insert("1.0", "\n".join(validation_notes))
            notes_text.configure(state="disabled")

        button_row = ttk.Frame(frame, style="App.TFrame")
        button_row.grid(row=3, column=0, sticky="e", pady=(18, 0))
        ok_button = ttk.Button(button_row, text="OK", command=close_dialog, underline=0)
        ok_button.pack(side="right")

        ok_button.focus_set()
        dialog.bind("<Escape>", lambda _event: (close_dialog(), "break")[1])
        self._bind_alt_shortcut(dialog, "o", lambda _event: (ok_button.invoke(), "break")[1])

        dialog.wait_window()

    def _build_export_buckets(self) -> tuple[list[str], list[str], list[str]]:
        review_records = self._review_records()
        valid_records = [record.raw_record for record in sorted((record for record in review_records if record.is_valid), key=self._sort_key)]
        invalid_records = [record.raw_record for record in sorted((record for record in review_records if record.is_invalid_non_duplicate), key=self._sort_key)]
        duplicate_records = [record.raw_record for record in sorted((record for record in review_records if record.is_duplicate), key=self._sort_key)]
        return valid_records, invalid_records, duplicate_records

    def _managed_export_paths(self, target_dir: Path) -> tuple[Path, ...]:
        return tuple(target_dir / file_name for file_name in EXPORT_OUTPUT_FILE_NAMES)

    def _managed_conversion_paths(self, target_dir: Path) -> tuple[Path, ...]:
        return tuple(target_dir / file_name for file_name in CONVERSION_OUTPUT_FILE_NAMES)

    def _binary_validation_notes(self, summary: BinaryValidationSummary) -> tuple[str, ...]:
        return (f"Binary file validated: {summary.record_count} record(s).",)

    def _conversion_source_records(self, config: ConversionConfig | None = None) -> tuple[RecordResult, ...]:
        if self.result is None:
            return ()
        config = config or self.conversion_config
        if config.scope == CONVERSION_SCOPE_VALID_AND_CORRECTED:
            source_records = self._review_records()
        else:
            source_records = self.result.records
        return tuple(
            sorted(
                (
                    record
                    for record in source_records
                    if record.is_valid and not record.is_duplicate
                ),
                key=self._sort_key,
            )
        )

    def export_ccipr60i(self) -> None:
        if self.result is None:
            messagebox.showwarning("Nothing to convert", "Validate files before exporting CCIPR60I.")
            return
        output_dir = filedialog.askdirectory(title="Choose CCIPR60I Export Folder")
        if not output_dir:
            return
        target_dir = Path(output_dir)
        text_path = target_dir / CCIPR60I_TEXT_FILE_NAME
        binary_path = target_dir / CCIPR60I_BINARY_FILE_NAME

        existing_paths = [path for path in self._managed_conversion_paths(target_dir) if path.exists()]
        if existing_paths:
            overwrite = messagebox.askyesno(
                "Overwrite Existing CCIPR60I Files",
                "One or more CCIPR60I export files already exist in this folder. Overwrite them and remove stale output files first?",
                parent=self.root,
            )
            if not overwrite:
                return
            for path in existing_paths:
                path.unlink()

        source_records = self._conversion_source_records()
        if not source_records:
            messagebox.showwarning("No eligible records", "No records match the selected CCIPR60I conversion scope.")
            return

        converted_records = [build_ccipr60i_record(record, self.conversion_config) for record in source_records]
        exported_paths: list[Path] = []
        validation_notes: list[str] = []
        if self.conversion_config.output_format in (CONVERSION_FORMAT_BOTH, CONVERSION_FORMAT_TEXT):
            write_ccipr60i_text(text_path, converted_records)
            exported_paths.append(text_path)
        if self.conversion_config.output_format in (CONVERSION_FORMAT_BOTH, CONVERSION_FORMAT_BINARY):
            write_ccipr60i_binary(binary_path, converted_records)
            binary_summary = validate_binary_file(binary_path)
            validation_notes.extend(self._binary_validation_notes(binary_summary))
            exported_paths.append(binary_path)

        self.status_var.set(
            f"CCIPR60I export complete for {len(converted_records)} record(s). "
            f"Scope: {CONVERSION_SCOPE_REVERSE[self.conversion_config.scope]}. "
            f"Format: {CONVERSION_FORMAT_REVERSE[self.conversion_config.output_format]}."
        )
        self.open_export_complete_dialog(target_dir, tuple(exported_paths), tuple(validation_notes))

    def export_results(self) -> None:
        if self.result is None:
            messagebox.showwarning("Nothing to export", "Validate files before exporting.")
            return
        output_dir = filedialog.askdirectory(title="Choose Export Folder")
        if not output_dir:
            return
        target_dir = Path(output_dir)
        valid_path = target_dir / "valid_records.txt"
        invalid_path = target_dir / "invalid_records.txt"
        duplicate_path = target_dir / "duplicate_records.txt"
        corrected_path = target_dir / "corrected_full_file.txt"
        defects_path = target_dir / "defect_report.csv"

        existing_paths = [path for path in self._managed_export_paths(target_dir) if path.exists()]
        if existing_paths:
            overwrite = messagebox.askyesno(
                "Overwrite Existing Export Files",
                "One or more CNDS export files already exist in this folder. Overwrite them and remove stale output files first?",
                parent=self.root,
            )
            if not overwrite:
                return
            for path in existing_paths:
                path.unlink()

        valid_records, invalid_records, duplicate_records = self._build_export_buckets()
        review_records = self._review_records()
        corrected_records = [record.raw_record for record in sorted(review_records, key=self._sort_key)]

        exported_paths: list[Path] = []
        if self.override_config.export_mode in (OVERRIDE_EXPORT_FULL_ONLY, OVERRIDE_EXPORT_FULL_AND_SPLIT):
            export_records(corrected_path, corrected_records)
            exported_paths.append(corrected_path)

        if self.override_config.export_mode in (OVERRIDE_EXPORT_SPLIT_ONLY, OVERRIDE_EXPORT_FULL_AND_SPLIT):
            export_records(valid_path, valid_records)
            export_records(invalid_path, invalid_records)
            export_records(duplicate_path, duplicate_records)
            exported_paths.extend((valid_path, invalid_path, duplicate_path))

        export_defects_csv_records(defects_path, review_records)
        exported_paths.append(defects_path)

        self.open_export_complete_dialog(target_dir, tuple(exported_paths))
def run() -> None:
    root = tk.Tk()
    app = ValidatorApp(root)
    app.root.mainloop()
























































