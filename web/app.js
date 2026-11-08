const state = {
  tasks: [],
  alarms: [],
  focus: { running: false, remaining_seconds: 0 },
  stopwatchStarted: null,
  stopwatchElapsed: 0,
  timerStarted: null,
  timerRemaining: 0,
  toastTimeout: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(state.toastTimeout);
  state.toastTimeout = setTimeout(() => toast.classList.remove("visible"), 2800);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The server returned an invalid response.");
  }
  if (!response.ok) throw new Error(payload.error || "Request failed.");
  return payload;
}

function formatMinutes(minutes) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return hours ? `${hours}h ${remainder}m` : `${remainder}m`;
}

function formatClock(totalSeconds, tenths = false) {
  const safe = Math.max(0, totalSeconds);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const seconds = Math.floor(safe % 60);
  const base = [hours, minutes, seconds].map((part) => String(part).padStart(2, "0")).join(":");
  return tenths ? `${base}.${Math.floor((safe % 1) * 10)}` : base;
}

function setView(view) {
  $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === view));
  $$(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  const names = {
    dashboard: ["Welcome back", "A little focus goes a long way."],
    tasks: ["Your tasks", "Turn your plans into small, finished steps."],
    focus: ["Focus session", "Set a pace, start your session, and settle in."],
    clock: ["Clock tools", "Useful time tools for your study day."],
    reports: ["Study reports", "A clear view of the work you have completed."],
  };
  $("#page-title").textContent = names[view][0];
  $("#page-subtitle").textContent = names[view][1];
  location.hash = view;
}

function createTaskItem(task, compact = false) {
  const item = document.createElement("li");
  item.className = `task-item${task.completed ? " completed" : ""}`;
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.completed;
  checkbox.setAttribute("aria-label", `Mark ${task.title} complete`);
  checkbox.addEventListener("change", async () => {
    try {
      await request(`/api/tasks/${encodeURIComponent(task.id)}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: checkbox.checked }),
      });
      await refresh();
    } catch (error) {
      checkbox.checked = !checkbox.checked;
      showToast(error.message);
    }
  });
  const title = document.createElement("span");
  title.className = "task-title";
  title.textContent = task.title;
  const remove = document.createElement("button");
  remove.className = "delete-button";
  remove.type = "button";
  remove.textContent = "Delete";
  remove.setAttribute("aria-label", `Delete ${task.title}`);
  remove.addEventListener("click", async () => {
    try {
      await request(`/api/tasks/${encodeURIComponent(task.id)}`, { method: "DELETE" });
      await refresh();
      showToast("Task deleted.");
    } catch (error) {
      showToast(error.message);
    }
  });
  item.append(checkbox, title, remove);
  if (compact) item.classList.add("compact");
  return item;
}

function renderTasks(tasks) {
  state.tasks = tasks;
  const lists = [$("#task-list"), $("#task-list-secondary")];
  lists.forEach((list) => {
    list.replaceChildren(...tasks.map((task) => createTaskItem(task)));
  });
  const completed = tasks.filter((task) => task.completed).length;
  const remaining = tasks.length - completed;
  $("#tasks-remaining").textContent = `${remaining} remaining`;
  $("#tasks-count").textContent = `${tasks.length} task${tasks.length === 1 ? "" : "s"}`;
  $("#stat-tasks").textContent = `${completed} / ${tasks.length}`;
  $("#stat-tasks-caption").textContent = `${remaining} remaining`;
  $("#tasks-empty").hidden = tasks.length > 0;
  $("#tasks-empty-secondary").hidden = tasks.length > 0;
}

function renderDistractions(items) {
  const list = $("#distraction-list");
  list.replaceChildren();
  items.forEach((text, index) => {
    const item = document.createElement("li");
    item.className = "task-item";
    const label = document.createElement("span");
    label.className = "task-title";
    label.textContent = text;
    const remove = document.createElement("button");
    remove.className = "delete-button";
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", async () => {
      try {
        await request("/api/distractions", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ index }),
        });
        await refresh();
      } catch (error) {
        showToast(error.message);
      }
    });
    item.append(label, remove);
    list.append(item);
  });
}

function renderAlarms(alarms) {
  state.alarms = alarms;
  const list = $("#alarm-list");
  list.replaceChildren();
  if (!alarms.length) {
    const empty = document.createElement("li");
    empty.className = "task-item";
    empty.textContent = "No alarms set.";
    list.append(empty);
    return;
  }
  alarms.forEach((alarm) => {
    const item = document.createElement("li");
    item.className = "task-item";
    const time = document.createElement("strong");
    time.textContent = new Date(alarm.timestamp * 1000).toLocaleString([], {
      weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
    const label = document.createElement("span");
    label.className = "task-title";
    label.textContent = alarm.label;
    const remove = document.createElement("button");
    remove.className = "delete-button";
    remove.type = "button";
    remove.textContent = "Delete";
    remove.addEventListener("click", async () => {
      try {
        await request(`/api/alarms/${encodeURIComponent(alarm.id)}`, { method: "DELETE" });
        await refresh();
      } catch (error) {
        showToast(error.message);
      }
    });
    item.append(time, label, remove);
    list.append(item);
  });
}

function renderSessions(sessions) {
  const list = $("#session-list");
  list.replaceChildren();
  $("#sessions-empty").hidden = sessions.length > 0;
  sessions.forEach((session) => {
    const item = document.createElement("li");
    const completedAt = new Date(session.completed_at * 1000);
    item.textContent = `${completedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · ${formatMinutes(Math.floor(session.duration_seconds / 60))}`;
    list.append(item);
  });
}

function renderDayChart(sessions) {
  const minutesByHour = Array(24).fill(0);
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  sessions.forEach((session) => {
    let cursor = Math.max(
      todayStart.getTime(),
      (session.completed_at - Math.max(0, session.duration_seconds)) * 1000,
    );
    const end = session.completed_at * 1000;
    while (cursor < end) {
      const hourStart = new Date(cursor);
      const hour = hourStart.getHours();
      const nextHour = new Date(hourStart);
      nextHour.setMinutes(60, 0, 0);
      const segmentEnd = Math.min(end, nextHour.getTime());
      minutesByHour[hour] += (segmentEnd - cursor) / 60000;
      cursor = segmentEnd;
    }
  });

  const peakMinutes = Math.max(...minutesByHour);
  const peakHour = minutesByHour.indexOf(peakMinutes);
  const period = $("#productive-period");
  period.textContent = peakMinutes > 0
    ? `Most focused: ${new Date(2020, 0, 1, peakHour).toLocaleTimeString([], { hour: "numeric" })}–${new Date(2020, 0, 1, peakHour + 1).toLocaleTimeString([], { hour: "numeric" })} · ${Math.round(peakMinutes)} min`
    : "No completed focus sessions yet.";

  const chart = $("#day-chart");
  chart.setAttribute("aria-label", peakMinutes > 0
    ? `Hourly focus time across today. Most focused: ${period.textContent}.`
    : "No completed focus sessions yet.");
  chart.replaceChildren(...minutesByHour.map((minutes, hour) => {
    const column = document.createElement("div");
    column.className = "day-chart-column";
    const bar = document.createElement("span");
    bar.className = `day-chart-bar${minutes === peakMinutes && minutes > 0 ? " peak" : ""}`;
    bar.style.height = peakMinutes > 0 ? `${minutes / peakMinutes * 100}%` : "0%";
    bar.title = `${new Date(2020, 0, 1, hour).toLocaleTimeString([], { hour: "numeric" })}: ${Math.round(minutes)} min`;
    bar.setAttribute("aria-hidden", "true");
    column.append(bar);
    return column;
  }));
}

function applyState(data) {
  renderTasks(data.tasks);
  renderAlarms(data.alarms);
  renderDistractions(data.distractions || []);
  const displayName = data.profile.name || "Your profile";
  $("#profile-name").textContent = displayName;
  $("#profile-bio").textContent = data.profile.bio || "Add a name and bio";
  $("#avatar").textContent = data.profile.name
    ? data.profile.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()
    : "?";
  $("#stat-focus").textContent = formatMinutes(data.focus_minutes);
  $("#stat-goal").textContent = `${data.goal_minutes}m`;
  $("#score-value").textContent = data.rating.score;
  $("#score-rating").textContent = data.rating.rating;
  $("#score-message").textContent = data.rating.message;
  $("#goal-caption").textContent = `${data.focus_minutes} of ${data.goal_minutes} minutes`;
  $("#goal-progress").style.width = `${data.rating.score}%`;
  $("#score-ring").style.setProperty("--score", `${data.rating.score}%`);
  if (!data.focus.running && document.activeElement !== $("#focus-minutes") &&
      !$("#focus-minutes").value) {
    $("#focus-minutes").value = 25;
  }
  state.focus = data.focus;
  $("#focus-clock").textContent = formatClock(data.focus.remaining_seconds);
  $("#focus-status").textContent = data.focus.running
    ? "Session in progress — stay with one thing."
    : data.focus.remaining_seconds > 0 ? "Session paused" : "Ready when you are";
  $("#focus-toggle").textContent = data.focus.running
    ? "Pause session" : data.focus.remaining_seconds > 0 ? "Resume session" : "Start focus session";
  $("#report-focus").textContent = formatMinutes(data.focus_minutes);
  $("#report-score").textContent = `${data.rating.score} / 100`;
  $("#report-tasks").textContent = `${data.tasks.filter((task) => task.completed).length} / ${data.tasks.length}`;
  renderDayChart(data.completed_sessions);
  renderSessions(data.completed_sessions);
  if (!$("#profile-dialog").open) {
    $("#profile-name-input").value = data.profile.name;
    $("#profile-bio-input").value = data.profile.bio;
    $("#profile-goal-input").value = data.goal_minutes;
  }
  data.due_alarms.forEach((alarm) => {
    showToast(`Alarm: ${alarm.label}`);
    window.alert(`Alarm: ${alarm.label}`);
  });
}

async function refresh() {
  try {
    applyState(await request("/api/state"));
  } catch (error) {
    showToast(error.message);
  }
}

async function submitTask(input) {
  const title = input.value.trim();
  if (!title) return;
  try {
    await request("/api/tasks", { method: "POST", body: JSON.stringify({ title }) });
    input.value = "";
    await refresh();
    showToast("Task added.");
  } catch (error) {
    showToast(error.message);
  }
}

$("#task-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitTask($("#task-title"));
});
$("#task-form-secondary").addEventListener("submit", (event) => {
  event.preventDefault();
  submitTask($("#task-title-secondary"));
});

$("#focus-toggle").addEventListener("click", async () => {
  try {
    if (state.focus.running) {
      await request("/api/focus/pause", { method: "POST", body: "{}" });
    } else {
      const minutes = Number($("#focus-minutes").value);
      if (!Number.isInteger(minutes) || minutes < 1 || minutes > 180) {
        throw new Error("Session length must be from 1 to 180 minutes.");
      }
      await request("/api/focus/start", { method: "POST", body: JSON.stringify({ minutes }) });
    }
    await refresh();
  } catch (error) {
    showToast(error.message);
  }
});

$("#distraction-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = $("#distraction-input").value.trim();
  if (!value) return;
  try {
    await request("/api/distractions", { method: "POST", body: JSON.stringify({ value }) });
    $("#distraction-input").value = "";
    await refresh();
  } catch (error) {
    showToast(error.message);
  }
});

$("#alarm-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const [hours, minutes] = $("#alarm-time").value.split(":").map(Number);
  const now = new Date();
  const alarmAt = new Date(now);
  alarmAt.setHours(hours, minutes, 0, 0);
  if (alarmAt <= now) alarmAt.setDate(alarmAt.getDate() + 1);
  try {
    await request("/api/alarms", {
      method: "POST",
      body: JSON.stringify({
        timestamp: alarmAt.getTime() / 1000,
        label: $("#alarm-label").value.trim() || "Alarm",
      }),
    });
    $("#alarm-label").value = "";
    await refresh();
    showToast(`Alarm set for ${alarmAt.toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}.`);
  } catch (error) {
    showToast(error.message);
  }
});

$("#timer-toggle").addEventListener("click", () => {
  if (state.timerStarted !== null) {
    state.timerRemaining = Math.max(0, state.timerStarted - Date.now() / 1000);
    state.timerStarted = null;
    $("#timer-toggle").textContent = "Resume timer";
    $("#timer-status").textContent = "Timer paused";
    return;
  }
  if (state.timerRemaining <= 0) {
    const hours = Number($("#timer-hours").value);
    const minutes = Number($("#timer-minutes").value);
    const seconds = Number($("#timer-seconds").value);
    if (![hours, minutes, seconds].every(Number.isInteger) ||
        hours < 0 || hours > 99 || minutes < 0 || minutes > 59 ||
        seconds < 0 || seconds > 59 || hours * 3600 + minutes * 60 + seconds <= 0) {
      showToast("Enter a valid timer duration greater than zero.");
      return;
    }
    state.timerRemaining = hours * 3600 + minutes * 60 + seconds;
  }
  state.timerStarted = Date.now() / 1000 + state.timerRemaining;
  $("#timer-toggle").textContent = "Pause timer";
  $("#timer-status").textContent = "";
});

$("#timer-reset").addEventListener("click", () => {
  state.timerStarted = null;
  state.timerRemaining = 0;
  $("#timer-display").textContent = "00:00:00";
  $("#timer-toggle").textContent = "Start timer";
  $("#timer-status").textContent = "";
});

$("#stopwatch-toggle").addEventListener("click", () => {
  if (state.stopwatchStarted === null) {
    state.stopwatchStarted = Date.now() / 1000;
    $("#stopwatch-toggle").textContent = "Pause";
  } else {
    state.stopwatchElapsed += Date.now() / 1000 - state.stopwatchStarted;
    state.stopwatchStarted = null;
    $("#stopwatch-toggle").textContent = "Start";
  }
});
$("#stopwatch-lap").addEventListener("click", () => {
  if (state.stopwatchStarted === null) return;
  const elapsed = state.stopwatchElapsed + Date.now() / 1000 - state.stopwatchStarted;
  const lap = document.createElement("li");
  lap.textContent = `Lap ${$("#lap-list").children.length + 1} · ${formatClock(elapsed, true)}`;
  $("#lap-list").prepend(lap);
});
$("#stopwatch-reset").addEventListener("click", () => {
  state.stopwatchStarted = null;
  state.stopwatchElapsed = 0;
  $("#stopwatch-toggle").textContent = "Start";
  $("#stopwatch-display").textContent = "00:00:00.0";
  $("#lap-list").replaceChildren();
});

$("#profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const save = $("#profile-save");
  if (event.submitter && event.submitter.value === "cancel") {
    $("#profile-dialog").close();
    return;
  }
  save.disabled = true;
  $("#profile-error").textContent = "";
  try {
    const name = $("#profile-name-input").value.trim();
    const bio = $("#profile-bio-input").value.trim();
    const minutes = Number($("#profile-goal-input").value);
    if (!name) {
      $("#profile-name-input").focus();
      throw new Error("Please enter your name before saving your daily goal.");
    }
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 600) {
      throw new Error("Daily study goal must be from 1 to 600 minutes.");
    }
    await request("/api/profile", { method: "POST", body: JSON.stringify({ name, bio }) });
    await request("/api/goal", { method: "POST", body: JSON.stringify({ minutes }) });
    $("#profile-dialog").close();
    await refresh();
    showToast("Profile saved.");
  } catch (error) {
    $("#profile-error").textContent = error.message;
  } finally {
    save.disabled = false;
  }
});

$("#open-profile").addEventListener("click", () => $("#profile-dialog").showModal());
$$(".nav-link").forEach((link) => link.addEventListener("click", (event) => {
  event.preventDefault();
  setView(link.dataset.view);
}));
$$("[data-navigate]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.navigate)));
$$(".clock-tab").forEach((button) => button.addEventListener("click", () => {
  $$(".clock-tab").forEach((tab) => tab.classList.toggle("selected", tab === button));
  $$(".clock-view").forEach((view) => view.classList.toggle("active", view.id === `clock-${button.dataset.tab}`));
}));

$("#theme-toggle").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme !== "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  localStorage.setItem("focus-desk-theme", dark ? "dark" : "light");
  $("#theme-toggle").textContent = dark ? "☀" : "☾";
});

const savedTheme = localStorage.getItem("focus-desk-theme");
if (savedTheme === "dark") {
  document.documentElement.dataset.theme = "dark";
  $("#theme-toggle").textContent = "☀";
}
const now = new Date();
$("#today-date").textContent = now.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
$("#report-date").textContent = now.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
$("#alarm-time").value = new Date(Date.now() + 60 * 60 * 1000).toTimeString().slice(0, 5);
setView(location.hash.slice(1) || "dashboard");
refresh();

setInterval(async () => {
  await refresh();
  if (state.focus.running) {
    $("#focus-clock").textContent = formatClock(state.focus.remaining_seconds);
    if (state.focus.remaining_seconds === 0) {
      showToast("Focus session complete. Nice work!");
      $("#focus-status").textContent = "Session complete — nice work!";
    }
  }
  if (state.stopwatchStarted !== null) {
    const elapsed = state.stopwatchElapsed + Date.now() / 1000 - state.stopwatchStarted;
    $("#stopwatch-display").textContent = formatClock(elapsed, true);
  }
  if (state.timerStarted !== null) {
    state.timerRemaining = Math.max(0, state.timerStarted - Date.now() / 1000);
    $("#timer-display").textContent = formatClock(state.timerRemaining);
    if (state.timerRemaining === 0) {
      state.timerStarted = null;
      $("#timer-toggle").textContent = "Start timer";
      $("#timer-status").textContent = "Timer complete!";
      showToast("Timer complete!");
      window.alert("Timer complete!");
    }
  }
}, 1000);
