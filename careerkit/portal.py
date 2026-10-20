"""Read-only localhost dashboard; private documents never become static assets."""

from __future__ import annotations

import json
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
footer{margin:32px 0;color:var(--muted);font-size:13px}
@media(max-width:700px){.grid,.list{grid-template-columns:1fr}body{padding:16px}header{align-items:flex-start;flex-direction:column}.header-actions{justify-content:flex-start}}
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
<code id="command"></code></section>
<div class="grid"><div class="card"><div class="muted" data-i18n="jobCount">Jobs to review</div><div class="number" id="job-count">—</div></div>
<div class="card"><div class="muted" data-i18n="appCount">Applications</div><div class="number" id="app-count">—</div></div>
<div class="card"><div class="muted" data-i18n="search">Search</div><div id="search-status"></div></div></div>
<section class="section"><h2 data-i18n="sources">Sources</h2><div id="sources"></div></section>
<section class="section"><div class="row"><h2 data-i18n="jobs">Jobs</h2><input id="filter" aria-label="Filter jobs" placeholder="Job title or company" data-i18n-label="filterLabel" data-i18n-placeholder="filterPlaceholder"></div>
<p class="muted" data-i18n="matchNote">A keyword match is a reason to review a job. Check its terms, country, work authorization and availability.</p><div class="list" id="jobs"></div></section>
<section class="section"><h2 data-i18n="applications">Application preparation</h2><div class="list" id="applications"></div></section>
<section class="section"><h2 data-i18n="learning">Learning plan</h2><pre class="card" id="plan"></pre></section>
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
let language='en';
try{const saved=localStorage.getItem('career-starter.language');if(saved==='en'||saved==='uk')language=saved;}catch{}
let current=null,loadError='';
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
 el('welcome').textContent=current.onboarded?t('nextStep'):t('welcome');
 el('next').textContent=current.onboarded?current.target_roles.join(' · ')+' / '+current.locations.join(' · '):t('onboarding');
 el('command').textContent=current.onboarded?'python career.py search':'python career.py import-cv local/inbox/your-cv.pdf';
 el('job-count').textContent=current.jobs.length;el('app-count').textContent=current.applications.length;
 el('search-status').textContent=label('statuses',current.search_status);
 el('sources').replaceChildren(...current.sources.map(s=>node('p',s.name+' — '+label('statuses',s.status)+' ('+(s.count||0)+')','tag')));
 if(!current.sources.length)el('sources').append(node('p',t('noSources'),'muted'));
 el('applications').replaceChildren(...current.applications.map(a=>{
 const card=node('article','','card');card.append(node('h3',a.title||a.id),node('p',a.company||''),node('span',label('stages',a.stage),'tag'),
 node('p',a.readiness?label('readiness',a.readiness):label('stages','needs repair'),'muted'),node('code','python career.py hash '+a.id));return card;
 }));
 if(!current.applications.length)el('applications').append(node('p',t('noApplications'),'muted'));
 el('plan').textContent=current.learning_plan||t('noPlan');
 jobs();
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
async function refresh(){
 try{
 const r=await fetch('/api/state');if(!r.ok)throw new Error('HTTP '+r.status);current=await r.json();
 loadError='';
 }catch(e){loadError=String(e);}
 render();
}
el('refresh').addEventListener('click',refresh);el('filter').addEventListener('input',jobs);
el('language-en').addEventListener('click',()=>setLanguage('en'));
el('language-uk').addEventListener('click',()=>setLanguage('uk'));
el('theme-toggle').addEventListener('click',toggleTheme);
render();refresh();
</script></body></html>"""


def handler(root: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            host = self.headers.get("Host", "")
            expected = f"127.0.0.1:{self.server.server_port}"
            if host != expected or self.headers.get("Origin") not in {None, f"http://{expected}"}:
                self.send_error(403)
                return
            if self.path not in {"/", "/api/state"}:
                self.send_error(404)
                return
            try:
                body = PAGE.encode() if self.path == "/" else json.dumps(state(root), ensure_ascii=False).encode()
            except (ValueError, OSError, KeyError):
                self.send_error(500, "Local workspace data needs repair. Ask your assistant to inspect it.")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8" if self.path == "/" else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

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
