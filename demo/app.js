"use strict";

const copy = {
  en: {
    skip: "Skip to content",
    caseLabel: "Interactive case study",
    title: "Ellen’s job shortlist",
    lead: "How does one line in a CV lead to two jobs worth reviewing and a plan for the week? Explore Ellen’s fictional case.",
    navMatches: "Job matches",
    navPlan: "Weekly plan",
    profileLabel: "Candidate brief",
    name: "Ellen Example",
    target: "Seeking a QA Engineer role in Poland",
    quote: "“Used SQL queries to compare order totals with payment records.”",
    quoteSource: "From Ellen’s fictional CV",
    matchesTitle: "Review the job matches",
    matchesLead: "Choose a posting to see the evidence and the questions Ellen still needs to ask.",
    qaCity: "Warsaw, Poland",
    testerCity: "Poland",
    matchReason: "Why it surfaced",
    cvEvidence: "What the CV supports",
    toVerify: "Still to confirm",
    planTitle: "Plan the practice week",
    planLead: "Ellen has three hours this week. Each 90-minute session turns a job requirement into something she can check.",
    sessionOne: "Session 01 · 90 min",
    sessionTwo: "Session 02 · 90 min",
    sqlSummary: "Reconcile order totals",
    pythonSummary: "Check payment records",
    assignment: "Assignment",
    output: "What to keep",
    check: "Check your work",
    nextLabel: "Your own workspace",
    nextTitle: "Try it with your own CV",
    nextBody: "Run Career Starter on your computer to import a CV, search for jobs and save a personal learning plan.",
    setupLink: "Local setup on GitHub",
    jobs: {
      qa: {
        kind: "Exact title match",
        reason: "Example Shop is looking for a QA Engineer in Warsaw. The job title matches Ellen’s target directly, and the posting asks for SQL.",
        evidence: "Ellen describes checking order totals against payment records. That gives her a concrete SQL example to discuss in an interview.",
        open: "Ask whether the employer can hire Ellen in Poland, which languages the team uses and what salary range is available.",
        plan: "See the SQL practice →",
      },
      tester: {
        kind: "Related title match",
        reason: "Software Tester is a known alternative title for Ellen’s target role. This fictional posting mentions Poland and asks for SQL and Python.",
        evidence: "Her CV gives a specific SQL example. It says nothing about Python, so her Python experience is still an open question.",
        open: "Ask how much Python the job involves. Also confirm eligibility to work, language requirements and pay with Example Studio.",
        plan: "See the Python practice →",
      },
    },
    sessions: {
      sql: {
        title: "Test a SQL join",
        origin: "Both postings ask for SQL. Start from the order and payment records Ellen already knows.",
        task: "Create two orders: one for 30, one for 20. Give the first two payments of 10 and 20; leave the second unpaid. Join the tables and total the payments per order.",
        output: "Keep the query and a table of expected and actual totals. Explain how you kept the unpaid order in the result.",
        check: "The paid amounts should be 30 and 0. If the second order disappeared, inspect the join before trusting the total.",
      },
      python: {
        title: "Flag a mismatched payment",
        origin: "The Software Tester posting mentions Python. A short exercise gives Ellen a starting point for checking her skills.",
        task: "Write a function that compares an order amount with the sum of its payments. Try an exact match (30 against 10 + 20), an underpayment (20 against 15) and an unpaid order for 20.",
        output: "Keep the function and three small tests with the expected and actual differences.",
        check: "The unpaid balances should be 0, 5 and 20 respectively. The function should flag only the last two orders for review.",
      },
    },
  },
  uk: {
    skip: "Перейти до вмісту",
    caseLabel: "Інтерактивний приклад",
    title: "Вакансії для Еллен",
    lead: "Як за одним рядком у CV знайти дві вакансії для розгляду й скласти план навчання на тиждень? Перегляньте вигаданий приклад Еллен.",
    navMatches: "Вакансії",
    navPlan: "План на тиждень",
    profileLabel: "Профіль кандидатки",
    name: "Еллен Екзампл",
    target: "Шукає роботу QA Engineer у Польщі",
    quote: "«Звіряла суми замовлень із записами про оплату за допомогою SQL-запитів».",
    quoteSource: "З вигаданого CV Еллен",
    matchesTitle: "Розгляньте вакансії",
    matchesLead: "Оберіть вакансію, щоб побачити причину збігу й запитання, які Еллен варто поставити роботодавцю.",
    qaCity: "Варшава, Польща",
    testerCity: "Польща",
    matchReason: "Чому вакансія підійшла для розгляду",
    cvEvidence: "Що відомо з CV",
    toVerify: "Що ще треба уточнити",
    planTitle: "Сплануйте тиждень практики",
    planLead: "Цього тижня Еллен має три години. На кожну вимогу з вакансій вона виділяє 90 хвилин і виконує вправу з результатом, який можна перевірити.",
    sessionOne: "Заняття 01 · 90 хв",
    sessionTwo: "Заняття 02 · 90 хв",
    sqlSummary: "Звірити суми замовлень",
    pythonSummary: "Перевірити записи про оплату",
    assignment: "Завдання",
    output: "Що зберегти",
    check: "Як перевірити результат",
    nextLabel: "Власний робочий простір",
    nextTitle: "Спробуйте зі своїм CV",
    nextBody: "Запустіть Career Starter на своєму комп’ютері, щоб імпортувати CV, шукати вакансії та зберігати особистий план навчання.",
    setupLink: "Інструкція на GitHub",
    jobs: {
      qa: {
        kind: "Точний збіг назви",
        reason: "Example Shop шукає QA Engineer у Варшаві. Назва посади точно відповідає цілі Еллен, а в описі є вимога володіти SQL.",
        evidence: "Еллен описала, як звіряла суми замовлень з оплатами. Це конкретний приклад використання SQL, про який вона може розповісти на співбесіді.",
        open: "Уточнити, чи може компанія найняти Еллен у Польщі, які мови використовує команда і яку зарплату пропонує роботодавець.",
        plan: "До практики SQL →",
      },
      tester: {
        kind: "Споріднена назва посади",
        reason: "Software Tester — одна з назв професії, яку шукає Еллен. У вигаданій вакансії згадано Польщу, а серед вимог є SQL та Python.",
        evidence: "У CV є конкретний приклад використання SQL. Про Python у ньому нічого не сказано, тому досвід Еллен із цією мовою ще потрібно з’ясувати.",
        open: "Запитати, скільки в цій ролі роботи з Python. Також уточнити в Example Studio умови працевлаштування, мовні вимоги й оплату.",
        plan: "До практики Python →",
      },
    },
    sessions: {
      sql: {
        title: "Перевірити SQL JOIN",
        origin: "Для обох вакансій потрібен SQL. Еллен починає з уже знайомих їй замовлень та оплат.",
        task: "Створіть два замовлення на 30 і 20. Для першого додайте дві оплати на 10 і 20, друге залиште неоплаченим. Об’єднайте таблиці й порахуйте оплачену суму для кожного замовлення.",
        output: "Збережіть запит і таблицю очікуваних та фактичних сум. Поясніть, як у результаті збереглося неоплачене замовлення.",
        check: "Оплачені суми мають дорівнювати 30 і 0. Якщо друге замовлення зникло, перевірте умову об’єднання таблиць.",
      },
      python: {
        title: "Знайти розбіжність в оплаті",
        origin: "У вакансії Software Tester є вимога володіти Python. Коротка вправа допоможе Еллен перевірити свої навички.",
        task: "Напишіть функцію, що звіряє суму замовлення з оплатами. Перевірте повну оплату (30 проти 10 + 20), часткову оплату (20 проти 15) і неоплачене замовлення на 20.",
        output: "Збережіть функцію й три невеликі тести з очікуваною та фактичною різницею.",
        check: "Неоплачені залишки мають дорівнювати 0, 5 і 20 відповідно. Функція має позначити для перевірки лише останні два замовлення.",
      },
    },
  },
};

const byId = (id) => document.getElementById(id);
let language, job, practice;

function readLocation() {
  const params = new URLSearchParams(location.search);
  language = params.get("lang") === "uk" ? "uk" : "en";
  job = params.get("job") === "tester" ? "tester" : "qa";
  practice = params.get("practice") === "python" ? "python" : "sql";
  render();
}

function selectedUrl() {
  const url = new URL(location.href);
  url.searchParams.set("lang", language);
  url.searchParams.set("job", job);
  url.searchParams.set("practice", practice);
  return url;
}

function render() {
  const strings = copy[language];
  document.documentElement.lang = language;
  document.title = strings.title + " · Career Starter";
  document.querySelectorAll("[data-copy]").forEach((node) => {
    node.textContent = strings[node.dataset.copy];
  });
  const detail = strings.jobs[job];
  const roleButton = byId("job-" + job);
  byId("match-kind").textContent = detail.kind;
  byId("match-title").textContent = roleButton.querySelector("strong").textContent;
  byId("match-company").textContent = roleButton.querySelector(".small-label").textContent +
    " · " + roleButton.querySelector(".choice-meta").textContent;
  byId("match-reason").textContent = detail.reason;
  byId("match-evidence").textContent = detail.evidence;
  byId("match-open").textContent = detail.open;
  const planUrl = selectedUrl();
  planUrl.searchParams.set("practice", job === "qa" ? "sql" : "python");
  planUrl.hash = "plan";
  byId("view-plan").href = planUrl.href;
  byId("view-plan").textContent = detail.plan;
  const session = strings.sessions[practice];
  byId("practice-kind").textContent = practice === "sql" ? strings.sessionOne : strings.sessionTwo;
  for (const key of ["title", "origin", "task", "output", "check"]) {
    byId("practice-" + key).textContent = session[key];
  }
  for (const [group, value] of [["language", language], ["job", job], ["practice", practice]]) {
    document.querySelectorAll("button[id^='" + group + "-']").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.id === group + "-" + value));
    });
  }
  byId("setup-link").href = language === "uk"
    ? "https://github.com/i5adovyi/career-starter/blob/main/README.uk.md#почати"
    : "https://github.com/i5adovyi/career-starter#get-started";
}

function choose(id, updateSelection) {
  byId(id).addEventListener("click", () => {
    updateSelection();
    history.replaceState(null, "", selectedUrl());
    render();
  });
}
for (const key of ["en", "uk"]) choose("language-" + key, () => { language = key; });
for (const key of ["qa", "tester"]) choose("job-" + key, () => { job = key; });
for (const key of ["sql", "python"]) choose("practice-" + key, () => { practice = key; });

window.addEventListener("popstate", readLocation);
readLocation();
