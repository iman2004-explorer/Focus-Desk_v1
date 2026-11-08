import tkinter as tk
from tkinter import ttk
from datetime import date
import subprocess

from focus_backend import FocusBackend


BG = "#F4F6FA"
CARD = "#FFFFFF"
TEXT = "#202635"
MUTED = "#7B8495"
ACCENT = "#5B6CFF"
GREEN = "#31A879"


class Dashboard(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Focus Desk")
        self.geometry("1100x760")
        self.minsize(900, 640)
        self.configure(bg=BG)
        self.theme_mode = tk.StringVar(value="System")
        self._active_theme = None
        self._theme_colors = {}
        self.nav_rows = {}
        self.task_items = []
        self.focus_backend = FocusBackend()

        self._build_sidebar()
        self._build_content()
        self._select_section("Dashboard")
        self._apply_theme()
        self._watch_system_theme()

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg="#20283B", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="◉  Focus Desk", bg="#20283B", fg="white",
            font=("Helvetica", 17, "bold")
        ).pack(anchor="w", padx=22, pady=(28, 42))

        items = [("▦", "Dashboard"), ("✓", "Tasks"),
                 ("◷", "App time"), ("◉", "Focus mode"), ("▤", "Reports")]
        for icon, label in items:
            row = tk.Frame(sidebar, bg="#20283B", cursor="hand2")
            row.pack(fill="x", padx=12, pady=4)
            icon_label = tk.Label(row, text=icon, bg="#20283B", fg="#AAB2C2",
                                  font=("Helvetica", 13), width=3)
            icon_label.pack(side="left", padx=(7, 0), pady=11)
            text_label = tk.Label(row, text=label, bg="#20283B", fg="#AAB2C2",
                                  font=("Helvetica", 11))
            text_label.pack(side="left")
            self.nav_rows[label] = (row, icon_label, text_label)
            for widget in (row, icon_label, text_label):
                widget.bind("<Button-1>", lambda _event, section=label: self._select_section(section))

        tk.Frame(sidebar, bg="#3A4357", height=1).pack(fill="x", padx=20, pady=(30, 18))
        tk.Label(sidebar, text="YOUR SPACE", bg="#20283B", fg="#7F899D",
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=22, pady=(0, 12))
        tk.Label(sidebar, text="⚙  Settings", bg="#20283B", fg="#AAB2C2",
                 font=("Helvetica", 11)).pack(anchor="w", padx=25, pady=8)

        tk.Label(sidebar, text="Local profile", bg="#20283B", fg="#AAB2C2",
                 font=("Helvetica", 10)).pack(side="bottom", anchor="w", padx=22, pady=22)

    def _build_content(self):
        content = tk.Frame(self, bg=BG)
        content.pack(side="left", fill="both", expand=True, padx=34, pady=28)

        header = tk.Frame(content, bg=BG)
        header.pack(fill="x", pady=(0, 24))
        heading = tk.Frame(header, bg=BG)
        heading.pack(fill="x")
        self.page_title = tk.Label(heading, text="Good morning", bg=BG, fg=TEXT,
                                   font=("Helvetica", 28, "bold"))
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(
            heading, text="Here’s your productivity overview for today.",
            bg=BG, fg=MUTED, font=("Helvetica", 11)
        )
        self.page_subtitle.pack(anchor="w", pady=(5, 0))
        controls = tk.Frame(header, bg=BG)
        controls.pack(fill="x", pady=(10, 0))
        tk.Label(controls, text=date.today().strftime("%A, %B %d"), bg=BG, fg=MUTED,
                 font=("Helvetica", 11)).pack(side="left", padx=(0, 14), pady=8)
        tk.Label(controls, text="Theme", bg=BG, fg=MUTED,
                 font=("Helvetica", 9)).pack(side="left", padx=(0, 5), pady=8)
        theme_select = tk.OptionMenu(
            controls, self.theme_mode, "System", "Light", "Dark",
            command=self._on_theme_change
        )
        theme_select.config(bg=CARD, fg=TEXT, activebackground=CARD,
                            activeforeground=TEXT, relief="flat", bd=0,
                            highlightthickness=1, highlightbackground="#E8EBF1")
        theme_select["menu"].config(bg=CARD, fg=TEXT, activebackground="#EEF0FF",
                                    activeforeground=TEXT, relief="flat")
        theme_select.pack(side="left")
        self.theme_select = theme_select

        stats = tk.Frame(content, bg=BG)
        stats.pack(fill="x", pady=(0, 22))
        self._stat_card(stats, "FOCUS TIME", "3h 24m", "Today so far", ACCENT)
        self._stat_card(stats, "TASKS DONE", "1 of 4", "3 tasks remaining", GREEN)
        self._stat_card(stats, "TOP APP", "Code Editor", "1h 12m today", "#E79742")

        panels = tk.Frame(content, bg=BG)
        panels.pack(fill="both", expand=True)
        panels.grid_columnconfigure(0, weight=3, uniform="panel")
        panels.grid_columnconfigure(1, weight=2, uniform="panel")
        panels.grid_rowconfigure(0, weight=1)

        tasks = self._panel(panels, "Today's tasks", "3 remaining")
        tasks.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.task_list = tk.Frame(tasks, bg=CARD)
        self.task_list.pack(fill="x")
        self._task_row(self.task_list, "Review project notes", "09:30", True)
        self._task_row(self.task_list, "Prepare weekly report", "11:00", False)
        self._task_row(self.task_list, "Take a screen break", "13:00", False)
        self._task_row(self.task_list, "Plan tomorrow", "16:30", False)
        tk.Button(tasks, text="+  Add a task", command=self._add_task,
                  bg="#EEF0FF", fg=ACCENT, activebackground="#E3E6FF",
                  activeforeground=ACCENT, relief="flat", bd=0,
                  font=("Helvetica", 10, "bold"), padx=12, pady=9,
                  cursor="hand2").pack(anchor="w", padx=20, pady=(12, 18))

        usage = self._panel(panels, "App time", "Today")
        usage.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self._usage_row(usage, "Code Editor", "1h 12m", 0.78, ACCENT)
        self._usage_row(usage, "Browser", "58m", 0.62, "#39A88A")
        self._usage_row(usage, "Mail", "34m", 0.38, "#E79742")
        self._usage_row(usage, "Other apps", "40m", 0.46, "#8993A6")
        tk.Label(usage, text="App tracking will appear here", bg=CARD, fg=MUTED,
                 font=("Helvetica", 9)).pack(anchor="w", padx=20, pady=(17, 18))

    def _select_section(self, section):
        pages = {
            "Dashboard": ("Good morning", "Here’s your productivity overview for today."),
            "Tasks": ("Your tasks", "Check off a task or add something new to your list."),
            "App time": ("App time", "A colorful snapshot of where your time went today."),
            "Focus mode": ("Focus mode", "Set distractions aside and protect your focus time."),
            "Reports": ("Your reports", "Review today’s focus and activity at a glance.")
        }
        if section == "Focus mode":
            self._open_focus_mode()
        self.page_title.config(text=pages[section][0])
        self.page_subtitle.config(text=pages[section][1])
        dark = self._active_theme == "dark"
        active_bg = "#303B55" if dark else "#343E56"
        sidebar_bg = "#111725" if dark else "#20283B"
        inactive_fg = "#B8C1D1" if dark else "#AAB2C2"
        for label, widgets in self.nav_rows.items():
            active = label == section
            row, icon_label, text_label = widgets
            row_color = active_bg if active else sidebar_bg
            foreground = "#FFFFFF" if active else inactive_fg
            row.configure(bg=row_color)
            icon_label.configure(bg=row_color, fg=foreground)
            text_label.configure(bg=row_color, fg=foreground,
                                 font=("Helvetica", 11, "bold" if active else "normal"))

    def _on_theme_change(self, _selected=None):
        self._apply_theme()

    def _open_focus_mode(self):
        if getattr(self, "focus_window", None) is not None and self.focus_window.winfo_exists():
            self.focus_window.lift()
            return

        colors = self._theme_colors
        window = tk.Toplevel(self)
        self.focus_window = window
        window.title("Focus mode")
        window.geometry("460x560")
        window.minsize(400, 480)
        window.configure(bg=colors[BG])
        window.protocol("WM_DELETE_WINDOW", self._close_focus_mode)

        tk.Label(window, text="Protect your focus", bg=colors[BG], fg=colors[TEXT],
                 font=("Helvetica", 21, "bold")).pack(anchor="w", padx=24, pady=(22, 4))
        tk.Label(window, text="Choose apps and websites to avoid during a session.",
                 bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10),
                 wraplength=400, justify="left").pack(anchor="w", padx=24, pady=(0, 8))
        tk.Label(window,
                 text="Your targets are saved and the timer works. Blocking apps or sites requires separate OS or browser integration.",
                 bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 9),
                 wraplength=400, justify="left").pack(anchor="w", padx=24, pady=(0, 16))

        card = tk.Frame(window, bg=colors[CARD], highlightbackground=colors["#E8EBF1"],
                        highlightthickness=1)
        card.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        tk.Label(card, text="BLOCK LIST", bg=colors[CARD], fg=colors[MUTED],
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(15, 8))

        entry_row = tk.Frame(card, bg=colors[CARD])
        entry_row.pack(fill="x", padx=16)
        self.focus_entry = tk.Entry(entry_row, relief="flat", bd=0,
                                    bg=colors[BG], fg=colors[TEXT],
                                    insertbackground=colors[TEXT])
        self.focus_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        tk.Button(entry_row, text="Add", command=self._add_focus_item,
                  bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
                  activeforeground="white", relief="flat", bd=0,
                  font=("Helvetica", 9, "bold"), padx=14, pady=7,
                  cursor="hand2").pack(side="right")
        self.focus_entry.bind("<Return>", lambda _event: self._add_focus_item())

        list_frame = tk.Frame(card, bg=colors[CARD])
        list_frame.pack(fill="both", expand=True, padx=16, pady=12)
        self.focus_listbox = tk.Listbox(
            list_frame, selectmode="extended", relief="flat", bd=0,
            bg=colors[BG], fg=colors[TEXT], selectbackground=colors[ACCENT],
            selectforeground="white", font=("Helvetica", 10),
            highlightthickness=0
        )
        self.focus_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, command=self.focus_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.focus_listbox.configure(yscrollcommand=scrollbar.set)
        for item in self.focus_backend.items:
            self.focus_listbox.insert("end", item)

        tk.Button(card, text="Remove selected", command=self._remove_focus_items,
                  bg=colors[BG], fg=colors[TEXT], activebackground=colors[BG],
                  activeforeground=colors[TEXT], relief="flat", bd=0,
                  font=("Helvetica", 9), padx=10, pady=7,
                  cursor="hand2").pack(anchor="w", padx=16, pady=(0, 14))

        timer_row = tk.Frame(window, bg=colors[BG])
        timer_row.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(timer_row, text="Session length", bg=colors[BG], fg=colors[TEXT],
                 font=("Helvetica", 10, "bold")).pack(side="left")
        self.focus_minutes = tk.StringVar(value="25")
        tk.Spinbox(timer_row, from_=1, to=180, width=5, textvariable=self.focus_minutes,
                   relief="flat", bg=colors[CARD], fg=colors[TEXT],
                   buttonbackground=colors[CARD]).pack(side="right")
        tk.Label(timer_row, text="minutes", bg=colors[BG], fg=colors[MUTED],
                 font=("Helvetica", 9)).pack(side="right", padx=8)

        self.focus_status = tk.Label(window, text="Ready when you are", bg=colors[BG],
                                     fg=colors[MUTED], font=("Helvetica", 10))
        self.focus_status.pack(pady=(0, 8))
        self.focus_button = tk.Button(
            window, text="Start focus session", command=self._toggle_focus_session,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0,
            font=("Helvetica", 11, "bold"), padx=20, pady=11, cursor="hand2"
        )
        self.focus_button.pack(fill="x", padx=24, pady=(0, 20))
        self._focus_after_id = None
        remaining = self.focus_backend.remaining_seconds()
        if self.focus_backend.is_running():
            self.focus_button.configure(text="Pause focus session")
            self._update_focus_countdown()
        elif remaining > 0:
            minutes, seconds = divmod(remaining, 60)
            self.focus_button.configure(text="Resume focus session")
            self.focus_status.configure(
                text="Session paused — {:02d}:{:02d} remaining".format(minutes, seconds)
            )

    def _add_focus_item(self):
        value = self.focus_entry.get().strip()
        if value and self.focus_backend.add_item(value):
            self.focus_listbox.insert("end", value)
        self.focus_entry.delete(0, "end")

    def _remove_focus_items(self):
        selected = list(self.focus_listbox.curselection())
        self.focus_backend.remove_items(selected)
        for index in reversed(selected):
            self.focus_listbox.delete(index)

    def _toggle_focus_session(self):
        if self.focus_backend.is_running():
            self.focus_backend.pause()
            if getattr(self, "_focus_after_id", None) is not None:
                self.focus_window.after_cancel(self._focus_after_id)
                self._focus_after_id = None
            self.focus_status.configure(text="Session paused")
            self.focus_button.configure(text="Resume focus session")
            return

        try:
            minutes = int(self.focus_minutes.get())
            self.focus_backend.start_or_resume(minutes)
        except ValueError:
            self.focus_status.configure(text="Enter a session length from 1 to 180 minutes")
            return
        self.focus_button.configure(text="Pause focus session")
        self._update_focus_countdown()

    def _update_focus_countdown(self):
        remaining = self.focus_backend.remaining_seconds()
        minutes, seconds = divmod(remaining, 60)
        if remaining <= 0:
            self.focus_button.configure(text="Start focus session")
            self.focus_status.configure(text="Session complete — nice work!")
            self._focus_after_id = None
            return
        self.focus_status.configure(
            text="Focus session: {:02d}:{:02d} remaining".format(minutes, seconds)
        )
        self._focus_after_id = self.focus_window.after(1000, self._update_focus_countdown)

    def _close_focus_mode(self):
        if getattr(self, "_focus_after_id", None) is not None:
            self.focus_window.after_cancel(self._focus_after_id)
        self._focus_after_id = None
        self.focus_window.destroy()
        self.focus_window = None

    def _system_uses_dark_theme(self):
        try:
            appearance = subprocess.check_output(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            return appearance.lower() == "dark"
        except (OSError, subprocess.CalledProcessError):
            return False

    def _apply_theme(self):
        dark = self.theme_mode.get() == "Dark" or (
            self.theme_mode.get() == "System" and self._system_uses_dark_theme()
        )
        light_colors = {
            BG: "#F4F6FA", CARD: "#FFFFFF", TEXT: "#202635",
            MUTED: "#7B8495", ACCENT: "#5B6CFF", GREEN: "#31A879",
            "#20283B": "#20283B", "#AAB2C2": "#AAB2C2",
            "#343E56": "#343E56", "#7F899D": "#7F899D",
            "#3A4357": "#3A4357", "#E79742": "#E79742",
            "#EEF0FF": "#EEF0FF", "#E3E6FF": "#E3E6FF",
            "#39A88A": "#39A88A", "#8993A6": "#8993A6",
            "#EEF0F4": "#EEF0F4", "#E8EBF1": "#E8EBF1"
        }
        dark_colors = {
            BG: "#151923", CARD: "#202635", TEXT: "#EDF0F7",
            MUTED: "#A6AFBF", ACCENT: "#8792FF", GREEN: "#55C99A",
            "#20283B": "#111725", "#AAB2C2": "#B8C1D1",
            "#343E56": "#303B55", "#7F899D": "#929DB2",
            "#3A4357": "#39445A", "#E79742": "#F0A957",
            "#EEF0FF": "#30385A", "#E3E6FF": "#3A456A",
            "#39A88A": "#55B99C", "#8993A6": "#A0AABD",
            "#EEF0F4": "#353D4D", "#E8EBF1": "#343C4B"
        }
        self._theme_colors = dark_colors if dark else light_colors
        self._active_theme = "dark" if dark else "light"
        self.configure(bg=self._theme_colors[BG])
        self._recolor_widget(self)
        self._recolor_widget(self.theme_select["menu"])

    def _recolor_widget(self, widget):
        dark_colors = {
            BG: "#151923", CARD: "#202635", TEXT: "#EDF0F7",
            MUTED: "#A6AFBF", ACCENT: "#8792FF", GREEN: "#55C99A",
            "#20283B": "#111725", "#AAB2C2": "#B8C1D1",
            "#343E56": "#303B55", "#7F899D": "#929DB2",
            "#3A4357": "#39445A", "#E79742": "#F0A957",
            "#EEF0FF": "#30385A", "#E3E6FF": "#3A456A",
            "#39A88A": "#55B99C", "#8993A6": "#A0AABD",
            "#EEF0F4": "#353D4D", "#E8EBF1": "#343C4B"
        }
        reverse = {target: source for source, target in dark_colors.items()}
        for option in ("bg", "fg", "activebackground", "activeforeground",
                       "selectcolor", "highlightbackground", "highlightcolor"):
            try:
                current = widget.cget(option)
                base = reverse.get(current, current)
                if base in self._theme_colors:
                    widget.configure(**{option: self._theme_colors[base]})
            except (tk.TclError, TypeError):
                pass
        for child in widget.winfo_children():
            self._recolor_widget(child)

    def _watch_system_theme(self):
        if self.theme_mode.get() == "System":
            current = "dark" if self._system_uses_dark_theme() else "light"
            if current != self._active_theme:
                self._apply_theme()
        self.after(2000, self._watch_system_theme)

    def _stat_card(self, parent, title, value, subtitle, color):
        card = tk.Frame(parent, bg=CARD, highlightbackground="#E8EBF1", highlightthickness=1)
        card.pack(side="left", fill="x", expand=True, padx=(0, 12))
        tk.Frame(card, bg=color, height=3).pack(fill="x")
        tk.Label(card, text=title, bg=CARD, fg=MUTED,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=17, pady=(14, 5))
        value_label = tk.Label(card, text=value, bg=CARD, fg=TEXT,
                               font=("Helvetica", 21, "bold"))
        value_label.pack(anchor="w", padx=17)
        subtitle_label = tk.Label(card, text=subtitle, bg=CARD, fg=MUTED,
                                  font=("Helvetica", 9))
        subtitle_label.pack(anchor="w", padx=17, pady=(4, 15))
        if title == "TASKS DONE":
            self.tasks_done_value = value_label
            self.tasks_done_subtitle = subtitle_label

    def _panel(self, parent, title, detail):
        panel = tk.Frame(parent, bg=CARD, highlightbackground="#E8EBF1", highlightthickness=1)
        top = tk.Frame(panel, bg=CARD)
        top.pack(fill="x", padx=20, pady=(18, 8))
        tk.Label(top, text=title, bg=CARD, fg=TEXT,
                 font=("Helvetica", 14, "bold")).pack(side="left")
        detail_label = tk.Label(top, text=detail, bg=CARD, fg=MUTED,
                                font=("Helvetica", 9))
        detail_label.pack(side="right")
        if title == "Today's tasks":
            self.tasks_remaining_label = detail_label
        return panel

    def _task_row(self, parent, title, due, completed):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=20, pady=8)
        checked = tk.BooleanVar(value=completed)
        label = tk.Label(row, text=title, bg=CARD, fg=MUTED if completed else TEXT,
                         font=("Helvetica", 10, "overstrike" if completed else "normal"))
        task = {"checked": checked, "label": label}
        check = tk.Checkbutton(
            row, variable=checked, command=lambda item=task: self._toggle_task(item),
            bg=CARD, activebackground=CARD, selectcolor=CARD,
            bd=0, highlightthickness=0
        )
        check.pack(side="left")
        label.pack(side="left", padx=5)
        tk.Label(row, text=due, bg=CARD, fg=MUTED,
                 font=("Helvetica", 9)).pack(side="right")
        self.task_items.append(task)
        self._update_task_summary()

    def _toggle_task(self, task):
        completed = task["checked"].get()
        task["label"].configure(
            fg=self._theme_colors.get(MUTED if completed else TEXT,
                                     MUTED if completed else TEXT),
            font=("Helvetica", 10, "overstrike" if completed else "normal")
        )
        self._update_task_summary()

    def _update_task_summary(self):
        total = len(self.task_items)
        completed = sum(1 for task in self.task_items if task["checked"].get())
        remaining = total - completed
        self.tasks_done_value.configure(text="{} of {}".format(completed, total))
        self.tasks_done_subtitle.configure(
            text="{} task{} remaining".format(remaining, "s" if remaining != 1 else "")
        )
        self.tasks_remaining_label.configure(
            text="{} remaining".format(remaining)
        )

    def _usage_row(self, parent, name, duration, amount, color):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=20, pady=(12, 0))
        line = tk.Frame(row, bg=CARD)
        line.pack(fill="x")
        tk.Label(line, text=name, bg=CARD, fg=TEXT,
                 font=("Helvetica", 10)).pack(side="left")
        tk.Label(line, text=duration, bg=CARD, fg=MUTED,
                 font=("Helvetica", 9)).pack(side="right")
        bar = tk.Frame(row, bg="#EEF0F4", height=7)
        bar.pack(fill="x", pady=(8, 0))
        bar.pack_propagate(False)
        tk.Frame(bar, bg=color, width=int(240 * amount)).pack(side="left", fill="y")

    def _add_task(self):
        # This prototype keeps tasks in the window only; persistence can be added later.
        from tkinter import simpledialog
        title = simpledialog.askstring("Add a task", "Task name:", parent=self)
        if title and title.strip():
            self._task_row(self.task_list, title.strip(), "", False)
            self._apply_theme()


if __name__ == "__main__":
    Dashboard().mainloop()
