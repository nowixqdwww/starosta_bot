const tg = window.Telegram && window.Telegram.WebApp;
const app = document.getElementById("app");
if (tg) { tg.ready(); tg.expand(); }

const startParam = (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || "";
const tgName = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.first_name) || "";

/* ---------- утилиты ---------- */

const $ = (sel) => app.querySelector(sel);

// всё, что пришло от пользователей или сервера, вставляем в HTML только через esc()
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

async function api(path, body) {
  const headers = { Authorization: "tma " + tg.initData };
  if (body) headers["Content-Type"] = "application/json";

  const res = await fetch("/api" + path, {
    method: body ? "POST" : "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    if (res.status === 422) throw new Error("Проверь, что все поля заполнены.");
    throw new Error(typeof data.detail === "string" ? data.detail : "Что-то пошло не так. Попробуй ещё раз.");
  }
  return data;
}

function field(id, label, value = "") {
  return `
    <label class="field" for="${id}">
      <span>${label}</span>
      <input id="${id}" value="${esc(value)}" maxlength="100" autocomplete="off">
    </label>`;
}

function setError(msg) { $(".error").textContent = msg || ""; }

async function submit(btn, action) {
  btn.disabled = true;
  setError("");
  try { await action(); }
  catch (e) { setError(e.message); btn.disabled = false; }
}

/* ---------- экраны ---------- */

function roleScreen() {
  app.innerHTML = `
    <h1>Кто ты?</h1>
    <p class="lead">Нужно выбрать один раз, чтобы всё настроить.</p>
    <button class="row" data-role="leader">
      <span class="row-title">Я староста</span>
      <span class="row-sub">Создам группу и приглашу студентов</span>
    </button>
    <button class="row" data-role="student">
      <span class="row-title">Я студент</span>
      <span class="row-sub">У меня есть код приглашения</span>
    </button>`;

  $('[data-role="leader"]').onclick = leaderScreen;
  $('[data-role="student"]').onclick = () => studentScreen("", true);
}

function leaderScreen() {
  app.innerHTML = `
    <button class="back" id="back">Назад</button>
    <h1>Создай группу</h1>
    <p class="lead">Код для студентов появится сразу после создания.</p>
    <form id="form" novalidate>
      ${field("name", "Твоё имя", tgName)}
      ${field("group", "Название группы")}
      ${field("inst", "Учебное заведение")}
      <p class="error" role="alert"></p>
      <button class="primary" type="submit">Создать группу</button>
    </form>`;

  $("#back").onclick = roleScreen;
  $("#form").onsubmit = (e) => {
    e.preventDefault();
    const name = $("#name").value.trim();
    const group_name = $("#group").value.trim();
    const institution = $("#inst").value.trim();
    if (!name || !group_name || !institution) return setError("Заполни все поля.");

    submit($(".primary"), async () => {
      homeScreen(await api("/register/leader", { name, group_name, institution }));
    });
  };
}

function studentScreen(code, canGoBack) {
  app.innerHTML = `
    ${canGoBack ? '<button class="back" id="back">Назад</button>' : ""}
    <h1>Присоединись к группе</h1>
    <p class="lead">Код можно взять у старосты.</p>
    <form id="form" novalidate>
      <label class="field" for="code">
        <span>Код приглашения</span>
        <input id="code" value="${esc(code)}" maxlength="8" autocomplete="off"
               autocapitalize="characters" spellcheck="false">
      </label>
      <p class="group-preview" id="preview" aria-live="polite"></p>
      ${field("name", "Твоё имя", tgName)}
      <p class="error" role="alert"></p>
      <button class="primary" type="submit">Присоединиться</button>
    </form>`;

  if (canGoBack) $("#back").onclick = roleScreen;

  // как только введён весь код, показываем, какая это группа
  let timer;
  async function checkCode() {
    const box = $("#preview");
    const value = $("#code").value.trim().toUpperCase();
    box.className = "group-preview";
    box.textContent = "";
    if (value.length < 8) return;
    try {
      const g = await api("/invite/" + encodeURIComponent(value));
      box.textContent = `${g.group_name}, ${g.institution}`;
    } catch (e) {
      box.textContent = e.message;
      box.classList.add("bad");
    }
  }
  $("#code").oninput = (e) => {
    e.target.value = e.target.value.toUpperCase();
    clearTimeout(timer);
    timer = setTimeout(checkCode, 250);
  };
  checkCode();

  $("#form").onsubmit = (e) => {
    e.preventDefault();
    const invite_code = $("#code").value.trim();
    const name = $("#name").value.trim();
    if (!invite_code || !name) return setError("Заполни все поля.");

    submit($(".primary"), async () => {
      homeScreen(await api("/register/student", { name, invite_code }));
    });
  };
}

function homeScreen(me) {
  const g = me.group;
  const isLeader = me.role === "leader";

  const invite = isLeader ? `
    <section class="invite">
      <h2>Приглашение для студентов</h2>
      <p class="code">${esc(g.invite_code)}</p>
      <button class="primary" id="share">Поделиться приглашением</button>
      <button class="secondary" id="copy">Скопировать код</button>
    </section>` : "";

  app.innerHTML = `
    <h1>${esc(g.name)}</h1>
    <p class="lead">${esc(g.institution)}</p>
    <p class="hint">${isLeader ? "Староста" : "Студент"}: ${esc(me.name)}</p>
    ${invite}
    <p class="soon">Расписание и посещаемость скоро появятся.</p>`;

  if (!isLeader) return;

  $("#share").onclick = () => {
    const url = "https://t.me/share/url?url=" + encodeURIComponent(g.invite_link)
      + "&text=" + encodeURIComponent("Присоединяйся к группе " + g.name);
    tg.openTelegramLink(url);
  };
  $("#copy").onclick = async (e) => {
    try {
      await navigator.clipboard.writeText(g.invite_code);
      e.target.textContent = "Скопировано";
    } catch {
      e.target.textContent = "Не удалось скопировать";
    }
  };
}

/* ---------- запуск ---------- */

async function start() {
  if (!tg || !tg.initData) {
    app.innerHTML = `<h1>Открой в Telegram</h1>
      <p class="lead">Приложение работает только внутри Telegram.</p>`;
    return;
  }
  try {
    const me = await api("/me");
    if (me.registered) return homeScreen(me);
    // пришёл по ссылке-приглашению: сразу форма студента с готовым кодом
    if (startParam) return studentScreen(startParam.toUpperCase(), false);
    roleScreen();
  } catch (e) {
    app.innerHTML = `<h1>Не удалось загрузить</h1><p class="lead">${esc(e.message)}</p>`;
  }
}

start();
