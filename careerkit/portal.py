"""Local onboarding and dashboard; private documents never become static assets."""

from __future__ import annotations

import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import cv
from .workspace import private, read_json


def state(root: Path) -> dict:
    profile = read_json(private(root, "profile.json"), {})
    market = read_json(private(root, "jobs.json"), {})
    applications = []
    base = private(root, "applications")
    if base.exists():
        for directory in sorted(base.iterdir()):
            if not directory.is_dir():
                continue
            try:
                directory = cv.folder(root, directory.name)
                saved = read_json(directory / "state.json")
                job = read_json(directory / "job.json")
                try:
                    cv.check(root, directory.name)
                    readiness = "Approved for export"
                except (ValueError, FileNotFoundError):
                    readiness = "Review or approval needed"
                applications.append({"id": directory.name, "stage": saved["stage"],
                                     "title": job.get("title", ""), "company": job.get("company", ""),
                                     "readiness": readiness})
            except (ValueError, KeyError, OSError):
                applications.append({"id": directory.name, "stage": "needs repair"})
    plan = private(root, "learning-plan.md")
    return {
        "onboarded": bool(profile.get("confirmed")),
        "target_roles": profile.get("target_roles", []),
        "locations": profile.get("locations", []),
        "jobs": market.get("jobs", []), "sources": market.get("sources", []),
        "search_status": market.get("status", "not_started"),
        "searched_at": market.get("searched_at"), "applications": applications,
        "learning_plan": plan.read_text(encoding="utf-8") if plan.exists() else "",
    }


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Career Starter</title>
<meta name="csrf-token" content="__CSRF_TOKEN__">
<script>
let theme=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
try{const saved=localStorage.getItem('career-starter.theme');if(saved==='dark'||saved==='light')theme=saved;}catch{}
document.documentElement.dataset.theme=theme;
</script>
<style>
:root{color-scheme:light;--bg:#f3f6f4;--surface:#fff;--text:#183245;--muted:#536c62;--border:#cddad4;--control-border:#81998c;--accent:#3c705e;--link:#16664d;--tag:#eaf1ed;--warning-bg:#fff5dc;--warning-text:#855610;--button:#194e3d;--button-hover:#286f59;--button-text:#fff;--code:#e9f0eb;--intro:#173f36;--intro-text:#fff;--intro-code:#285148;--intro-code-text:#daf5d7;--focus:#397f61;font-family:system-ui,sans-serif;color:var(--text);background:var(--bg)}
:root[data-theme="dark"]{color-scheme:dark;--bg:#101916;--surface:#192620;--text:#e4eee8;--muted:#a5b9ad;--border:#35483d;--control-border:#708e7c;--accent:#91c6a9;--link:#95d9b4;--tag:#283d31;--warning-bg:#3b301c;--warning-text:#f1ce88;--button:#9bd6b5;--button-hover:#b4e4c7;--button-text:#10271b;--code:#253b2e;--intro:#1c3d2d;--intro-text:#edf7ef;--intro-code:#2b4e38;--intro-code-text:#d3edc8;--focus:#a4e0bc}
*{box-sizing:border-box}body{max-width:1200px;margin:auto;padding:28px}
header{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;border-bottom:1px solid var(--border);padding-bottom:20px}
h1{font-size:32px;margin:0;letter-spacing:-1px}h2{font-size:20px}p{line-height:1.55}
.eyebrow{color:var(--accent);text-transform:uppercase;letter-spacing:2px;font-size:12px;font-weight:700}
.intro{background:var(--intro);color:var(--intro-text);padding:28px;border-radius:16px;margin:24px 0}
.intro h2{font-size:26px;margin-top:0}.intro code{color:var(--intro-code-text);background:var(--intro-code)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{background:var(--surface);border:1px solid var(--border);padding:20px;border-radius:12px}
.number{font-size:32px;font-weight:700}.muted{color:var(--muted);font-size:14px}
.list{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.tag{display:inline-block;background:var(--tag);border-radius:5px;padding:4px 8px;margin:2px;font-size:12px}
.warning{color:var(--warning-text);background:var(--warning-bg);padding:12px;border-radius:6px}
button{background:var(--button);color:var(--button-text);border:0;border-radius:8px;padding:11px 18px;cursor:pointer}
button:hover{background:var(--button-hover)}a{color:var(--link)}code{background:var(--code);padding:3px 5px;border-radius:4px;overflow-wrap:anywhere}
.header-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:flex-end}
.language-switch{display:flex;gap:3px;padding:3px;border:1px solid var(--control-border);border-radius:10px}
.language-switch button{background:transparent;color:var(--accent);padding:8px 11px}
.language-switch button:hover{background:var(--tag)}
.language-switch button[aria-pressed="true"]{background:var(--button);color:var(--button-text)}
#theme-toggle{display:flex;align-items:center;gap:8px;background:var(--surface);color:var(--text);border:1px solid var(--control-border);padding:9px 12px}
#theme-toggle:hover{background:var(--tag)}#theme-toggle svg{width:17px;height:17px}
.theme-sun{display:none}:root[data-theme="dark"] .theme-sun{display:block}:root[data-theme="dark"] .theme-moon{display:none}
button:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
pre{white-space:pre-wrap;line-height:1.6;overflow-wrap:anywhere;font:14px/1.7 system-ui,sans-serif}
.section{margin-top:32px}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
input{padding:10px;border:1px solid var(--control-border);border-radius:8px;min-width:240px;background:var(--surface);color:var(--text)}
input::placeholder{color:var(--muted);opacity:1}
textarea,select{font:inherit;padding:12px;border:1px solid var(--control-border);border-radius:8px;background:var(--surface);color:var(--text);width:100%}
textarea{resize:vertical;line-height:1.6}textarea::placeholder{color:var(--muted)}
textarea:focus-visible,select:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
[hidden]{display:none!important}button:disabled{opacity:.6;cursor:wait}
.wizard{max-width:900px;margin:24px auto;padding:28px}.wizard h2{margin:8px 0 12px;font-size:25px}
.steps{display:flex;list-style:none;padding:0;gap:10px;margin:0 0 28px;counter-reset:step}
.steps li{flex:1;color:var(--muted);border-top:3px solid var(--border);padding-top:12px;font-size:13px}
.steps li::before{counter-increment:step;content:counter(step) ". ";font-weight:700}
.steps li[aria-current="step"]{border-color:var(--button);color:var(--text);font-weight:700}
fieldset{border:0;padding:0;margin:0;min-width:0}.field{display:grid;gap:8px;margin:20px 0}
.field>label,.field>legend{font-size:14px;font-weight:600}.field input:not([type="checkbox"]){width:100%;min-width:0;font:inherit}
.field small{color:var(--muted);line-height:1.5}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:0 22px}
.choices{display:flex;flex-wrap:wrap;gap:12px}.choice{display:flex;align-items:center;gap:8px;font-size:14px;line-height:1.6;cursor:pointer}
input[type="checkbox"]{min-width:0;width:18px;height:18px;accent-color:var(--button);flex-shrink:0}
.upload-box{border:1px dashed var(--control-border);padding:20px;border-radius:12px;background:var(--bg)}
.upload-box input{width:100%;min-width:0;background:transparent;border:0;padding:8px 0}
input[type="file"]::file-selector-button{font:inherit;background:var(--button);color:var(--button-text);border:0;border-radius:6px;padding:10px 14px;margin-right:12px;cursor:pointer}
.wizard-actions{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;border-top:1px solid var(--border);margin-top:28px;padding-top:20px}
.secondary{background:var(--surface);border:1px solid var(--control-border);color:var(--text)}.secondary:hover{background:var(--tag)}
.saved{font-size:12px;color:var(--muted);margin:12px 0 0}.error{color:var(--warning-text);background:var(--warning-bg);padding:14px;border-radius:8px;white-space:pre-wrap}
details{margin:18px 0}summary{cursor:pointer;color:var(--link);line-height:1.6}
.review-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.review-item{padding:14px;border:1px solid var(--border);border-radius:8px}
.review-item strong{display:block;font-size:13px;color:var(--muted);margin-bottom:8px}.review-item p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.cv-preview{max-height:280px;overflow:auto;padding:16px;background:var(--bg);border-radius:8px}
.search-actions{margin-top:18px}.search-actions button{background:var(--button);color:var(--button-text)}
.search-message{margin:10px 0 0;white-space:pre-wrap}
footer{margin:32px 0;color:var(--muted);font-size:13px}
@media(max-width:700px){.grid,.list,.two-col,.review-grid{grid-template-columns:1fr}body{padding:16px}header{align-items:flex-start;flex-direction:column}.header-actions{justify-content:flex-start}.wizard{padding:20px}.steps{gap:7px}.steps li{font-size:12px}}
</style></head><body>
<header><div><div class="eyebrow" data-i18n="eyebrow">Local career workspace</div><h1>Career Starter</h1></div>
<div class="header-actions"><div class="language-switch" role="group" aria-label="Language" data-i18n-label="language">
<button id="language-en" type="button" lang="en" aria-label="English" aria-pressed="true">EN</button>
<button id="language-uk" type="button" lang="uk" aria-label="Українська" aria-pressed="false">УК</button>
</div><button id="theme-toggle" type="button">
<svg class="theme-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.5 14.5A9 9 0 0 1 9.5 3.5a9 9 0 1 0 11 11Z"/></svg>
<svg class="theme-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>
<span id="theme-label">Dark theme</span></button>
<button id="refresh" type="button" data-i18n="refresh">Refresh</button></div></header>
<section class="intro"><h2 id="welcome">Loading…</h2><p id="next"></p>
<div class="search-actions" id="search-actions" hidden><button id="start-search" type="button" data-i18n="startSearch">Find jobs</button>
<p class="search-message" id="search-message" role="status" aria-live="polite"></p></div></section>
<section class="wizard card" id="wizard" hidden aria-label="Onboarding" data-i18n-label="onboardingLabel">
<ol class="steps"><li data-i18n="stepCV">Your CV</li><li data-i18n="stepWork">Your next role</li><li data-i18n="stepLearn">Skills & learning</li><li data-i18n="stepReview">Review & search</li></ol>
<form id="onboarding-form" novalidate>
<fieldset data-step="0">
<h2 tabindex="-1" data-i18n="cvTitle">Let's start with your experience</h2>
<p class="muted" data-i18n="cvIntro">Upload your CV, or paste a description of your work, education and projects. You can edit the text before confirming it.</p>
<div class="upload-box"><label for="cv-file" data-i18n="uploadCV">Upload your CV</label>
<input id="cv-file" type="file" accept=".pdf,.docx,.txt,.md">
<small class="muted" data-i18n="fileHelp">PDF, DOCX, TXT or Markdown · up to 20 MiB · stored on this computer</small></div>
<p id="upload-status" role="status" class="muted"></p>
<div class="field"><label for="cv-text" data-i18n="cvText">Your CV text</label>
<textarea id="cv-text" rows="10" maxlength="200000" required data-i18n-placeholder="cvPlaceholder" placeholder="Paste or review your experience here…"></textarea>
<small data-i18n="cvHelp">Check names, dates and responsibilities. Fix extraction errors and remove anything you do not want to use.</small></div>
</fieldset>
<fieldset data-step="1" hidden>
<h2 tabindex="-1" data-i18n="workTitle">What would you like to do next?</h2>
<p class="muted" data-i18n="workIntro">Choose roles you would consider now. Use titles that employers use in their job listings.</p>
<div class="two-col">
<div class="field"><label for="target-roles" data-i18n="targetRoles">Target job titles</label><input id="target-roles" required maxlength="2000" data-i18n-placeholder="rolesPlaceholder" placeholder="e.g. Customer Support, Office Administrator"><small data-i18n="listHelp">Separate items with commas or new lines.</small></div>
<div class="field"><label for="locations" data-i18n="locationsLabel">Countries or cities</label><input id="locations" required maxlength="2000" data-i18n-placeholder="locationsPlaceholder" placeholder="e.g. Poland, Warsaw"><small data-i18n="locationHelp">Remote jobs may still have country restrictions. We will flag unverified eligibility.</small></div>
</div>
<div class="field"><span id="work-modes-label" data-i18n="workModes">Working arrangement</span><div class="choices" role="group" aria-labelledby="work-modes-label">
<label class="choice"><input type="checkbox" name="work-mode" value="remote"><span data-i18n="remote">Remote</span></label>
<label class="choice"><input type="checkbox" name="work-mode" value="hybrid"><span data-i18n="hybrid">Hybrid</span></label>
<label class="choice"><input type="checkbox" name="work-mode" value="onsite"><span data-i18n="onsite">On site</span></label></div></div>
<details><summary data-i18n="morePreferences">More preferences (optional)</summary>
<div class="two-col">
<div class="field"><label for="seniority" data-i18n="seniorityLabel">Experience level</label><input id="seniority" maxlength="2000" placeholder="junior, middle, senior"></div>
<div class="field"><label for="keywords" data-i18n="keywordsLabel">Useful keywords</label><input id="keywords" maxlength="2000"></div>
<div class="field"><label for="excluded-keywords" data-i18n="excludeLabel">Terms to exclude</label><input id="excluded-keywords" maxlength="2000"></div>
<div class="field"><label for="salary-min" data-i18n="salaryLabel">Minimum salary (optional)</label><input id="salary-min" type="number" min="0" step="any"></div>
<div class="field"><label for="salary-currency" data-i18n="currencyLabel">Currency</label><input id="salary-currency" maxlength="10" placeholder="EUR"></div>
<div class="field"><label for="salary-period" data-i18n="periodLabel">Salary period</label><select id="salary-period"><option value="" data-i18n="notSpecified">Not specified</option><option value="year" data-i18n="perYear">Year</option><option value="month" data-i18n="perMonth">Month</option><option value="hour" data-i18n="perHour">Hour</option></select></div>
</div></details>
</fieldset>
<fieldset data-step="2" hidden>
<h2 tabindex="-1" data-i18n="learnTitle">Build on what you already know</h2>
<p class="muted" data-i18n="learnIntro">Share your current skills and a realistic study budget. Unlisted skills will stay unknown, not be treated as missing.</p>
<div class="two-col">
<div class="field"><label for="skills" data-i18n="skillsLabel">Skills you already use (optional)</label><textarea id="skills" rows="3" maxlength="4000"></textarea></div>
<div class="field"><label for="languages" data-i18n="languagesLabel">Languages you can work in (optional)</label><input id="languages" maxlength="2000" data-i18n-placeholder="languagesPlaceholder" placeholder="e.g. English, Ukrainian"></div>
<div class="field"><label for="weekly-hours" data-i18n="hoursLabel">Hours per week for learning</label><input id="weekly-hours" type="number" required min="0" max="80" step="0.5" value="3"><small data-i18n="hoursHelp">Zero is fine — focus on jobs using your current skills.</small></div>
<div class="field"><label for="learning-language" data-i18n="planLanguage">Learning-plan language</label><select id="learning-language"><option value="en">English</option><option value="uk">Українська</option></select></div>
</div>
<div class="field"><label for="learning-goals" data-i18n="goalsLabel">What would you like to learn? (optional)</label><textarea id="learning-goals" rows="3" maxlength="2000"></textarea><small data-i18n="goalsHelp">Up to three topics, one per line. Your assistant can refine the plan after reviewing vacancies.</small></div>
</fieldset>
<fieldset data-step="3" hidden>
<h2 tabindex="-1" data-i18n="reviewTitle">Check your profile, then find jobs</h2>
<p class="muted" data-i18n="reviewIntro">Your answers will become your local profile. Go back to change anything before confirming.</p>
<div id="profile-summary" class="review-grid"></div>
<details><summary data-i18n="reviewCV">Review your CV text</summary><pre class="cv-preview" id="review-cv"></pre></details>
<div class="field"><span id="feeds-label" data-i18n="sources">Sources</span><div class="choices" role="group" aria-labelledby="feeds-label">
<label class="choice"><input type="checkbox" name="feed" value="arbeitnow" checked>Arbeitnow</label>
<label class="choice"><input type="checkbox" name="feed" value="remotive" checked>Remotive</label></div>
<small id="preserved-sources" hidden></small>
<small data-i18n="feedsHelp">A starting selection of public European and remote listings, not the whole market. Your CV is not sent to these sources.</small></div>
<label class="choice"><input id="confirm-profile" type="checkbox"><span data-i18n="confirmation">I have reviewed my CV text and preferences. They accurately describe my experience and what I want to search for.</span></label>
</fieldset>
<p class="error" id="wizard-error" role="alert" hidden></p>
<div class="wizard-actions"><button id="wizard-back" type="button" class="secondary" data-i18n="back">Back</button><span id="step-count" class="muted"></span><button id="wizard-next" type="submit" data-i18n="continue">Save & continue</button></div>
<p id="draft-status" class="saved" role="status" aria-live="polite"></p>
</form></section>
<div id="dashboard" hidden>
<div class="grid"><div class="card"><div class="muted" data-i18n="jobCount">Jobs to review</div><div class="number" id="job-count">—</div></div>
<div class="card"><div class="muted" data-i18n="appCount">Applications</div><div class="number" id="app-count">—</div></div>
<div class="card"><div class="muted" data-i18n="search">Search</div><div id="search-status"></div></div></div>
<section class="section"><h2 data-i18n="sources">Sources</h2><div id="sources"></div></section>
<section class="section"><div class="row"><h2 data-i18n="jobs">Jobs</h2><input id="filter" aria-label="Filter jobs" placeholder="Job title or company" data-i18n-label="filterLabel" data-i18n-placeholder="filterPlaceholder"></div>
<p class="muted" data-i18n="matchNote">A keyword match is a reason to review a job. Check its terms, country, work authorization and availability.</p><div class="list" id="jobs"></div></section>
<section class="section"><h2 data-i18n="applications">Application preparation</h2><div class="list" id="applications"></div></section>
<section class="section"><h2 data-i18n="learning">Learning plan</h2><pre class="card" id="plan"></pre></section>
</div>
<footer data-i18n="footer">Your data stays in local/. Use Codex / Claude Code or the CLI for actions. This page does not submit applications.
Text read by your assistant is processed according to its provider settings.</footer>
<script>
const messages={
 en:{
  eyebrow:'Local career workspace',language:'Language',refresh:'Refresh',loading:'Loading…',
  darkTheme:'Dark theme',lightTheme:'Light theme',
  jobCount:'Jobs to review',appCount:'Applications',search:'Search',sources:'Sources',jobs:'Jobs',
  applications:'Application preparation',learning:'Learning plan',filterLabel:'Filter jobs',filterPlaceholder:'Job title or company',
  matchNote:'A keyword match is a reason to review a job. Check its terms, country, work authorization and availability.',
  footer:'Your data stays in local/. Use Codex / Claude Code or the CLI for actions. This page does not submit applications. Text read by your assistant is processed according to its provider settings.',
  welcome:'Start with your CV',nextStep:'Your next step',
  onboarding:'Put your CV in local/inbox/ and ask your assistant: “Read AGENTS.md and guide me through onboarding in English.”',
  noSources:'No sources have been checked yet.',unknownLocation:'Location unknown',openJob:'Open job',
  prepare:'Prepare with your assistant:',noJobs:'No jobs to show. Check sources and criteria, or import jobs found with your assistant.',
  noApplications:'Prepare an application with your assistant after choosing a job.',
  noPlan:'After onboarding, run python career.py learn. Your assistant will refine the exercises and completion criteria.',
  loadError:'Could not read local data',
  statuses:{not_started:'Not started',not_configured:'No feeds configured',ok:'Up to date',cached:'Cached',partial:'Some sources failed',failed:'Failed',warning:'Needs review'},
  stages:{preparing:'Preparing',applied:'Applied',interview:'Interview',offer:'Offer',accepted:'Accepted',rejected:'Rejected',withdrawn:'Withdrawn','needs repair':'Needs repair'},
  readiness:{'Approved for export':'Approved for export','Review or approval needed':'Review or approval needed'}
 },
 uk:{
  eyebrow:'Локальний кар’єрний простір',language:'Мова',refresh:'Оновити',loading:'Завантаження…',
  darkTheme:'Темна тема',lightTheme:'Світла тема',
  jobCount:'Вакансії для перегляду',appCount:'Заявки',search:'Пошук',sources:'Джерела',jobs:'Вакансії',
  applications:'Підготовка заявок',learning:'Навчальний план',filterLabel:'Фільтр вакансій',filterPlaceholder:'Назва або компанія',
  matchNote:'Збіг за ключовими словами — привід переглянути вакансію. Перевір умови, країну, право на роботу та актуальність.',
  footer:'Дані залишаються в local/. Робочі дії виконуй через Codex / Claude Code або CLI. Сторінка не надсилає заявки. Під час роботи асистента прочитані ним дані обробляються за налаштуваннями його провайдера.',
  welcome:'Почни зі свого CV',nextStep:'Твій наступний крок',
  onboarding:'Поклади CV в local/inbox/ і попроси асистента: «Прочитай AGENTS.md і проведи мене через онбординг українською».',
  noSources:'Джерела ще не запускались.',unknownLocation:'Локацію не вказано',openJob:'Відкрити вакансію',
  prepare:'Підготувати з асистентом:',noJobs:'Немає вакансій для показу. Перевір джерела та критерії або імпортуй знайдені з асистентом вакансії.',
  noApplications:'Обери вакансію та підготуй заявку разом з асистентом.',
  noPlan:'Після онбордингу: python career.py learn. Асистент уточнить вправи та критерії виконання.',
  loadError:'Не вдалося прочитати локальні дані',
  statuses:{not_started:'Ще не запускався',not_configured:'Фіди не налаштовано',ok:'Дані отримано',cached:'Із кешу',partial:'Частина джерел недоступна',failed:'Помилка',warning:'Потрібна перевірка'},
  stages:{preparing:'Підготовка',applied:'Подано',interview:'Співбесіда',offer:'Пропозиція',accepted:'Прийнято',rejected:'Відмова',withdrawn:'Відкликано','needs repair':'Потрібне виправлення'},
  readiness:{'Approved for export':'Підтверджено для експорту','Review or approval needed':'Потрібна перевірка або підтвердження'}
 }
};
const ukrainianSignals={
 'Work mode is unknown; verify remote, hybrid, or onsite conditions':'Формат роботи невідомий; перевір дистанційні, гібридні або офісні умови',
 'Geography is unverified; confirm hiring country and location restrictions':'Географію не перевірено; уточни країну найму та обмеження локації',
 'Work authorization and employer hiring eligibility are unverified':'Право на роботу та можливість найму роботодавцем не перевірено',
 'Language requirements and proficiency are unverified':'Мовні вимоги та відповідність рівня не перевірено',
 'Seniority is not explicit in the title':'Рівень досвіду не вказано в назві',
 'Published salary ceiling meets configured minimum':'Верхня межа опублікованої зарплати відповідає заданому мінімуму',
 'Confirm salary range, gross/net basis, and contract before applying':'Перед подачею уточни вилку зарплати, суму до чи після податків і тип договору',
 'Salary is unknown or not comparable; no currency or period conversion assumed':'Зарплата невідома або непорівнювана; валюту й період не перераховано',
 'Source failed; retained from an earlier run, availability unverified':'Джерело недоступне; збережено попередній результат, актуальність не перевірено'
};
const ukrainianPrefixes={'Title matches: ':'Збіг назви: ','Keywords found: ':'Знайдені ключові слова: ','Location text matches: ':'Збіг локації: '};
Object.assign(messages.en,{
 onboardingLabel:'Onboarding',stepCV:'Your CV',stepWork:'Your next role',stepLearn:'Skills & learning',stepReview:'Review & search',
 cvTitle:"Let's start with your experience",cvIntro:'Upload your CV, or paste a description of your work, education and projects. You can edit the text before confirming it.',
 uploadCV:'Upload your CV',fileHelp:'PDF, DOCX, TXT or Markdown · up to 20 MiB · stored on this computer',cvText:'Your CV text',cvPlaceholder:'Paste or review your experience here…',
 cvHelp:'Check names, dates and responsibilities. Fix extraction errors and remove anything you do not want to use.',
 workTitle:'What would you like to do next?',workIntro:'Choose roles you would consider now. Use titles that employers use in their job listings.',
 targetRoles:'Target job titles',rolesPlaceholder:'e.g. Customer Support, Office Administrator',listHelp:'Separate items with commas or new lines.',
 locationsLabel:'Countries or cities',locationsPlaceholder:'e.g. Poland, Warsaw',locationHelp:'Remote jobs may still have country restrictions. We will flag unverified eligibility.',
 workModes:'Working arrangement',remote:'Remote',hybrid:'Hybrid',onsite:'On site',morePreferences:'More preferences (optional)',
 seniorityLabel:'Experience level',keywordsLabel:'Useful keywords',excludeLabel:'Terms to exclude',salaryLabel:'Minimum salary (optional)',currencyLabel:'Currency',periodLabel:'Salary period',
 notSpecified:'Not specified',perYear:'Year',perMonth:'Month',perHour:'Hour',
 learnTitle:'Build on what you already know',learnIntro:'Share your current skills and a realistic study budget. Unlisted skills will stay unknown, not be treated as missing.',
 skillsLabel:'Skills you already use (optional)',languagesLabel:'Languages you can work in (optional)',languagesPlaceholder:'e.g. English, Ukrainian',
 hoursLabel:'Hours per week for learning',hoursHelp:'Zero is fine — focus on jobs using your current skills.',planLanguage:'Learning-plan language',
 goalsLabel:'What would you like to learn? (optional)',goalsHelp:'Up to three topics, one per line. Your assistant can refine the plan after reviewing vacancies.',
 reviewTitle:'Check your profile, then find jobs',reviewIntro:'Your answers will become your local profile. Go back to change anything before confirming.',
 reviewCV:'Review your CV text',feedsHelp:'A starting selection of public European and remote listings, not the whole market. Your CV is not sent to these sources.',
 otherSources:'Other saved sources kept: ',
 confirmation:'I have reviewed my CV text and preferences. They accurately describe my experience and what I want to search for.',
 back:'Back',continue:'Save & continue',finish:'Confirm & find jobs',startSearch:'Find jobs',searchAgain:'Search again',searching:'Searching…',
 uploading:'Reading your CV…',uploadReady:'CV imported. Review and correct the text below.',pasteRequired:'The original file is saved, but readable text could not be extracted. Paste the CV text below, or upload a DOCX/TXT copy.',
 saving:'Saving on this computer…',saved:'Draft saved on this computer. You can come back later.',draftHint:'Your progress saves on this computer as you go.',unsaved:'Changes not saved yet.',stepOf:'Step {step} of 4',
 cvRequired:'Add your CV text or a short description of your experience before continuing.',rolesRequired:'Enter at least one job title and location.',modeRequired:'Choose at least one working arrangement.',
 salaryRequired:'For a minimum salary, choose both a currency and a period.',goalsLimit:'Choose up to three learning topics.',confirmRequired:'Review your CV and preferences, then tick the confirmation box.',feedsRequired:'Choose at least one source to start searching.',
 uploadLarge:'Choose a file of at most 20 MiB.',uploadType:'Choose a PDF, DOCX, TXT or Markdown file.',requestError:'Could not complete this step. Please try again.',
 searchRunning:'Searching the selected public sources. Your profile is saved; results will appear here.',
 searchFailed:'Some sources could not be reached. Your profile is saved. You can try the search again.',
 searchEmpty:'No matching jobs yet. You can retry later or ask your assistant to review your criteria and add other sources.',
 searchReady:'Review the jobs below with your assistant. Check location, eligibility and requirements before applying.',
 searchNotStarted:'Your profile is ready. Start a search when you are ready.',
 noPlan:'Your first search creates a learning-plan starting point. Your assistant can refine the exercises and completion criteria.',
 welcome:'A new chapter starts here',onboarding:'Four short steps: add your CV, choose your next role, set your learning priorities and find real job leads.',
 footer:'Your CV and answers are stored in local/ on this computer. Public job searches do not send your CV. Use your assistant to tailor CVs and refine the learning plan. This portal does not submit applications.'
});
Object.assign(messages.uk,{
 onboardingLabel:'Онбординг',stepCV:'Твоє CV',stepWork:'Бажана робота',stepLearn:'Навички й навчання',stepReview:'Перевірка й пошук',
 cvTitle:'Почнімо з твого досвіду',cvIntro:'Завантаж CV або встав опис роботи, освіти та проєктів. Перед підтвердженням текст можна відредагувати.',
 uploadCV:'Завантаж своє CV',fileHelp:'PDF, DOCX, TXT або Markdown · до 20 МіБ · зберігається на цьому комп’ютері',cvText:'Текст твого CV',cvPlaceholder:'Встав або перевір свій досвід тут…',
 cvHelp:'Перевір імена, дати й обов’язки. Виправ помилки розпізнавання та прибери зайві подробиці.',
 workTitle:'Яку роботу ти хочеш знайти?',workIntro:'Обери ролі, які готовий або готова розглядати зараз. Використовуй назви посад із вакансій роботодавців.',
 targetRoles:'Бажані посади',rolesPlaceholder:'Наприклад: Customer Support, Office Administrator',listHelp:'Розділяй значення комами або новими рядками.',
 locationsLabel:'Країни або міста',locationsPlaceholder:'Наприклад: Poland, Warsaw',locationHelp:'Дистанційна робота теж може мати обмеження за країною. Невідомі умови будуть позначені для перевірки.',
 workModes:'Формат роботи',remote:'Дистанційно',hybrid:'Гібридно',onsite:'В офісі',morePreferences:'Додаткові побажання (необов’язково)',
 seniorityLabel:'Рівень досвіду',keywordsLabel:'Корисні ключові слова',excludeLabel:'Слова для виключення',salaryLabel:'Мінімальна зарплата (необов’язково)',currencyLabel:'Валюта',periodLabel:'Період зарплати',
 notSpecified:'Не вказано',perYear:'Рік',perMonth:'Місяць',perHour:'Година',
 learnTitle:'Спираймося на те, що ти вже вмієш',learnIntro:'Вкажи наявні навички й реалістичний час на навчання. Невказана навичка залишиться невідомою — це не означає, що її немає.',
 skillsLabel:'Навички, які вже використовуєш (необов’язково)',languagesLabel:'Мови для роботи (необов’язково)',languagesPlaceholder:'Наприклад: English, Ukrainian',
 hoursLabel:'Годин на навчання щотижня',hoursHelp:'Можна вказати нуль і зосередитися на роботі з наявними навичками.',planLanguage:'Мова навчального плану',
 goalsLabel:'Чого хочеш навчитися? (необов’язково)',goalsHelp:'До трьох тем, кожна з нового рядка. Асистент уточнить план після перегляду вакансій.',
 reviewTitle:'Перевір профіль і знайди вакансії',reviewIntro:'Відповіді стануть твоїм локальним профілем. Повернися назад, якщо потрібно щось змінити.',
 reviewCV:'Переглянути текст CV',feedsHelp:'Початкова добірка публічних європейських і дистанційних вакансій, а не весь ринок. Твоє CV не надсилається цим джерелам.',
 otherSources:'Інші збережені джерела: ',
 confirmation:'Я перевірив або перевірила текст CV й побажання. Вони правильно описують мій досвід і бажану роботу.',
 back:'Назад',continue:'Зберегти й далі',finish:'Підтвердити й знайти роботу',startSearch:'Знайти вакансії',searchAgain:'Шукати ще раз',searching:'Шукаємо…',
 uploading:'Читаємо твоє CV…',uploadReady:'CV імпортовано. Перевір і виправ текст нижче.',pasteRequired:'Оригінал збережено, але текст не вдалося прочитати. Встав текст CV нижче або завантаж копію DOCX/TXT.',
 saving:'Зберігаємо на цьому комп’ютері…',saved:'Чернетку збережено на цьому комп’ютері. Можна повернутися пізніше.',draftHint:'Відповіді зберігатимуться на цьому комп’ютері під час заповнення.',unsaved:'Зміни ще не збережено.',stepOf:'Крок {step} із 4',
 cvRequired:'Додай текст CV або короткий опис досвіду.',rolesRequired:'Вкажи хоча б одну посаду й локацію.',modeRequired:'Обери хоча б один формат роботи.',
 salaryRequired:'Для мінімальної зарплати вкажи валюту та період.',goalsLimit:'Обери до трьох тем для навчання.',confirmRequired:'Перевір CV й побажання та познач підтвердження.',feedsRequired:'Обери хоча б одне джерело для пошуку.',
 uploadLarge:'Обери файл розміром до 20 МіБ.',uploadType:'Обери PDF, DOCX, TXT або Markdown.',requestError:'Не вдалося завершити цей крок. Спробуй ще раз.',
 searchRunning:'Шукаємо у вибраних публічних джерелах. Профіль збережено; результати з’являться тут.',
 searchFailed:'Частина джерел недоступна. Профіль збережено. Можна повторити пошук.',
 searchEmpty:'Відповідних вакансій поки немає. Спробуй пізніше або попроси асистента переглянути критерії та додати інші джерела.',
 searchReady:'Переглянь вакансії нижче разом з асистентом. Перед подачею перевір локацію, право на роботу та вимоги.',
 searchNotStarted:'Профіль готовий. Можна починати пошук.',
 noPlan:'Перший пошук створить основу навчального плану. Асистент допоможе уточнити вправи та критерії виконання.',
 welcome:'Тут починається новий етап',onboarding:'Чотири короткі кроки: додай CV, обери бажану роботу, визнач пріоритети навчання та знайди реальні вакансії.',
 footer:'CV та відповіді зберігаються в local/ на цьому комп’ютері. Публічний пошук не передає твоє CV джерелам вакансій. Асистент допоможе адаптувати CV й уточнити навчальний план. Портал не надсилає заявки.'
});
let language='en';
try{const saved=localStorage.getItem('career-starter.language');if(saved==='en'||saved==='uk')language=saved;}catch{}
let current=null,loadError='';
let draft=null,step=0,busy=false,uploading=false,saveTimer,searchTimer,saveQueue=Promise.resolve(),draftVersion=0,savedVersion=0,refreshing=null,starting=false,searchError='';
const el=id=>document.getElementById(id);
const t=key=>messages[language][key]??messages.en[key]??key;
const label=(group,value)=>t(group)[value]??value;
const node=(tag,text,cls)=>{const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n};
function signal(text){
 if(language==='en')return text;
 if(ukrainianSignals[text])return ukrainianSignals[text];
 for(const [prefix,translation] of Object.entries(ukrainianPrefixes)){
  if(text.startsWith(prefix))return translation+text.slice(prefix.length);
 }
 return text;
}
function jobs(){
 if(!current)return;
 const list=el('jobs');list.replaceChildren();const q=el('filter').value.toLowerCase();
 const filtered=current.jobs.filter(j=>(j.title+' '+j.company).toLowerCase().includes(q));
 for(const j of filtered){
  const card=node('article','','card');card.append(node('h3',j.title),node('p',j.company+' · '+(j.location||t('unknownLocation')),'muted'));
  for(const reason of j.reasons||[])card.append(node('span',signal(reason),'tag'));
  if((j.review_flags||[]).length)card.append(node('p',j.review_flags.map(signal).join(' · '),'warning'));
  try{const u=new URL(j.url);if(['http:','https:'].includes(u.protocol)&&!u.username&&!u.password){
   const a=node('a',t('openJob'));a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';card.append(a);}}catch{}
  card.append(node('p',t('prepare')),node('code','python career.py prepare '+j.id));
  list.append(card);
 }
 if(!filtered.length)list.append(node('p',t('noJobs'),'card'));
}
function render(){
 document.documentElement.lang=language;
 renderTheme();
 document.querySelectorAll('[data-i18n]').forEach(n=>n.textContent=t(n.dataset.i18n));
 document.querySelectorAll('[data-i18n-label]').forEach(n=>n.setAttribute('aria-label',t(n.dataset.i18nLabel)));
 document.querySelectorAll('[data-i18n-placeholder]').forEach(n=>n.placeholder=t(n.dataset.i18nPlaceholder));
 for(const code of ['en','uk'])el('language-'+code).setAttribute('aria-pressed',String(language===code));
 if(loadError){el('welcome').textContent=t('loadError');el('next').textContent=loadError;return;}
 if(!current){el('welcome').textContent=t('loading');return;}
 el('dashboard').hidden=!current.onboarded;
 el('wizard').hidden=current.onboarded||!draft;
 el('search-actions').hidden=!current.onboarded;
 el('welcome').textContent=current.onboarded?t('nextStep'):t('welcome');
 el('next').textContent=current.onboarded?current.target_roles.join(' · ')+' / '+current.locations.join(' · '):t('onboarding');
 el('job-count').textContent=current.jobs.length;el('app-count').textContent=current.applications.length;
 el('search-status').textContent=current.search_task?.status==='running'?t('searching'):label('statuses',current.search_status);
 el('sources').replaceChildren(...current.sources.map(s=>node('p',s.name+' — '+label('statuses',s.status)+' ('+(s.count||0)+')','tag')));
 if(!current.sources.length)el('sources').append(node('p',t('noSources'),'muted'));
 el('applications').replaceChildren(...current.applications.map(a=>{
 const card=node('article','','card');card.append(node('h3',a.title||a.id),node('p',a.company||''),node('span',label('stages',a.stage),'tag'),
 node('p',a.readiness?label('readiness',a.readiness):label('stages','needs repair'),'muted'),node('code','python career.py hash '+a.id));return card;
 }));
 if(!current.applications.length)el('applications').append(node('p',t('noApplications'),'muted'));
 el('plan').textContent=current.learning_plan||t('noPlan');
 jobs();
 renderWizard();
 renderSearch();
}
function setLanguage(value){
 language=value;
 try{localStorage.setItem('career-starter.language',language);}catch{}
 render();
}
function renderTheme(){
 document.documentElement.dataset.theme=theme;
 el('theme-label').textContent=t(theme==='dark'?'lightTheme':'darkTheme');
}
function toggleTheme(){
 theme=theme==='dark'?'light':'dark';
 try{localStorage.setItem('career-starter.theme',theme);}catch{}
 renderTheme();
}
async function api(path,payload){
 const options=payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(payload)};
 const response=await fetch(path,options);
 const data=await response.json();
 if(!response.ok)throw new Error(data.error||t('requestError'));
 return data;
}
const listValue=id=>el(id).value.split(/[,\n]/).map(x=>x.trim()).filter(Boolean);
const selected=name=>Array.from(document.querySelectorAll('input[name="'+name+'"]:checked'),n=>n.value);
function collectDraft(){
 const goalNames=el('learning-goals').value.split('\n').map(x=>x.trim()).filter(Boolean);
 return {
  step,cv_text:el('cv-text').value,target_roles:listValue('target-roles'),locations:listValue('locations'),
  work_modes:selected('work-mode'),languages:listValue('languages'),skills:listValue('skills'),seniority:listValue('seniority'),
  keywords:listValue('keywords'),excluded_keywords:listValue('excluded-keywords'),weekly_hours:Number(el('weekly-hours').value),
  learning_language:el('learning-language').value,
  learning_goals:goalNames.map(skill=>({skill,reason:(draft.learning_goals||[]).find(g=>g.skill===skill)?.reason||
   (el('learning-language').value==='uk'?'Тема, обрана кандидатом під час онбордингу.':'Candidate-selected learning topic during onboarding.')})),
  salary:{minimum:el('salary-min').value===''?null:Number(el('salary-min').value),currency:el('salary-currency').value.trim(),period:el('salary-period').value},
  sources:[...(draft.sources||[]).filter(s=>!['arbeitnow','remotive'].includes(s.type)),
   ...selected('feed').map(type=>({...((draft.sources||[]).find(s=>s.type===type)||{}),type,enabled:true}))]
 };
}
function fillDraft(){
 step=draft.step||0;
 el('cv-text').value=draft.cv_text||'';
 for(const [id,key] of Object.entries({'target-roles':'target_roles',locations:'locations',languages:'languages',skills:'skills',seniority:'seniority',keywords:'keywords','excluded-keywords':'excluded_keywords'})){
  el(id).value=(draft[key]||[]).join(', ');
 }
 document.querySelectorAll('input[name="work-mode"]').forEach(n=>n.checked=(draft.work_modes||[]).includes(n.value));
 document.querySelectorAll('input[name="feed"]').forEach(n=>n.checked=(draft.sources||[]).some(s=>s.type===n.value&&s.enabled!==false));
 el('weekly-hours').value=draft.weekly_hours??3;el('learning-language').value=draft.learning_language||language;
 el('learning-goals').value=(draft.learning_goals||[]).map(g=>g.skill).join('\n');
 el('salary-min').value=draft.salary?.minimum??'';el('salary-currency').value=draft.salary?.currency||'';
 el('salary-period').value=draft.salary?.period||'';
}
function showWizardError(error){
 el('wizard-error').textContent=error?error.message||String(error):'';
 el('wizard-error').hidden=!error;
}
function renderWizard(){
 if(!draft||current?.onboarded)return;
 document.querySelectorAll('fieldset[data-step]').forEach(n=>{n.hidden=Number(n.dataset.step)!==step;n.disabled=busy;});
 document.querySelectorAll('.steps li').forEach((n,i)=>i===step?n.setAttribute('aria-current','step'):n.removeAttribute('aria-current'));
 el('step-count').textContent=t('stepOf').replace('{step}',step+1);
 el('wizard-back').hidden=step===0;el('wizard-back').disabled=busy;
 el('wizard-next').disabled=busy;el('wizard-next').textContent=busy?t(uploading?'uploading':'saving'):t(step===3?'finish':'continue');
 el('draft-status').textContent=t(busy&&!uploading?'saving':draftVersion!==savedVersion?'unsaved':!draft.cv_text&&!draft.target_roles?.length?'draftHint':'saved');
 el('upload-status').textContent=uploading?t('uploading'):draft.extraction==='assistant_required'?t('pasteRequired'):draft.import_id?t('uploadReady'):'';
 if(step===3){
  const values=collectDraft();
  const pairs=[
   ['targetRoles',values.target_roles.join(', ')],['locationsLabel',values.locations.join(', ')],
   ['workModes',values.work_modes.map(t).join(', ')],['languagesLabel',values.languages.join(', ')],
   ['skillsLabel',values.skills.join(', ')],['hoursLabel',String(values.weekly_hours)],
   ['planLanguage',values.learning_language==='uk'?'Українська':'English'],['goalsLabel',values.learning_goals.map(g=>g.skill).join('\n')]
  ];
  if(values.seniority.length)pairs.push(['seniorityLabel',values.seniority.join(', ')]);
  if(values.keywords.length)pairs.push(['keywordsLabel',values.keywords.join(', ')]);
  if(values.excluded_keywords.length)pairs.push(['excludeLabel',values.excluded_keywords.join(', ')]);
  if(values.salary.minimum!==null)pairs.push(['salaryLabel',`${values.salary.minimum} ${values.salary.currency} / ${values.salary.period}`]);
  el('profile-summary').replaceChildren(...pairs.map(([key,value])=>{
   const item=node('div','','review-item');item.append(node('strong',t(key)),node('p',value||t('notSpecified')));return item;
  }));
  el('review-cv').textContent=values.cv_text;
  const others=values.sources.filter(s=>!['arbeitnow','remotive'].includes(s.type));
  el('preserved-sources').hidden=!others.length;
  el('preserved-sources').textContent=t('otherSources')+others.map(s=>s.type+(s.board?': '+s.board:'')).join(', ');
 }
}
function validateStep(index){
 const active=document.querySelector('fieldset[data-step="'+index+'"]');
 for(const control of active.querySelectorAll('input,textarea,select')){
  if(!control.checkValidity()){control.reportValidity();return false;}
 }
 const values=collectDraft();
 let error='';
 if(index===0&&!values.cv_text.trim())error='cvRequired';
 if(index===1){
  if(!values.target_roles.length||!values.locations.length)error='rolesRequired';
  else if(!values.work_modes.length)error='modeRequired';
  else if(values.salary.minimum!==null&&(!values.salary.currency||!values.salary.period))error='salaryRequired';
 }
 if(index===2&&values.learning_goals.length>3)error='goalsLimit';
 if(index===3){
  if(!values.sources.some(s=>s.enabled!==false))error='feedsRequired';
  else if(!el('confirm-profile').checked)error='confirmRequired';
 }
 if(error){showWizardError(new Error(t(error)));return false;}
 return true;
}
async function saveDraft(){
 clearTimeout(saveTimer);
 const value=collectDraft(),version=draftVersion;
 const saving=saveQueue.catch(()=>{}).then(()=>api('/api/onboarding',{...value,draft_sha256:draft.draft_sha256}));
 saveQueue=saving;
 const result=await saving;
 draft=result;savedVersion=version;
 renderWizard();
 return result;
}
function changedDraft(event){
 if(event.target.id==='cv-file'||event.target.id==='confirm-profile'||busy)return;
 draftVersion++;el('confirm-profile').checked=false;showWizardError(null);renderWizard();
 clearTimeout(saveTimer);
 saveTimer=setTimeout(()=>saveDraft().catch(showWizardError),900);
}
async function moveStep(direction){
 if(busy)return;
 showWizardError(null);
 if(direction>0&&!validateStep(step))return;
 busy=true;renderWizard();
 const oldStep=step;
 try{
  step=Math.max(0,Math.min(3,step+direction));draftVersion++;
  await saveDraft();
 }catch(error){step=oldStep;showWizardError(error);}
 finally{busy=false;renderWizard();}
 document.querySelector('fieldset[data-step="'+step+'"] h2').focus();
}
async function finishOnboarding(){
 if(busy||!validateStep(3))return;
 busy=true;showWizardError(null);renderWizard();
 try{
  const saved=await saveDraft();
  await api('/api/onboarding/complete',{confirmed:true,draft_sha256:saved.draft_sha256});
  draft={onboarded:true};
  await refresh(true);
  await startSearch();
 }catch(error){showWizardError(error);}
 finally{busy=false;renderWizard();}
}
async function uploadCV(){
 const file=el('cv-file').files[0];if(!file||busy)return;
 showWizardError(null);
 if(file.size>20*1024*1024){showWizardError(new Error(t('uploadLarge')));return;}
 if(!/\.(pdf|docx|txt|md)$/i.test(file.name)){showWizardError(new Error(t('uploadType')));return;}
 busy=true;uploading=true;renderWizard();
 try{
  await saveDraft();
  const content=await new Promise((resolve,reject)=>{
   const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error(t('requestError')));reader.readAsDataURL(file);
  });
  draft=await api('/api/cv',{name:file.name,content});step=0;
  el('cv-text').value=draft.cv_text;draftVersion++;savedVersion=draftVersion;el('confirm-profile').checked=false;
 }catch(error){showWizardError(error);}
 finally{busy=false;uploading=false;el('cv-file').value='';renderWizard();}
}
function renderSearch(){
 if(!current?.onboarded)return;
 const task=current.search_task||{};
 const running=starting||task.status==='running';
 el('start-search').disabled=running;el('start-search').textContent=t(running?'searching':current.searched_at?'searchAgain':'startSearch');
 const status=current.search_status;
 el('search-message').textContent=searchError||t(running?'searchRunning':task.status==='failed'||status==='failed'||status==='partial'?'searchFailed':status==='not_started'?'searchNotStarted':current.jobs.length?'searchReady':'searchEmpty');
}
async function startSearch(){
 if(starting||current?.search_task?.status==='running')return;
 starting=true;searchError='';renderSearch();
 try{
  await api('/api/search',{});
  await refresh(true);
 }catch(error){searchError=t('requestError')+' '+error.message;}
 finally{starting=false;renderSearch();}
}
function refresh(afterMutation=false){
 if(refreshing)return afterMutation?refreshing.then(()=>refresh(true)):refreshing;
 clearTimeout(searchTimer);
 refreshing=(async()=>{
  try{
   current=await api('/api/state');
   if(!current.onboarded&&!draft){draft=await api('/api/onboarding');fillDraft();}
   loadError='';
  }catch(e){loadError=String(e);}
  render();
  if(current?.search_task?.status==='running')searchTimer=setTimeout(()=>refresh(),1200);
 })().finally(()=>{refreshing=null;});
 return refreshing;
}
el('refresh').addEventListener('click',()=>refresh());el('filter').addEventListener('input',jobs);
el('language-en').addEventListener('click',()=>setLanguage('en'));
el('language-uk').addEventListener('click',()=>setLanguage('uk'));
el('theme-toggle').addEventListener('click',toggleTheme);
el('onboarding-form').addEventListener('submit',event=>{event.preventDefault();step===3?finishOnboarding():moveStep(1);});
el('onboarding-form').addEventListener('input',changedDraft);
el('wizard-back').addEventListener('click',()=>moveStep(-1));
el('cv-file').addEventListener('change',uploadCV);
el('start-search').addEventListener('click',startSearch);
window.addEventListener('beforeunload',event=>{if(!current?.onboarded&&(busy||draftVersion!==savedVersion)){event.preventDefault();event.returnValue='';}});
render();refresh();
</script></body></html>"""


def handler(root: Path):
    from .onboarding import PortalSession

    session = PortalSession(root)
    csrf_token = secrets.token_urlsafe(32)
    max_body = 28 * 1024 * 1024

    class Handler(BaseHTTPRequestHandler):
        def allowed(self, *, writing=False):
            host = self.headers.get("Host", "")
            expected = f"127.0.0.1:{self.server.server_port}"
            origin = self.headers.get("Origin")
            return (
                host == expected
                and (origin == f"http://{expected}" if writing else origin in {None, f"http://{expected}"})
                and (not writing or secrets.compare_digest(
                    self.headers.get("X-CSRF-Token", "").encode("utf-8"), csrf_token.encode("utf-8")))
            )

        def respond(self, value, status=200, *, html=False):
            body = value.encode("utf-8") if html else json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.allowed():
                self.respond({"error": "Local portal access only."}, 403)
                return
            if self.path not in {"/", "/api/state", "/api/onboarding"}:
                self.respond({"error": "Not found."}, 404)
                return
            try:
                if self.path == "/":
                    self.respond(PAGE.replace("__CSRF_TOKEN__", csrf_token), html=True)
                elif self.path == "/api/onboarding":
                    self.respond(session.draft())
                else:
                    self.respond({**state(root), "search_task": session.task()})
            except (ValueError, OSError, KeyError):
                self.respond({"error": "Local workspace data needs repair. Ask your assistant to inspect it."}, 500)

        def do_POST(self):
            # Check origin and token before reading uploads or changing local files.
            if not self.allowed(writing=True):
                self.respond({"error": "Reload this local portal and try again."}, 403)
                return
            actions = {
                "/api/cv": session.upload,
                "/api/onboarding": session.save,
                "/api/onboarding/complete": session.complete,
                "/api/search": session.start_search,
            }
            if self.path not in actions:
                self.respond({"error": "Not found."}, 404)
                return
            if self.headers.get_content_type() != "application/json":
                self.respond({"error": "Send application/json."}, 415)
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
                self.respond({"error": "A single Content-Length is required."}, 400)
                return
            try:
                length = int(lengths[0])
            except ValueError:
                length = -1
            if length < 0 or length > max_body:
                self.respond({"error": "Request is too large. CV files must be at most 20 MiB."}, 413)
                return
            try:
                self.connection.settimeout(60)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete request. Please try again.")
                def reject_constant(_value):
                    raise ValueError("Numbers must be finite.")
                payload = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
                if not isinstance(payload, dict):
                    raise ValueError("Send a JSON object.")
                result = actions[self.path](payload)
                self.respond(result, 202 if self.path == "/api/search" else 200)
            except (ValueError, UnicodeError) as exc:
                message = "Invalid JSON request." if isinstance(exc, json.JSONDecodeError) else str(exc)
                self.respond({"error": message}, 400)
            except (OSError, KeyError):
                self.respond({"error": "Could not save local data. Check the workspace and try again."}, 500)

        def log_message(self, *_args):
            pass

    return Handler


def serve(root: Path, port: int = 8766, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(root))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Career Starter: {url} (Ctrl+C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
