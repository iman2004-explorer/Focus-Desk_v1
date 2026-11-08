import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk
from datetime import date, datetime, timedelta
import subprocess
import time

from focus_backend import FocusBackend
from productivity_model import rate_productivity


BG = "#F5F7FB"
CARD = "#FFFFFF"
TEXT = "#20243A"
MUTED = "#778097"
ACCENT = "#5F63F2"
GREEN = "#219A78"

THEME_COLOR_PAIRS = (
    (BG, "#111827"),
    (CARD, "#1B2434"),
    (TEXT, "#F0F3FA"),
    (MUTED, "#9AA7BA"),
    (ACCENT, "#9290FF"),
    (GREEN, "#5DD4A7"),
    ("#1D2440", "#0D1423"),
    ("#B8C0D4", "#AAB6CA"),
    ("#303B61", "#263451"),
    ("#8791AB", "#8593AD"),
    ("#414B67", "#303B52"),
    ("#D88936", "#ECA85B"),
    ("#EEF0FF", "#292C4A"),
    ("#E1E4FF", "#34385E"),
    ("#258A73", "#45B89B"),
    ("#8993A6", "#A0ADC1"),
    ("#EEF1F7", "#2B3547"),
    ("#E6EAF2", "#303B4C"),
)

THEME_COLOR_ALIASES = {
    "#20283B": "#1D2440",
    "#AAB2C2": "#B8C0D4",
    "#343E56": "#303B61",
    "#7F899D": "#8791AB",
    "#3A4357": "#414B67",
    "#E79742": "#D88936",
    "#E3E6FF": "#E1E4FF",
    "#39A88A": "#258A73",
    "#EEF0F4": "#EEF1F7",
    "#E8EBF1": "#E6EAF2",
}


class Dashboard(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Focus Desk")
        self.geometry("1180x800")
        self.minsize(900, 640)
        self.configure(bg=BG)
        self.theme_mode = tk.StringVar(value="System")
        self._active_theme = None
        self._theme_colors = {}
        self.nav_rows = {}
        self.task_items = []
        self.focus_backend = FocusBackend()
        self.profile_window = None
        self._scroll_task_after_id = None
        self.alarms = [
            {
                "id": alarm["id"],
                "time": datetime.fromtimestamp(alarm["timestamp"]),
                "label": alarm["label"],
            }
            for alarm in self.focus_backend.alarms
        ]
        self.timer_remaining = 0
        self.timer_deadline = None
        self.stopwatch_elapsed = 0.0
        self.stopwatch_started_at = None
        self.clock_window = None
        self._clock_after_id = None

        self._build_sidebar()
        self._build_content()
        self.bind("<Destroy>", self._cancel_pending_task_scroll, add="+")
        self._select_section("Dashboard")
        self._apply_theme()
        self._watch_system_theme()
        self._check_alarms()

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg="#20283B", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg="#20283B")
        brand.pack(fill="x", padx=20, pady=(25, 38))
        tk.Label(
            brand, text="F", bg=ACCENT, fg="white", width=2, height=1,
            font=("Helvetica", 15, "bold")
        ).pack(side="left", padx=(0, 10), ipady=4)
        brand_text = tk.Frame(brand, bg="#20283B")
        brand_text.pack(side="left")
        tk.Label(
            brand_text, text="FOCUS", bg="#20283B", fg="white",
            font=("Helvetica", 15, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand_text, text="DESK", bg="#20283B", fg="#AAB2C2",
            font=("Helvetica", 8, "bold")
        ).pack(anchor="w", pady=(1, 0))

        items = [("▦", "Dashboard"), ("✓", "Tasks"),
                 ("◷", "App time"), ("◉", "Focus mode"), ("◷", "Clock tools"),
                 ("◈", "Productivity"), ("▤", "Reports")]
        for icon, label in items:
            row = tk.Frame(sidebar, bg="#20283B", cursor="hand2")
            row.pack(fill="x", padx=12, pady=3, ipady=2)
            indicator = tk.Frame(row, bg="#20283B", width=3)
            indicator.pack(side="left", fill="y", padx=(0, 5))
            icon_label = tk.Label(row, text=icon, bg="#20283B", fg="#AAB2C2",
                                  font=("Helvetica", 13), width=3)
            icon_label.pack(side="left", padx=(7, 0), pady=11)
            text_label = tk.Label(row, text=label, bg="#20283B", fg="#AAB2C2",
                                  font=("Helvetica", 11))
            text_label.pack(side="left")
            self.nav_rows[label] = (row, indicator, icon_label, text_label)
            for widget in (row, indicator, icon_label, text_label):
                widget.bind("<Button-1>", lambda _event, section=label: self._select_section(section))

        tk.Frame(sidebar, bg="#3A4357", height=1).pack(fill="x", padx=20, pady=(30, 18))
        tk.Label(sidebar, text="WORKSPACE", bg="#20283B", fg="#7F899D",
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=22, pady=(0, 12))
        tk.Label(sidebar, text="⚙  Preferences", bg="#20283B", fg="#AAB2C2",
                 font=("Helvetica", 10)).pack(anchor="w", padx=25, pady=8)

        profile_card = tk.Frame(sidebar, bg="#303B61", cursor="hand2")
        profile_card.pack(side="bottom", fill="x", padx=12, pady=16)
        profile_card.bind("<Button-1>", lambda _event: self._open_profile())
        self.profile_avatar = tk.Label(
            profile_card, text="?", bg=ACCENT, fg="white", width=2,
            font=("Helvetica", 11, "bold"), cursor="hand2"
        )
        self.profile_avatar.pack(side="left", padx=(10, 9), pady=10, ipady=3)
        profile_text = tk.Frame(profile_card, bg="#303B61", cursor="hand2")
        profile_text.pack(side="left", fill="x", expand=True, pady=8)
        self.profile_name_label = tk.Label(
            profile_text, text="Your profile", bg="#303B61", fg="white",
            font=("Helvetica", 10, "bold"), anchor="w", cursor="hand2"
        )
        self.profile_name_label.pack(fill="x")
        self.profile_bio_label = tk.Label(
            profile_text, text="Add your name and bio", bg="#303B61",
            fg="#B8C0D4", font=("Helvetica", 8), anchor="w",
            cursor="hand2"
        )
        self.profile_bio_label.pack(fill="x", pady=(2, 0))
        for widget in (self.profile_avatar, profile_text,
                       self.profile_name_label, self.profile_bio_label):
            widget.bind("<Button-1>", lambda _event: self._open_profile())
        self._refresh_profile_card()

    def _build_content(self):
        content = tk.Frame(self, bg=BG)
        content.pack(side="left", fill="both", expand=True, padx=38, pady=32)

        header = tk.Frame(content, bg=BG)
        header.pack(fill="x", pady=(0, 28))
        heading = tk.Frame(header, bg=BG)
        heading.pack(side="left", fill="x", expand=True)
        self.page_title = tk.Label(heading, text=self._greeting(), bg=BG, fg=TEXT,
                                   font=("Helvetica", 30, "bold"))
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(
            heading, text="Here’s your productivity overview for today.",
            bg=BG, fg=MUTED, font=("Helvetica", 11)
        )
        self.page_subtitle.pack(anchor="w", pady=(5, 0))
        controls = tk.Frame(header, bg=BG)
        controls.pack(side="right", anchor="n", padx=(14, 0), pady=(4, 0))
        date_badge = tk.Label(
            controls, text=date.today().strftime("%a, %b %d"), bg=CARD, fg=TEXT,
            font=("Helvetica", 10, "bold"), padx=13, pady=9,
            highlightbackground="#E8EBF1", highlightthickness=1
        )
        date_badge.pack(side="left", padx=(0, 9))
        theme_select = ttk.Combobox(
            controls, textvariable=self.theme_mode, values=("System", "Light", "Dark"),
            state="readonly", width=9, style="Theme.TCombobox"
        )
        theme_select.bind("<<ComboboxSelected>>", self._on_theme_change)
        theme_select.pack(side="left")
        self.theme_select = theme_select

        stats = tk.Frame(content, bg=BG)
        stats.pack(fill="x", pady=(0, 24))
        focus_minutes = self._today_focus_minutes()
        stored_tasks = self.focus_backend.tasks
        completed_tasks = sum(task["completed"] for task in stored_tasks)
        remaining_tasks = len(stored_tasks) - completed_tasks
        self._stat_card(
            stats, "FOCUS TIME", self._format_minutes(focus_minutes),
            "Completed study time today", ACCENT
        )
        self._stat_card(
            stats, "TASKS DONE",
            "{} of {}".format(completed_tasks, len(stored_tasks)),
            "{} task{} remaining".format(
                remaining_tasks, "s" if remaining_tasks != 1 else ""
            ),
            GREEN
        )
        self._stat_card(stats, "DAILY GOAL", "{} min".format(
            self.focus_backend.daily_goal_minutes
        ), "Completed focus target", "#E79742")

        panels = tk.Frame(content, bg=BG)
        panels.pack(fill="both", expand=True)
        panels.grid_columnconfigure(0, weight=3, uniform="panel")
        panels.grid_columnconfigure(1, weight=2, uniform="panel")
        panels.grid_rowconfigure(0, weight=1)

        tasks = self._panel(
            panels, "Today's tasks",
            "{} remaining".format(remaining_tasks)
        )
        tasks.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        task_container = tk.Frame(tasks, bg=CARD)
        task_container.pack(fill="both", expand=True)
        self.task_canvas = tk.Canvas(
            task_container, bg=CARD, highlightthickness=0, bd=0
        )
        self.task_canvas.pack(side="left", fill="both", expand=True)
        task_scrollbar = tk.Scrollbar(
            task_container, orient="vertical", command=self.task_canvas.yview
        )
        task_scrollbar.pack(side="right", fill="y")
        self.task_canvas.configure(yscrollcommand=task_scrollbar.set)
        self.task_list = tk.Frame(self.task_canvas, bg=CARD)
        self._task_list_window = self.task_canvas.create_window(
            (0, 0), window=self.task_list, anchor="nw"
        )
        self.task_list.bind("<Configure>", self._on_task_list_configure)
        self.task_canvas.bind(
            "<Configure>",
            lambda event: self.task_canvas.itemconfigure(
                self._task_list_window, width=event.width
            ),
        )
        for task in stored_tasks:
            self._task_row(
                self.task_list, task["title"], "", task["completed"],
                task_id=task["id"]
            )
        tk.Button(tasks, text="+  Add a task", command=self._add_task,
                  bg="#EEF0FF", fg=ACCENT, activebackground="#E3E6FF",
                  activeforeground=ACCENT, relief="flat", bd=0,
                  font=("Helvetica", 10, "bold"), padx=12, pady=9,
                  cursor="hand2").pack(anchor="w", padx=20, pady=(12, 18))

        usage = self._panel(panels, "App time", "Today")
        usage.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        tk.Label(
            usage,
            text="App usage tracking is not enabled. Focus Desk currently records only completed focus sessions.",
            bg=CARD, fg=MUTED, font=("Helvetica", 10),
            wraplength=300, justify="left"
        ).pack(anchor="w", padx=20, pady=(24, 18))

    def _select_section(self, section):
        pages = {
            "Dashboard": (self._greeting(), "Here’s your productivity overview for today."),
            "Tasks": ("Your tasks", "Check off a task or add something new to your list."),
            "App time": ("App time", "A colorful snapshot of where your time went today."),
            "Focus mode": ("Focus mode", "Set distractions aside and protect your focus time."),
            "Clock tools": ("Clock tools", "Set alarms, run a stopwatch, or start a timer."),
            "Productivity": ("Productivity", "See your completed study time and daily goal."),
            "Reports": ("Your reports", "Review today’s focus and activity at a glance.")
        }
        if section == "Focus mode":
            self._open_focus_mode()
        elif section == "Clock tools":
            self._open_clock_tools()
        elif section == "Productivity":
            self._open_productivity()
        elif section == "Reports":
            self._open_reports()
        elif section == "App time":
            messagebox.showinfo(
                "App time tracking",
                "Focus Desk does not currently collect app usage. It tracks completed focus sessions only.",
                parent=self,
            )
        self.page_title.config(text=pages[section][0])
        self.page_subtitle.config(text=pages[section][1])
        dark = self._active_theme == "dark"
        active_bg = "#263451" if dark else "#303B61"
        sidebar_bg = "#0D1423" if dark else "#1D2440"
        inactive_fg = "#AAB6CA" if dark else "#B8C0D4"
        for label, widgets in self.nav_rows.items():
            active = label == section
            row, indicator, icon_label, text_label = widgets
            row_color = active_bg if active else sidebar_bg
            foreground = "#FFFFFF" if active else inactive_fg
            row.configure(bg=row_color)
            indicator.configure(
                bg=self._theme_colors.get(ACCENT, ACCENT) if active else row_color
            )
            icon_label.configure(bg=row_color, fg=foreground)
            text_label.configure(bg=row_color, fg=foreground,
                                 font=("Helvetica", 11, "bold" if active else "normal"))

    def _greeting(self):
        hour = datetime.now().hour
        if hour < 12:
            return "Good morning"
        if hour < 17:
            return "Good afternoon"
        return "Good evening"

    def _on_theme_change(self, _selected=None):
        self._apply_theme()

    def _open_profile(self):
        if self.profile_window is not None and self.profile_window.winfo_exists():
            self.profile_window.lift()
            return

        colors = self._theme_colors
        profile = self.focus_backend.profile
        window = tk.Toplevel(self)
        self.profile_window = window
        window.title("Your profile")
        window.geometry("460x400")
        window.minsize(420, 360)
        window.configure(bg=colors[BG])
        window.protocol("WM_DELETE_WINDOW", self._close_profile)

        heading = tk.Frame(window, bg=colors[BG])
        heading.pack(fill="x", padx=26, pady=(24, 18))
        tk.Label(
            heading, text="YOUR SPACE", bg=colors[BG], fg=colors[ACCENT],
            font=("Helvetica", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            heading, text="Profile", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 24, "bold")
        ).pack(anchor="w", pady=(3, 2))
        tk.Label(
            heading, text="Add your name and share something interesting about yourself.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w")

        card = self._clock_card(window, colors)
        card.pack(fill="x", padx=22, pady=(0, 14))
        tk.Label(
            card, text="NAME", bg=colors[CARD], fg=colors[MUTED],
            font=("Helvetica", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(14, 5))
        self.profile_name_entry = tk.Entry(
            card, relief="flat", bd=0, bg=colors[BG], fg=colors[TEXT],
            insertbackground=colors[TEXT], font=("Helvetica", 11)
        )
        self.profile_name_entry.pack(fill="x", padx=16, ipady=9)
        self.profile_name_entry.insert(0, profile["name"])
        tk.Label(
            card, text="SOMETHING INTERESTING ABOUT YOU", bg=colors[CARD], fg=colors[MUTED],
            font=("Helvetica", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(14, 5))
        self.profile_bio_entry = tk.Entry(
            card, relief="flat", bd=0, bg=colors[BG], fg=colors[TEXT],
            insertbackground=colors[TEXT], font=("Helvetica", 11)
        )
        self.profile_bio_entry.pack(fill="x", padx=16, ipady=9, pady=(0, 16))
        self.profile_bio_entry.insert(0, profile["bio"])

        self.profile_status = tk.Label(
            window, text="Your profile is saved on this device.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 9)
        )
        self.profile_status.pack(anchor="w", padx=26, pady=(0, 8))
        actions = tk.Frame(window, bg=colors[BG])
        actions.pack(fill="x", padx=22, pady=(0, 20))
        tk.Button(
            actions, text="Cancel", command=self._close_profile,
            bg=colors[CARD], fg=colors[TEXT], relief="flat", bd=0,
            padx=17, pady=10, cursor="hand2"
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            actions, text="Save profile", command=self._save_profile,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0,
            font=("Helvetica", 10, "bold"), padx=18, pady=10,
            cursor="hand2"
        ).pack(side="right")

    def _save_profile(self):
        try:
            self.focus_backend.set_profile(
                self.profile_name_entry.get(),
                self.profile_bio_entry.get(),
            )
        except ValueError as error:
            self.profile_status.configure(text=str(error))
            return
        self._refresh_profile_card()
        self._close_profile()

    def _refresh_profile_card(self):
        profile = self.focus_backend.profile
        name = profile["name"] or "Your profile"
        bio = profile["bio"] or "Add your name and bio"
        initials = "".join(part[0] for part in profile["name"].split()[:2]).upper()
        self.profile_avatar.configure(text=initials or "?")
        self.profile_name_label.configure(text=name)
        self.profile_bio_label.configure(text=bio)

    def _close_profile(self):
        if self.profile_window is not None and self.profile_window.winfo_exists():
            self.profile_window.destroy()
        self.profile_window = None

    def _open_productivity(self):
        if (
            getattr(self, "productivity_window", None) is not None
            and self.productivity_window.winfo_exists()
        ):
            self.productivity_window.lift()
            self._refresh_productivity()
            return

        colors = self._theme_colors
        window = tk.Toplevel(self)
        self.productivity_window = window
        window.title("Productivity rating")
        window.geometry("520x570")
        window.minsize(460, 520)
        window.configure(bg=colors[BG])

        heading = tk.Frame(window, bg=colors[BG])
        heading.pack(fill="x", padx=28, pady=(24, 16))
        tk.Label(
            heading, text="YOUR STUDY PROGRESS", bg=colors[BG],
            fg=colors[ACCENT], font=("Helvetica", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            heading, text="Productivity rating", bg=colors[BG],
            fg=colors[TEXT], font=("Helvetica", 24, "bold")
        ).pack(anchor="w", pady=(3, 2))
        tk.Label(
            heading,
            text="A simple score from focus sessions you complete today.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w")

        score_card = self._clock_card(window, colors)
        score_card.pack(fill="x", padx=24, pady=(0, 14))
        self.productivity_score = tk.Label(
            score_card, text="0", bg=colors[CARD], fg=colors[ACCENT],
            font=("Helvetica", 52, "bold")
        )
        self.productivity_score.pack(pady=(15, 0))
        tk.Label(
            score_card, text="OUT OF 100", bg=colors[CARD],
            fg=colors[MUTED], font=("Helvetica", 9, "bold")
        ).pack()
        self.productivity_rating = tk.Label(
            score_card, text="", bg=colors[CARD], fg=colors[TEXT],
            font=("Helvetica", 15, "bold")
        )
        self.productivity_rating.pack(pady=(12, 2))
        self.productivity_message = tk.Label(
            score_card, text="", bg=colors[CARD], fg=colors[MUTED],
            font=("Helvetica", 10)
        )
        self.productivity_message.pack(pady=(0, 15))
        tk.Label(
            score_card,
            text="Score = completed focus minutes ÷ daily goal. Paused or unfinished sessions do not count.",
            bg=colors[CARD], fg=colors[MUTED], font=("Helvetica", 9),
            wraplength=420, justify="center"
        ).pack(padx=18, pady=(0, 15))

        detail_card = self._clock_card(window, colors)
        detail_card.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(
            detail_card, text="TODAY'S FOCUS", bg=colors[CARD],
            fg=colors[MUTED], font=("Helvetica", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(14, 4))
        self.productivity_minutes = tk.Label(
            detail_card, text="", bg=colors[CARD], fg=colors[TEXT],
            font=("Helvetica", 16, "bold")
        )
        self.productivity_minutes.pack(anchor="w", padx=16)
        self.productivity_progress = ttk.Progressbar(
            detail_card, maximum=100, style="Productivity.Horizontal.TProgressbar"
        )
        self.productivity_progress.pack(fill="x", padx=16, pady=(10, 15))

        goal_row = tk.Frame(window, bg=colors[BG])
        goal_row.pack(fill="x", padx=28, pady=(0, 8))
        tk.Label(
            goal_row, text="Daily study goal", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 10, "bold")
        ).pack(side="left")
        self.productivity_goal = tk.StringVar(
            value=str(self.focus_backend.daily_goal_minutes)
        )
        tk.Spinbox(
            goal_row, from_=1, to=600, width=6,
            textvariable=self.productivity_goal, justify="center",
            relief="flat", bg=colors[CARD], fg=colors[TEXT],
            buttonbackground=colors[CARD], font=("Helvetica", 10)
        ).pack(side="right", padx=(8, 0), ipady=5)
        tk.Label(
            goal_row, text="minutes", bg=colors[BG], fg=colors[MUTED],
            font=("Helvetica", 9)
        ).pack(side="right")
        self.productivity_status = tk.Label(
            window, text="", bg=colors[BG], fg=colors[MUTED],
            font=("Helvetica", 9)
        )
        self.productivity_status.pack(anchor="w", padx=28, pady=(0, 8))
        tk.Button(
            window, text="Save daily goal", command=self._save_productivity_goal,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0,
            font=("Helvetica", 10, "bold"), padx=18, pady=10,
            cursor="hand2"
        ).pack(fill="x", padx=24, pady=(0, 20))
        self._refresh_productivity()

    def _open_reports(self):
        if (
            getattr(self, "reports_window", None) is not None
            and self.reports_window.winfo_exists()
        ):
            self.reports_window.lift()
            self._refresh_reports()
            return

        colors = self._theme_colors
        window = tk.Toplevel(self)
        self.reports_window = window
        window.title("Study reports")
        window.geometry("560x700")
        window.minsize(480, 610)
        window.configure(bg=colors[BG])

        heading = tk.Frame(window, bg=colors[BG])
        heading.pack(fill="x", padx=26, pady=(22, 16))
        tk.Label(
            heading, text="YOUR ACTUAL STUDY DATA", bg=colors[BG],
            fg=colors[ACCENT], font=("Helvetica", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            heading, text="Study reports", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 24, "bold")
        ).pack(anchor="w", pady=(3, 2))
        tk.Label(
            heading, text="Based on completed focus sessions and your task list.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w")

        summary = self._clock_card(window, colors)
        summary.pack(fill="x", padx=22, pady=(0, 14))
        self.report_focus = tk.Label(
            summary, text="", bg=colors[CARD], fg=colors[TEXT],
            font=("Helvetica", 15, "bold")
        )
        self.report_focus.pack(anchor="w", padx=16, pady=(14, 6))
        self.report_rating = tk.Label(
            summary, text="", bg=colors[CARD], fg=colors[ACCENT],
            font=("Helvetica", 11, "bold")
        )
        self.report_rating.pack(anchor="w", padx=16, pady=(0, 5))
        self.report_tasks = tk.Label(
            summary, text="", bg=colors[CARD], fg=colors[MUTED],
            font=("Helvetica", 10)
        )
        self.report_tasks.pack(anchor="w", padx=16, pady=(0, 14))

        history_card = self._clock_card(window, colors)
        history_card.pack(fill="both", expand=True, padx=22, pady=(0, 20))
        chart_heading = tk.Frame(history_card, bg=colors[CARD])
        chart_heading.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(
            chart_heading, text="FOCUS ACROSS THE DAY", bg=colors[CARD],
            fg=colors[MUTED], font=("Helvetica", 9, "bold")
        ).pack(side="left")
        self.report_peak = tk.Label(
            chart_heading, text="", bg=colors[CARD], fg=colors[GREEN],
            font=("Helvetica", 9, "bold")
        )
        self.report_peak.pack(side="right")
        self.report_hourly_minutes = [0] * 24
        self.report_chart = tk.Canvas(
            history_card, height=132, bg=colors[CARD], highlightthickness=0
        )
        self.report_chart.pack(fill="x", padx=14, pady=(0, 10))
        self.report_chart.bind(
            "<Configure>", lambda _event: self._draw_report_chart()
        )
        tk.Label(
            history_card, text="TODAY'S COMPLETED SESSIONS", bg=colors[CARD],
            fg=colors[MUTED], font=("Helvetica", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(0, 8))
        self.report_sessions = tk.Listbox(
            history_card, relief="flat", bd=0, bg=colors[BG], fg=colors[TEXT],
            highlightthickness=0, activestyle="none", font=("Helvetica", 10)
        )
        self.report_sessions.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._refresh_reports()

    def _refresh_reports(self):
        if (
            getattr(self, "reports_window", None) is None
            or not self.reports_window.winfo_exists()
        ):
            return
        focus_minutes = self._today_focus_minutes()
        rating = rate_productivity(
            focus_minutes, self.focus_backend.daily_goal_minutes
        )
        tasks = self.focus_backend.tasks
        completed = sum(task["completed"] for task in tasks)
        self.report_focus.configure(
            text="{} focused today".format(self._format_minutes(focus_minutes))
        )
        self.report_rating.configure(
            text="{} — {}% of daily goal".format(
                rating["rating"], rating["score"]
            )
        )
        self.report_tasks.configure(
            text="{} of {} tasks complete".format(completed, len(tasks))
        )
        start, end = self._today_epoch_range()
        sessions = [
            session for session in self.focus_backend.completed_sessions
            if start <= session["completed_at"] < end
        ]
        hourly_minutes = [0] * 24
        for session in sessions:
            session_end = session["completed_at"]
            cursor = max(
                start,
                session_end - max(0, session["duration_seconds"]),
            )
            while cursor < session_end:
                hour_start = datetime.fromtimestamp(cursor)
                next_hour = hour_start.replace(
                    minute=0, second=0, microsecond=0
                ) + timedelta(hours=1)
                segment_end = min(session_end, next_hour.timestamp())
                hourly_minutes[hour_start.hour] += (segment_end - cursor) / 60
                cursor = segment_end
        self.report_hourly_minutes = hourly_minutes
        peak_minutes = max(hourly_minutes)
        if peak_minutes:
            peak_hour = hourly_minutes.index(peak_minutes)
            peak_start = datetime(2020, 1, 1, peak_hour).strftime("%I %p").lstrip("0")
            peak_end = datetime(2020, 1, 1, peak_hour + 1).strftime("%I %p").lstrip("0")
            self.report_peak.configure(
                text="Most focused: {}–{} · {} min".format(
                    peak_start, peak_end, round(peak_minutes)
                )
            )
        else:
            self.report_peak.configure(text="No sessions yet")
        self._draw_report_chart()
        sessions.sort(key=lambda session: session["completed_at"], reverse=True)
        self.report_sessions.delete(0, "end")
        if not sessions:
            self.report_sessions.insert("end", "No completed focus sessions today yet.")
        for session in sessions:
            completed_at = datetime.fromtimestamp(session["completed_at"])
            duration = self._format_minutes(session["duration_seconds"] // 60)
            self.report_sessions.insert(
                "end", "{}  ·  {}".format(completed_at.strftime("%I:%M %p"), duration)
            )

    def _draw_report_chart(self):
        canvas = getattr(self, "report_chart", None)
        if canvas is None or not canvas.winfo_exists():
            return
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1:
            return

        colors = self._theme_colors
        canvas.delete("all")
        left, right, top, bottom = 5, 5, 8, 24
        plot_width = width - left - right
        plot_height = height - top - bottom
        baseline = top + plot_height
        peak_minutes = max(self.report_hourly_minutes, default=0)
        for fraction in (0.25, 0.5, 0.75):
            y = top + plot_height * (1 - fraction)
            canvas.create_line(left, y, width - right, y, fill=colors[BG])
        canvas.create_line(left, baseline, width - right, baseline, fill=colors[MUTED])

        column_width = plot_width / 24
        bar_width = min(12, max(4, column_width * 0.58))
        for hour, minutes in enumerate(self.report_hourly_minutes):
            x = left + column_width * (hour + 0.5)
            bar_height = plot_height * minutes / peak_minutes if peak_minutes else 0
            if bar_height:
                color = colors[GREEN] if minutes == peak_minutes else colors[ACCENT]
                canvas.create_rectangle(
                    x - bar_width / 2, baseline - bar_height,
                    x + bar_width / 2, baseline, fill=color, outline=""
                )
            if hour % 3 == 0:
                label = datetime(2020, 1, 1, hour).strftime("%I %p").lstrip("0")
                canvas.create_text(
                    x, height - 10, text=label, fill=colors[MUTED],
                    font=("Helvetica", 7)
                )

    def _today_epoch_range(self):
        now = datetime.now().astimezone()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        end = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()
        return start, end

    def _today_focus_minutes(self):
        start, end = self._today_epoch_range()
        return self.focus_backend.completed_focus_minutes(start, end)

    def _refresh_productivity(self):
        self._refresh_focus_summary()
        self._refresh_reports()
        if (
            getattr(self, "productivity_window", None) is None
            or not self.productivity_window.winfo_exists()
        ):
            return
        focus_minutes = self._today_focus_minutes()
        goal_minutes = self.focus_backend.daily_goal_minutes
        rating = rate_productivity(focus_minutes, goal_minutes)
        self.productivity_score.configure(text=str(rating["score"]))
        self.productivity_rating.configure(text=rating["rating"])
        self.productivity_message.configure(text=rating["message"])
        self.productivity_minutes.configure(
            text="{} of {} min".format(focus_minutes, goal_minutes)
        )
        self.productivity_progress.configure(value=rating["score"])
        self.productivity_goal.set(str(goal_minutes))

    def _format_minutes(self, minutes):
        hours, remainder = divmod(minutes, 60)
        if hours:
            return "{}h {}m".format(hours, remainder)
        return "{}m".format(remainder)

    def _refresh_focus_summary(self):
        if hasattr(self, "focus_time_value"):
            self.focus_time_value.configure(
                text=self._format_minutes(self._today_focus_minutes())
            )
            self.focus_time_subtitle.configure(text="Completed study time today")
        if hasattr(self, "daily_goal_value"):
            self.daily_goal_value.configure(
                text="{} min".format(self.focus_backend.daily_goal_minutes)
            )

    def _save_productivity_goal(self):
        try:
            goal_minutes = int(self.productivity_goal.get())
            self.focus_backend.set_daily_goal(goal_minutes)
        except ValueError:
            self.productivity_status.configure(
                text="Enter a daily goal between 1 and 600 minutes."
            )
            return
        self.productivity_status.configure(text="Daily goal saved.")
        self._refresh_productivity()

    def _open_clock_tools(self):
        if getattr(self, "clock_window", None) is not None and self.clock_window.winfo_exists():
            self.clock_window.lift()
            return

        colors = self._theme_colors
        window = tk.Toplevel(self)
        self.clock_window = window
        window.title("Clock tools")
        window.geometry("640x700")
        window.minsize(540, 620)
        window.configure(bg=colors[BG])
        window.protocol("WM_DELETE_WINDOW", self._close_clock_tools)

        heading = tk.Frame(window, bg=colors[BG])
        heading.pack(fill="x", padx=28, pady=(24, 18))
        tk.Label(
            heading, text="TIME YOUR WAY", bg=colors[BG], fg=colors[ACCENT],
            font=("Helvetica", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            heading, text="Clock tools", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 25, "bold")
        ).pack(anchor="w", pady=(3, 2))
        tk.Label(
            heading, text="Alarms, laps, and countdowns — all in one place.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w")

        tabs = ttk.Notebook(window)
        tabs.pack(fill="both", expand=True, padx=22, pady=(0, 22))

        alarm_tab = tk.Frame(tabs, bg=colors[BG])
        stopwatch_tab = tk.Frame(tabs, bg=colors[BG])
        timer_tab = tk.Frame(tabs, bg=colors[BG])
        tabs.add(alarm_tab, text="Alarm")
        tabs.add(stopwatch_tab, text="Stopwatch")
        tabs.add(timer_tab, text="Timer")
        self._build_alarm_tab(alarm_tab, colors)
        self._build_stopwatch_tab(stopwatch_tab, colors)
        self._build_timer_tab(timer_tab, colors)
        self._refresh_alarm_list()
        self._schedule_clock_update()

    def _build_alarm_tab(self, parent, colors):
        tk.Label(
            parent, text="Never miss your moment", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 17, "bold")
        ).pack(anchor="w", padx=20, pady=(22, 3))
        tk.Label(
            parent, text="Set a one-time alarm using 24-hour time.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w", padx=20, pady=(0, 16))
        card = self._clock_card(parent, colors)
        card.pack(fill="x", padx=18, pady=(0, 12))
        tk.Label(card, text="NEW ALARM", bg=colors[CARD], fg=colors[MUTED],
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        controls = tk.Frame(card, bg=colors[CARD])
        controls.pack(fill="x", padx=16, pady=(0, 15))
        self.alarm_time_entry = tk.Entry(
            controls, width=7, justify="center", font=("Helvetica", 16, "bold"),
            relief="flat", bg=colors[BG], fg=colors[TEXT],
            insertbackground=colors[TEXT]
        )
        self.alarm_time_entry.insert(0, datetime.now().strftime("%H:%M"))
        self.alarm_time_entry.pack(side="left", ipady=8)
        self.alarm_label_entry = tk.Entry(
            controls, font=("Helvetica", 11), relief="flat",
            bg=colors[BG], fg=colors[TEXT], insertbackground=colors[TEXT]
        )
        self.alarm_label_entry.insert(0, "Name this alarm")
        self.alarm_label_entry.pack(side="left", fill="x", expand=True,
                                    padx=9, ipady=10)
        tk.Button(
            controls, text="＋  Set alarm", command=self._add_alarm,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0, padx=13, pady=9,
            font=("Helvetica", 10, "bold"),
            cursor="hand2"
        ).pack(side="right")
        self.alarm_status = tk.Label(
            parent, text="Alarms ring once while Focus Desk is running.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 9)
        )
        self.alarm_status.pack(anchor="w", padx=21, pady=(0, 8))
        list_card = self._clock_card(parent, colors)
        list_card.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        list_header = tk.Frame(list_card, bg=colors[CARD])
        list_header.pack(fill="x", padx=15, pady=(12, 8))
        tk.Label(list_header, text="UPCOMING", bg=colors[CARD], fg=colors[TEXT],
                 font=("Helvetica", 9, "bold")).pack(side="left")
        tk.Button(
            list_header, text="Remove selected", command=self._delete_alarm,
            bg=colors[CARD], fg=colors[MUTED], activebackground=colors[CARD],
            activeforeground=colors[TEXT], relief="flat", bd=0,
            font=("Helvetica", 9), cursor="hand2"
        ).pack(side="right")
        self.alarm_listbox = tk.Listbox(
            list_card, relief="flat", bd=0, bg=colors[BG], fg=colors[TEXT],
            selectbackground=colors[ACCENT], selectforeground="white",
            highlightthickness=0, font=("Helvetica", 11), activestyle="none",
            height=5, selectmode="browse"
        )
        self.alarm_listbox.pack(fill="both", expand=True, padx=14, pady=(0, 13))

    def _build_stopwatch_tab(self, parent, colors):
        tk.Label(
            parent, text="Stay in your rhythm", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 17, "bold")
        ).pack(anchor="w", padx=20, pady=(22, 3))
        tk.Label(
            parent, text="Track elapsed time and save lap marks.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w", padx=20, pady=(0, 15))
        display_card = self._clock_card(parent, colors)
        display_card.pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(display_card, text="STOPWATCH", bg=colors[CARD], fg=colors[MUTED],
                 font=("Helvetica", 9, "bold")).pack(pady=(18, 2))
        self.stopwatch_display = tk.Label(
            display_card, text="00:00:00.0", bg=colors[CARD], fg=colors[ACCENT],
            font=("Helvetica", 38, "bold")
        )
        elapsed = self.stopwatch_elapsed
        if self.stopwatch_started_at is not None:
            elapsed += time.perf_counter() - self.stopwatch_started_at
        self.stopwatch_display.configure(
            text=self._format_duration(elapsed, True)
        )
        self.stopwatch_display.pack(pady=(0, 18))
        controls = tk.Frame(display_card, bg=colors[CARD])
        controls.pack(pady=(0, 17))
        self.stopwatch_button = tk.Button(
            controls, text="Start", command=self._toggle_stopwatch,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0, padx=18, pady=9,
            font=("Helvetica", 10, "bold"), cursor="hand2"
        )
        self.stopwatch_button.pack(side="left", padx=5)
        if self.stopwatch_started_at is not None:
            self.stopwatch_button.configure(text="Pause")
        tk.Button(
            controls, text="Lap", command=self._record_lap,
            bg=colors[BG], fg=colors[TEXT], relief="flat", bd=0,
            padx=18, pady=9, cursor="hand2"
        ).pack(side="left", padx=5)
        tk.Button(
            controls, text="Reset", command=self._reset_stopwatch,
            bg=colors[BG], fg=colors[TEXT], relief="flat", bd=0,
            padx=18, pady=9, cursor="hand2"
        ).pack(side="left", padx=5)
        lap_card = self._clock_card(parent, colors)
        lap_card.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        tk.Label(lap_card, text="LAP HISTORY", bg=colors[CARD], fg=colors[MUTED],
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=15, pady=(12, 7))
        self.lap_listbox = tk.Listbox(
            lap_card, height=5, relief="flat", bd=0, bg=colors[BG],
            fg=colors[TEXT], highlightthickness=0, font=("Helvetica", 10),
            activestyle="none"
        )
        self.lap_listbox.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def _build_timer_tab(self, parent, colors):
        tk.Label(
            parent, text="Make time for what matters", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 17, "bold")
        ).pack(anchor="w", padx=20, pady=(22, 3))
        tk.Label(
            parent, text="Set a countdown and let Focus Desk keep time.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w", padx=20, pady=(0, 15))
        display_card = self._clock_card(parent, colors)
        display_card.pack(fill="x", padx=18, pady=(0, 15))
        tk.Label(display_card, text="COUNTDOWN", bg=colors[CARD], fg=colors[MUTED],
                 font=("Helvetica", 9, "bold")).pack(pady=(16, 2))
        self.timer_display = tk.Label(
            display_card, text="00:00:00", bg=colors[CARD], fg=colors[ACCENT],
            font=("Helvetica", 38, "bold")
        )
        remaining = self.timer_remaining
        if self.timer_deadline is not None:
            remaining = max(0, self.timer_deadline - time.time())
        self.timer_display.configure(text=self._format_duration(remaining))
        self.timer_display.pack(pady=(0, 12))
        fields = tk.Frame(display_card, bg=colors[CARD])
        fields.pack(pady=(0, 17))
        self.timer_hours = tk.StringVar(value="0")
        self.timer_minutes = tk.StringVar(value="5")
        self.timer_seconds = tk.StringVar(value="0")
        for label, variable, limit in (
            ("hours", self.timer_hours, 99),
            ("minutes", self.timer_minutes, 59),
            ("seconds", self.timer_seconds, 59),
        ):
            field = tk.Frame(fields, bg=colors[CARD])
            field.pack(side="left", padx=6)
            tk.Spinbox(
                field, from_=0, to=limit, width=4, textvariable=variable,
                justify="center", relief="flat", bg=colors[BG], fg=colors[TEXT],
                buttonbackground=colors[BG], font=("Helvetica", 12)
            ).pack()
            tk.Label(field, text=label.upper(), bg=colors[CARD], fg=colors[MUTED],
                     font=("Helvetica", 9)).pack(pady=(4, 0))
        controls = tk.Frame(parent, bg=colors[BG])
        controls.pack(pady=(2, 10))
        self.timer_button = tk.Button(
            controls, text="Start", command=self._toggle_timer,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0, padx=20, pady=10,
            font=("Helvetica", 10, "bold"), cursor="hand2"
        )
        self.timer_button.pack(side="left", padx=5)
        if self.timer_deadline is not None:
            self.timer_button.configure(text="Pause")
        elif self.timer_remaining > 0:
            self.timer_button.configure(text="Resume")
        tk.Button(
            controls, text="Reset", command=self._reset_timer,
            bg=colors[CARD], fg=colors[TEXT], relief="flat", bd=0,
            padx=18, pady=10, cursor="hand2"
        ).pack(side="left", padx=5)
        self.timer_status = tk.Label(
            parent, text="", bg=colors[BG], fg=colors[MUTED],
            font=("Helvetica", 10, "bold")
        )
        self.timer_status.pack()

    def _clock_card(self, parent, colors):
        return tk.Frame(
            parent, bg=colors[CARD],
            highlightbackground=colors.get("#E8EBF1", "#E6EAF2"),
            highlightthickness=1
        )

    def _close_clock_tools(self):
        self.clock_window.destroy()
        self.clock_window = None
        if not self._clock_is_active() and self._clock_after_id is not None:
            self.after_cancel(self._clock_after_id)
            self._clock_after_id = None

    def _add_alarm(self):
        try:
            alarm_time = datetime.strptime(
                self.alarm_time_entry.get().strip(), "%H:%M"
            ).time()
        except ValueError:
            self.alarm_status.configure(text="Enter a valid time in HH:MM format.")
            return

        now = datetime.now()
        alarm_at = datetime.combine(now.date(), alarm_time)
        if alarm_at <= now:
            alarm_at += timedelta(days=1)
        label = self.alarm_label_entry.get().strip() or "Alarm"
        try:
            stored_alarm = self.focus_backend.add_alarm(alarm_at.timestamp(), label)
        except ValueError as error:
            self.alarm_status.configure(text=str(error))
            return
        self.alarms.append({
            "id": stored_alarm["id"],
            "time": alarm_at,
            "label": stored_alarm["label"],
        })
        self.alarms.sort(key=lambda alarm: alarm["time"])
        self.alarm_status.configure(text="Alarm set for {}".format(alarm_at.strftime("%b %d, %H:%M")))
        self._refresh_alarm_list()

    def _refresh_alarm_list(self):
        if getattr(self, "alarm_listbox", None) is None:
            return
        if not self.alarm_listbox.winfo_exists():
            return
        self.alarm_listbox.delete(0, "end")
        for alarm in self.alarms:
            self.alarm_listbox.insert(
                "end", "{}  —  {}".format(
                    alarm["time"].strftime("%b %d, %H:%M"), alarm["label"]
                )
            )

    def _delete_alarm(self):
        selected = list(self.alarm_listbox.curselection())
        alarm_ids = [self.alarms[index]["id"] for index in selected]
        self.focus_backend.delete_alarms(alarm_ids)
        for index in reversed(selected):
            del self.alarms[index]
        self._refresh_alarm_list()

    def _check_alarms(self):
        completed_count = len(self.focus_backend.completed_sessions)
        self.focus_backend.remaining_seconds()
        if len(self.focus_backend.completed_sessions) > completed_count:
            self._refresh_productivity()

        due = self.focus_backend.take_due_alarms()
        if due:
            due_ids = {alarm["id"] for alarm in due}
            self.alarms = [
                alarm for alarm in self.alarms if alarm["id"] not in due_ids
            ]
            self._refresh_alarm_list()
            for alarm in due:
                self.bell()
                messagebox.showinfo(
                    "Alarm", alarm["label"], parent=self
                )
        self.after(500, self._check_alarms)

    def _clock_is_active(self):
        return (
            self.stopwatch_started_at is not None
            or self.timer_deadline is not None
        )

    def _schedule_clock_update(self):
        if self._clock_after_id is None and self._clock_is_active():
            self._clock_after_id = self.after(100, self._update_clock_display)

    def _format_duration(self, seconds, tenths=False):
        total_tenths = max(0, int(seconds * 10))
        hours, remainder = divmod(total_tenths, 36000)
        minutes, remainder = divmod(remainder, 600)
        whole_seconds, fractional = divmod(remainder, 10)
        if tenths:
            return "{:02d}:{:02d}:{:02d}.{}".format(
                hours, minutes, whole_seconds, fractional
            )
        return "{:02d}:{:02d}:{:02d}".format(
            hours, minutes, whole_seconds
        )

    def _update_clock_display(self):
        self._clock_after_id = None
        window_open = self.clock_window is not None and self.clock_window.winfo_exists()
        if self.stopwatch_started_at is not None and window_open:
            elapsed = self.stopwatch_elapsed + time.perf_counter() - self.stopwatch_started_at
            self.stopwatch_display.configure(text=self._format_duration(elapsed, True))
        if self.timer_deadline is not None:
            remaining = max(0, int(self.timer_deadline - time.time() + 0.999))
            if window_open:
                self.timer_display.configure(text=self._format_duration(remaining))
            if remaining == 0:
                self.timer_deadline = None
                self.timer_remaining = 0
                if window_open:
                    self.timer_button.configure(text="Start")
                    self.timer_status.configure(text="Timer complete!")
                self.bell()
                messagebox.showinfo("Timer", "Time is up!", parent=self)
        elif window_open:
            self.timer_display.configure(
                text=self._format_duration(self.timer_remaining)
            )
        if self._clock_is_active():
            self._clock_after_id = self.after(100, self._update_clock_display)

    def _toggle_stopwatch(self):
        if self.stopwatch_started_at is None:
            self.stopwatch_started_at = time.perf_counter()
            self.stopwatch_button.configure(text="Pause")
        else:
            self.stopwatch_elapsed += time.perf_counter() - self.stopwatch_started_at
            self.stopwatch_started_at = None
            self.stopwatch_button.configure(text="Start")
        self._schedule_clock_update()

    def _record_lap(self):
        if self.stopwatch_started_at is None:
            return
        elapsed = self.stopwatch_elapsed + time.perf_counter() - self.stopwatch_started_at
        self.lap_listbox.insert("end", self._format_duration(elapsed, True))
        self.lap_listbox.see("end")

    def _reset_stopwatch(self):
        self.stopwatch_started_at = None
        self.stopwatch_elapsed = 0.0
        self.stopwatch_button.configure(text="Start")
        self.stopwatch_display.configure(text="00:00:00.0")
        self.lap_listbox.delete(0, "end")
        if not self._clock_is_active() and self._clock_after_id is not None:
            self.after_cancel(self._clock_after_id)
            self._clock_after_id = None

    def _toggle_timer(self):
        if self.timer_deadline is not None:
            self.timer_remaining = max(0, self.timer_deadline - time.time())
            self.timer_deadline = None
            self.timer_button.configure(text="Resume")
            self.timer_status.configure(text="Timer paused")
            return
        if self.timer_remaining <= 0:
            try:
                hours = int(self.timer_hours.get())
                minutes = int(self.timer_minutes.get())
                seconds = int(self.timer_seconds.get())
                if not 0 <= hours <= 99 or not 0 <= minutes <= 59 or not 0 <= seconds <= 59:
                    raise ValueError
            except ValueError:
                self.timer_status.configure(text="Enter valid timer values.")
                return
            self.timer_remaining = hours * 3600 + minutes * 60 + seconds
        if self.timer_remaining <= 0:
            self.timer_status.configure(text="Set a duration greater than zero.")
            return
        self.timer_deadline = time.time() + self.timer_remaining
        self.timer_button.configure(text="Pause")
        self.timer_status.configure(text="")
        self._schedule_clock_update()

    def _reset_timer(self):
        self.timer_deadline = None
        self.timer_remaining = 0
        self.timer_display.configure(text="00:00:00")
        self.timer_button.configure(text="Start")
        self.timer_status.configure(text="")
        if not self._clock_is_active() and self._clock_after_id is not None:
            self.after_cancel(self._clock_after_id)
            self._clock_after_id = None

    def _open_focus_mode(self):
        if getattr(self, "focus_window", None) is not None and self.focus_window.winfo_exists():
            self.focus_window.lift()
            return

        colors = self._theme_colors
        window = tk.Toplevel(self)
        self.focus_window = window
        window.title("Focus mode")
        window.geometry("540x760")
        window.minsize(480, 700)
        window.configure(bg=colors[BG])
        window.protocol("WM_DELETE_WINDOW", self._close_focus_mode)

        heading = tk.Frame(window, bg=colors[BG])
        heading.pack(fill="x", padx=28, pady=(22, 14))
        tk.Label(
            heading, text="FOCUS SESSION", bg=colors[BG], fg=colors[ACCENT],
            font=("Helvetica", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            heading, text="Protect your focus", bg=colors[BG], fg=colors[TEXT],
            font=("Helvetica", 24, "bold")
        ).pack(anchor="w", pady=(3, 2))
        tk.Label(
            heading, text="Create a little space for your best work.",
            bg=colors[BG], fg=colors[MUTED], font=("Helvetica", 10)
        ).pack(anchor="w")

        hero = tk.Frame(
            window, bg=colors["#20283B"], highlightthickness=0
        )
        hero.pack(fill="x", padx=22, pady=(0, 14))
        tk.Label(
            hero, text="TIME TO FOCUS", bg=colors["#20283B"],
            fg=colors["#AAB2C2"], font=("Helvetica", 9, "bold")
        ).pack(pady=(15, 0))
        self.focus_timer_display = tk.Label(
            hero, text="25:00", bg=colors["#20283B"], fg="white",
            font=("Helvetica", 38, "bold")
        )
        self.focus_timer_display.pack(pady=(0, 3))
        self.focus_status = tk.Label(
            hero, text="Ready when you are", bg=colors["#20283B"],
            fg=colors["#AAB2C2"], font=("Helvetica", 10)
        )
        self.focus_status.pack(pady=(0, 15))

        card = tk.Frame(
            window, bg=colors[CARD],
            highlightbackground=colors.get("#E8EBF1", "#E6EAF2"),
            highlightthickness=1
        )
        card.pack(fill="both", expand=True, padx=22, pady=(0, 14))
        list_heading = tk.Frame(card, bg=colors[CARD])
        list_heading.pack(fill="x", padx=16, pady=(14, 3))
        tk.Label(
            list_heading, text="DISTRACTION LIST", bg=colors[CARD],
            fg=colors[TEXT], font=("Helvetica", 10, "bold")
        ).pack(side="left")
        tk.Label(
            list_heading, text="Optional", bg=colors[CARD], fg=colors[MUTED],
            font=("Helvetica", 9)
        ).pack(side="right")
        tk.Label(
            card, text="Keep distracting apps and sites in view while you work.",
            bg=colors[CARD], fg=colors[MUTED], font=("Helvetica", 9)
        ).pack(anchor="w", padx=16, pady=(0, 10))

        entry_row = tk.Frame(card, bg=colors[CARD])
        entry_row.pack(fill="x", padx=16)
        self.focus_entry = tk.Entry(entry_row, relief="flat", bd=0,
                                    bg=colors[BG], fg=colors[TEXT],
                                    insertbackground=colors[TEXT])
        self.focus_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        tk.Button(entry_row, text="＋ Add", command=self._add_focus_item,
                  bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
                  activeforeground="white", relief="flat", bd=0,
                  font=("Helvetica", 9, "bold"), padx=14, pady=9,
                  cursor="hand2").pack(side="right")
        self.focus_entry.bind("<Return>", lambda _event: self._add_focus_item())

        list_frame = tk.Frame(card, bg=colors[CARD])
        list_frame.pack(fill="both", expand=True, padx=16, pady=12)
        self.focus_listbox = tk.Listbox(
            list_frame, selectmode="extended", relief="flat", bd=0,
            bg=colors[BG], fg=colors[TEXT], selectbackground=colors[ACCENT],
            selectforeground="white", font=("Helvetica", 10),
            highlightthickness=0, activestyle="none", height=4
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
                  cursor="hand2").pack(anchor="w", padx=16, pady=(0, 13))

        controls = tk.Frame(window, bg=colors[BG])
        controls.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(controls, text="Session length", bg=colors[BG], fg=colors[TEXT],
                 font=("Helvetica", 10, "bold")).pack(side="left")
        self.focus_minutes = tk.StringVar(value="25")
        tk.Spinbox(
            controls, from_=1, to=180, width=5, textvariable=self.focus_minutes,
            relief="flat", bg=colors[CARD], fg=colors[TEXT],
            buttonbackground=colors[CARD], font=("Helvetica", 11)
        ).pack(side="right")
        tk.Label(controls, text="minutes", bg=colors[BG], fg=colors[MUTED],
                 font=("Helvetica", 9)).pack(side="right", padx=8)
        self.focus_button = tk.Button(
            window, text="Start focus session", command=self._toggle_focus_session,
            bg=colors[ACCENT], fg="white", activebackground=colors[ACCENT],
            activeforeground="white", relief="flat", bd=0,
            font=("Helvetica", 11, "bold"), padx=20, pady=12, cursor="hand2"
        )
        self.focus_button.pack(fill="x", padx=24, pady=(0, 22))
        self._focus_after_id = None
        remaining = self.focus_backend.remaining_seconds()
        if self.focus_backend.is_running():
            self.focus_button.configure(text="Pause focus session")
            self._update_focus_countdown()
        elif remaining > 0:
            minutes, seconds = divmod(remaining, 60)
            self.focus_timer_display.configure(text="{:02d}:{:02d}".format(minutes, seconds))
            self.focus_button.configure(text="Resume focus session")
            self.focus_status.configure(text="Session paused")

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
            self.focus_timer_display.configure(text="00:00")
            self.focus_button.configure(text="Start focus session")
            self.focus_status.configure(text="Session complete — nice work!")
            self._focus_after_id = None
            self._refresh_productivity()
            return
        self.focus_timer_display.configure(
            text="{:02d}:{:02d}".format(minutes, seconds)
        )
        self.focus_status.configure(text="Session in progress")
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
            BG: "#F5F7FB", CARD: "#FFFFFF", TEXT: "#20243A",
            MUTED: "#778097", ACCENT: "#5F63F2", GREEN: "#219A78",
            "#20283B": "#1D2440", "#AAB2C2": "#B8C0D4",
            "#343E56": "#303B61", "#7F899D": "#8791AB",
            "#3A4357": "#414B67", "#E79742": "#D88936",
            "#EEF0FF": "#EEF0FF", "#E3E6FF": "#E1E4FF",
            "#39A88A": "#258A73", "#8993A6": "#8993A6",
            "#EEF0F4": "#EEF1F7", "#E8EBF1": "#E6EAF2"
        }
        dark_colors = {
            BG: "#111827", CARD: "#1B2434", TEXT: "#F0F3FA",
            MUTED: "#9AA7BA", ACCENT: "#9290FF", GREEN: "#5DD4A7",
            "#20283B": "#0D1423", "#AAB2C2": "#AAB6CA",
            "#343E56": "#263451", "#7F899D": "#8593AD",
            "#3A4357": "#303B52", "#E79742": "#ECA85B",
            "#EEF0FF": "#292C4A", "#E3E6FF": "#34385E",
            "#39A88A": "#45B89B", "#8993A6": "#A0ADC1",
            "#EEF0F4": "#2B3547", "#E8EBF1": "#303B4C"
        }
        self._theme_colors = dark_colors if dark else light_colors
        self._active_theme = "dark" if dark else "light"
        self.configure(bg=self._theme_colors[BG])
        self._recolor_widget(self)
        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel) and child.winfo_exists():
                self._recolor_widget(child)
        self._configure_ttk_theme()

    def _configure_ttk_theme(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        colors = self._theme_colors
        style.configure(
            "TNotebook", background=colors[BG], borderwidth=0, tabmargins=(0, 0, 0, 0)
        )
        style.configure(
            "TNotebook.Tab", background=colors[CARD], foreground=colors[MUTED],
            padding=(16, 10), borderwidth=0, font=("Helvetica", 10, "bold")
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", colors[BG]), ("active", colors[CARD])],
            foreground=[("selected", colors[ACCENT]), ("active", colors[TEXT])],
        )
        style.configure(
            "Theme.TCombobox", fieldbackground=colors[CARD], background=colors[CARD],
            foreground=colors[TEXT], arrowcolor=colors[ACCENT], padding=(8, 6),
            borderwidth=0, font=("Helvetica", 10)
        )
        style.configure(
            "Productivity.Horizontal.TProgressbar",
            troughcolor=colors[BG], background=colors[ACCENT],
            bordercolor=colors[BG], lightcolor=colors[ACCENT],
            darkcolor=colors[ACCENT], thickness=10
        )
        style.map(
            "Theme.TCombobox",
            fieldbackground=[("readonly", colors[CARD])],
            foreground=[("readonly", colors[TEXT])],
        )

    def _recolor_widget(self, widget):
        dark_to_light = {dark: light for light, dark in THEME_COLOR_PAIRS}
        light_to_dark = {light: dark for light, dark in THEME_COLOR_PAIRS}
        for option in ("bg", "fg", "activebackground", "activeforeground",
                       "selectcolor", "highlightbackground", "highlightcolor",
                       "insertbackground", "buttonbackground"):
            try:
                current = widget.cget(option)
                if self._active_theme == "dark":
                    light = dark_to_light.get(
                        current, THEME_COLOR_ALIASES.get(current, current)
                    )
                    target = light_to_dark.get(light, light)
                else:
                    target = dark_to_light.get(
                        current, THEME_COLOR_ALIASES.get(current, current)
                    )
                if target != current:
                    widget.configure(**{option: target})
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
        elif title == "FOCUS TIME":
            self.focus_time_value = value_label
            self.focus_time_subtitle = subtitle_label
        elif title == "DAILY GOAL":
            self.daily_goal_value = value_label

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

    def _task_row(self, parent, title, due, completed, task_id=None):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=20, pady=8)
        checked = tk.BooleanVar(value=completed)
        normal_font = tkfont.Font(self, family="Helvetica", size=11)
        completed_font = tkfont.Font(self, family="Helvetica", size=11, overstrike=True)
        label = tk.Label(row, text=title, bg=CARD, fg=TEXT, font=normal_font)
        task = {
            "checked": checked,
            "label": label,
            "row": row,
            "task_id": task_id,
            "normal_font": normal_font,
            "completed_font": completed_font,
        }
        check = tk.Checkbutton(
            row, variable=checked, command=lambda item=task: self._toggle_task(item),
            bg=CARD, activebackground=CARD, selectcolor=CARD,
            bd=0, highlightthickness=0
        )
        check.pack(side="left")
        label.pack(side="left", padx=5)
        tk.Button(
            row, text="Delete",
            command=lambda item=task: self._delete_task(item),
            bg=CARD, fg="#C94B50", activebackground=CARD,
            activeforeground="#A93439", relief="flat", bd=0,
            font=("Helvetica", 9), cursor="hand2",
        ).pack(side="right", padx=(8, 0))
        if due:
            tk.Label(row, text=due, bg=CARD, fg=MUTED,
                     font=("Helvetica", 9)).pack(side="right")
        self.task_items.append(task)
        self._style_task(task)
        self._update_task_summary()
        return task

    def _on_task_list_configure(self, _event=None):
        self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all"))

    def _scroll_to_latest_task(self):
        self._scroll_task_after_id = None
        if not self.winfo_exists():
            return
        self.update_idletasks()
        self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all"))
        self.task_canvas.yview_moveto(1.0)

    def _cancel_pending_task_scroll(self, event):
        if event.widget is self and self._scroll_task_after_id is not None:
            try:
                self.after_cancel(self._scroll_task_after_id)
            except tk.TclError:
                pass
            self._scroll_task_after_id = None

    def _delete_task(self, task):
        if task not in self.task_items:
            return
        if task["task_id"] is not None:
            self.focus_backend.delete_task(task["task_id"])
        self.task_items.remove(task)
        task["row"].destroy()
        self._update_task_summary()

    def _toggle_task(self, task):
        if task["task_id"] is not None:
            self.focus_backend.set_task_completed(
                task["task_id"], task["checked"].get()
            )
        self._style_task(task)
        self._update_task_summary()

    def _style_task(self, task):
        completed = task["checked"].get()
        task["label"].configure(
            fg=self._theme_colors.get(
                GREEN if completed else TEXT, GREEN if completed else TEXT
            ),
            font=task["completed_font"] if completed else task["normal_font"]
        )

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
        self._refresh_reports()

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
        from tkinter import simpledialog
        title = simpledialog.askstring("Add a task", "Task name:", parent=self)
        if title and title.strip():
            try:
                task = self.focus_backend.add_task(title)
            except ValueError as error:
                messagebox.showerror("Could not add task", str(error), parent=self)
                return
            self._task_row(
                self.task_list, task["title"], "", False, task_id=task["id"]
            )
            if self._scroll_task_after_id is not None:
                self.after_cancel(self._scroll_task_after_id)
            self._scroll_task_after_id = self.after_idle(
                self._scroll_to_latest_task
            )
            self._apply_theme()


if __name__ == "__main__":
    Dashboard().mainloop()
