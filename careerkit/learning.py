"""Evidence-led local learning plans; no candidate data leaves the workspace."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .search import plain_text
from .workspace import digest, evidence, private, read_json, validate_profile, write_json, write_text


# Aliases identify a topic, never proficiency. Exercises use synthetic work samples.
# Each localized task is: exercise, output, completion check, first small action.
SKILLS = {
    "spreadsheets": {
        "aliases": ("excel", "spreadsheets", "spreadsheet", "google sheets", "таблиці", "таблицями", "електронних таблиць", "excel-kenntnisse", "arkusze"),
        "en": ("Spreadsheets", "Create a 20-row fictional work tracker with categories, dates and amounts; clean it and summarize it using formulas and a pivot table.", "A workbook with raw data, a summary and a short explanation.", "Totals reconcile with raw rows; filters and formulas work after adding a row; explain two decisions without a tutorial.", "Create five fictional rows relevant to the target role and calculate one total."),
        "uk": ("Електронні таблиці", "Створіть таблицю з 20 вигаданими робочими записами, категоріями, датами й сумами; очистіть дані та підсумуйте їх формулами і зведеною таблицею.", "Файл із вихідними даними, підсумками та коротким поясненням.", "Підсумки збігаються з даними; фільтри й формули працюють після додавання рядка; поясніть два рішення без інструкції.", "Додайте п'ять вигаданих записів для цільової ролі й обчисліть один підсумок."),
    },
    "customer_support": {
        "aliases": ("customer support", "customer service", "customer inquiries", "customer enquiries", "customer questions", "client questions", "customer requests", "support requests", "billing questions", "support tickets", "ticket handling", "підтримка клієнтів", "підтримки клієнтів", "звернення клієнтів", "kundenservice", "kundenanfragen", "obsługa klienta"),
        "en": ("Customer support", "Resolve three fictional cases: a billing dispute, an unclear request and an outage; write replies, internal notes and escalation decisions.", "Three case records with replies and next actions.", "Each reply identifies the problem, avoids unsupported promises, gives a clear next step and records when escalation is needed.", "Write a five-sentence reply to a fictional unexpected-charge complaint."),
        "uk": ("Підтримка клієнтів", "Опрацюйте три вигадані звернення: спір щодо рахунку, неясний запит і збій; напишіть відповіді, внутрішні нотатки та рішення про ескалацію.", "Три описи звернень із відповідями та наступними діями.", "Кожна відповідь визначає проблему, не містить непідтверджених обіцянок, дає наступний крок та умови ескалації.", "Напишіть відповідь із п'яти речень на вигадану скаргу щодо несподіваного списання."),
    },
    "crm": {
        "aliases": ("crm", "salesforce", "hubspot", "zendesk", "intercom", "freshdesk"),
        "en": ("CRM and case records", "Model five fictional contacts or tickets in a table, including status, owner, history and next action; document an escalation and a duplicate merge.", "A small CRM workflow and five complete records.", "No record lacks an owner or next action; history remains traceable; explain the duplicate and escalation rules.", "List the fields needed for one fictional contact or ticket."),
        "uk": ("CRM та облік звернень", "Змоделюйте в таблиці п'ять вигаданих контактів або звернень зі статусом, відповідальним, історією й наступною дією; опишіть ескалацію та об'єднання дубліката.", "Схема процесу CRM і п'ять заповнених записів.", "Кожен запис має відповідального й наступну дію; історія простежується; поясніть правила дублікатів та ескалації.", "Визначте поля одного вигаданого контакту або звернення."),
    },
    "writing": {
        "aliases": ("written communication", "business writing", "copywriting", "content writing", "documentation", "письмова комунікація", "копірайтинг", "документація", "schriftliche kommunikation", "redagowanie"),
        "en": ("Workplace writing", "Write a 250-word explanation of a fictional role-specific process and a short email for its intended audience; revise for clarity.", "A first draft, revised text and three editing decisions.", "A reader can identify the purpose, required action and deadline; facts stay consistent; remove vague claims and unexplained jargon.", "Define the reader and write the main action in one sentence."),
        "uk": ("Робочі тексти", "Напишіть пояснення вигаданого робочого процесу на 250 слів і короткий лист для його аудиторії; відредагуйте для зрозумілості.", "Чернетка, відредагований текст і три пояснення правок.", "Читач розуміє мету, потрібну дію та строк; факти узгоджені; немає нечітких заяв і непоясненого жаргону.", "Визначте читача та сформулюйте головну дію одним реченням."),
    },
    "english": {
        "aliases": ("english", "англійська", "англійською", "англійської", "englisch", "angielski"),
        "en": ("English for work", "Prepare a 150-word role-specific email and a two-minute spoken explanation in English; ask for feedback on clarity.", "The email, a recording or transcript and a correction log.", "The recipient can repeat the intended action; explain unfamiliar words; revise three unclear phrases. This does not certify a language level.", "Write five sentences about a fictional task in the target role."),
        "uk": ("Англійська для роботи", "Підготуйте робочий лист на 150 слів і двохвилинне усне пояснення англійською; попросіть відгук про зрозумілість.", "Лист, запис або транскрипт та журнал виправлень.", "Адресат може повторити потрібну дію; поясніть незнайомі слова; виправте три неясні фрази. Це не сертифікує мовний рівень.", "Напишіть п'ять речень про вигадане завдання на цільовій посаді."),
    },
    "german": {
        "aliases": ("german", "німецька", "німецькою", "німецької", "deutsch", "niemiecki"),
        "en": ("German for work", "Prepare a 150-word role-specific email and a two-minute spoken explanation in German; request clarity feedback.", "The email, a recording or transcript and a correction log.", "The recipient understands the intended action; revise three unclear phrases. A practice result does not certify a language level.", "Write five German sentences about a fictional task in the target role."),
        "uk": ("Німецька для роботи", "Підготуйте робочий лист на 150 слів і двохвилинне усне пояснення німецькою; попросіть відгук про зрозумілість.", "Лист, запис або транскрипт та журнал виправлень.", "Адресат розуміє потрібну дію; виправте три неясні фрази. Результат вправи не сертифікує мовний рівень.", "Напишіть п'ять речень німецькою про вигадане завдання на цільовій посаді."),
    },
    "sql": {
        "aliases": ("sql", "postgresql", "mysql"),
        "en": ("SQL", "Use two small fictional tables to answer three work questions with filtering, joins and aggregation; include a missing value and a duplicate.", "Queries, sample tables and expected results.", "Results match hand-calculated totals; joins do not duplicate totals; explain how missing values are handled.", "Draw two related tables and hand-calculate the answer to one question."),
        "uk": ("SQL", "Використайте дві невеликі таблиці з вигаданими даними для трьох робочих запитань через фільтрацію, об'єднання й агрегацію; додайте пропуск та дублікат.", "Запити, приклади таблиць та очікувані результати.", "Результати збігаються з ручним розрахунком; об'єднання не подвоює суми; поясніть обробку пропусків.", "Накресліть дві пов'язані таблиці й вручну знайдіть відповідь на одне запитання."),
    },
    "python": {
        "aliases": ("python", "пайтон"),
        "en": ("Python", "Transform a fictional CSV into a summary report; validate missing fields and malformed numbers and explain the transformation.", "A small script, input sample and output report.", "A valid example produces the expected totals; invalid rows are reported clearly; rerunning gives the same result.", "Create a five-row fictional CSV and describe its expected summary."),
        "uk": ("Python", "Перетворіть CSV із вигаданими даними на підсумковий звіт; перевірте пропуски та хибні числа, поясніть перетворення.", "Невеликий скрипт, приклад вхідних даних і звіт.", "Правильний приклад дає очікувані підсумки; хибні рядки мають зрозумілі повідомлення; повторний запуск дає той самий результат.", "Створіть CSV із п'ятьма вигаданими рядками й опишіть очікуваний підсумок."),
    },
    "bookkeeping": {
        "aliases": ("bookkeeping", "reconciliation", "accounts payable", "accounts receivable", "бухгалтерський облік", "бухгалтерського обліку", "звірка", "buchhaltung", "księgowość"),
        "en": ("Bookkeeping and reconciliation", "Reconcile ten fictional invoices with a payment ledger; flag a duplicate, missing payment and amount mismatch.", "A reconciliation table and an exceptions note.", "Every invoice is accounted for; the difference reconciles to listed exceptions; no real financial decisions are made.", "Create three fictional invoices and match them to three payments."),
        "uk": ("Облік і звірка", "Звірте десять вигаданих рахунків із журналом оплат; позначте дублікат, відсутню оплату та розбіжність сум.", "Таблиця звірки й перелік винятків.", "Кожен рахунок враховано; різниця пояснюється винятками; жодних реальних фінансових рішень.", "Створіть три вигадані рахунки та зіставте їх із трьома оплатами."),
    },
    "marketing": {
        "aliases": ("digital marketing", "seo", "social media", "email marketing", "campaigns", "маркетинг", "соціальні мережі", "соціальних мереж", "kampagnen", "marketing cyfrowy"),
        "en": ("Marketing campaigns", "Create a one-page campaign brief for a fictional product: audience, message, two channel examples and a measurement plan.", "A campaign brief, two sample messages and a metrics table.", "Each message fits the stated audience; metrics connect to the objective; distinguish projected results from observed results.", "Choose a fictional audience and write one measurable campaign objective."),
        "uk": ("Маркетингові кампанії", "Створіть односторінковий бриф кампанії вигаданого продукту: аудиторія, повідомлення, два приклади каналів і план вимірювання.", "Бриф, два приклади повідомлень та таблиця метрик.", "Повідомлення відповідають аудиторії; метрики пов'язані з метою; очікувані результати відокремлено від фактичних.", "Виберіть вигадану аудиторію та запишіть одну вимірювану мету кампанії."),
    },
    "analysis": {
        "aliases": ("data analysis", "power bi", "tableau", "analytics", "аналіз даних", "аналітика", "datenanalyse", "analiza danych"),
        "en": ("Data analysis", "Analyze a small fictional dataset to answer a role-specific decision question; compare two groups and show one chart with limitations.", "A short analysis, chart and recommendation.", "The calculation is reproducible; chart labels include units; the recommendation distinguishes evidence from assumptions.", "State one decision question and sketch the data needed to answer it."),
        "uk": ("Аналіз даних", "Проаналізуйте невеликий набір вигаданих даних для робочого рішення; порівняйте дві групи й покажіть графік з обмеженнями.", "Короткий аналіз, графік і рекомендація.", "Розрахунок відтворюється; графік має одиниці виміру; рекомендація відокремлює факти від припущень.", "Сформулюйте одне запитання для рішення та перелік потрібних даних."),
    },
    "coordination": {
        "aliases": ("project management", "project coordination", "scheduling", "stakeholder", "управління проєктами", "координація", "планування зустрічей", "projektmanagement", "koordynacja"),
        "en": ("Coordination and planning", "Plan a fictional five-task delivery with owners, dependencies, dates and risks; write a short status update after one task slips.", "A task plan and a revised status update.", "Each task has an owner and completion check; dependencies are feasible; the delay has a clear impact and next action.", "List five tasks for a fictional deliverable and identify the first dependency."),
        "uk": ("Координація і планування", "Сплануйте вигадану роботу з п'яти завдань: відповідальні, залежності, дати й ризики; напишіть статус після затримки одного завдання.", "План завдань і оновлений статус.", "Кожне завдання має відповідального та критерій завершення; залежності реалістичні; затримка має опис впливу й наступну дію.", "Запишіть п'ять завдань для вигаданого результату й першу залежність."),
    },
}

REQUIREMENT = re.compile(
    r"\b(require\w*|must|experience|proficien\w*|knowledge|familiar\w*|ability|skills?|"
    r"responsib\w*|you will|you.ll|manage|handle|resolve|prepare|create|analy[sz]e|"
    r"qualifications?|kenntnisse|erfahrung|aufgaben|anforderungen|wymag\w*|doświadczenie|"
    r"вимог\w*|досвід\w*|знан\w*|володін\w*|обов.яз\w*|потріб\w*|вміння|"
    r"опрацьов\w*|створюв\w*|готув\w*|аналізув\w*|compétences?|expérience|maîtrise|"
    r"requis\w*|exig\w*|missions?)\b", re.I,
)
NEGATIVE = re.compile(
    r"\b(no|not|never|without|lack\w*|haven.t|hasn.t|don.t|doesn.t|didn.t|"
    r"не|немає|без|ніколи|kein\w*|nicht|ohne|brak|nie)\b", re.I,
)
FUTURE = re.compile(
    r"\b(want|wish|hope|plan|intend|aim|will|aspir\w*|learning|studying|"
    r"хочу|планую|вивчаю|навчаюсь|навчаюся|буду|lernen|möchte|planuję|uczę)\b", re.I,
)
ACTION = re.compile(
    r"\b(used|built|created|managed|handled|answered|resolved|prepared|maintained|wrote|"
    r"analy[sz]ed|developed|delivered|supported|worked|produced|reconciled|"
    r"використов\w*|створ\w*|опрацьов\w*|працюв\w*|готув\w*|виріш\w*|"
    r"аналізув\w*|керув\w*|erstell\w*|bearbeit\w*|verwend\w*)\b", re.I,
)
REQUIREMENT_HEADING = re.compile(
    r"^(requirements?|qualifications?|responsibilities|your profile|what you.ll do|"
    r"what you bring|вимоги|обов.язки|що потрібно|anforderungen|aufgaben|wymagania|"
    r"profil recherché|compétences|vos missions)\s*:?\s*$", re.I,
)
OTHER_HEADING = re.compile(
    r"^(benefits|about us|what we offer|our offer|perks|ми пропонуємо|про нас|"
    r"wir bieten|über uns|benefity|oferujemy|avantages|à propos de nous|nous offrons)\s*:?\s*$", re.I,
)


def _contains(text: str, phrase: str) -> bool:
    words = re.findall(r"\w+", phrase.casefold())
    normalized = " ".join(re.findall(r"\w+", text.casefold()))
    return bool(words) and " " + " ".join(words) + " " in " " + normalized + " "


def _topics(text: str) -> list[str]:
    return [key for key, spec in SKILLS.items() if any(_contains(text, term) for term in spec["aliases"])]


def _sentences(text: str) -> list[str]:
    return [part.strip(" -*\t") for part in re.split(r"\n+|(?<=[.!?;])\s+", text) if part.strip(" -*\t")]


def _candidate_records(root: Path, profile: dict) -> list[dict]:
    claims = list(evidence(root).values())
    records = [{"id": c["id"], "text": c["text"], "source": c["source"]} for c in claims]
    seen = {c["text"].strip().casefold() for c in claims}
    master = private(root, "master.md")
    for line in _sentences(master.read_text(encoding="utf-8") if master.exists() else ""):
        if line.casefold() not in seen and not line.startswith("#"):
            records.append({"id": "", "text": line, "source": "local/master.md"})
    records += [{"id": "", "text": text, "source": "profile.skills"} for text in profile["skills"]]
    records += [{"id": "", "text": text, "source": "profile.languages"} for text in profile["languages"]]
    return records


def _claim_status(clause: str, skill_id: str, label: str, source: str) -> str:
    aliases = SKILLS[skill_id]["aliases"] if skill_id in SKILLS else (label,)
    normalized = " ".join(re.findall(r"\w+", clause.casefold()))
    # A negation elsewhere ("SQL with no errors") is not a reported skill gap.
    for alias in aliases:
        phrase = " ".join(re.findall(r"\w+", alias.casefold()))
        for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized):
            before, after = normalized[:match.start()].strip(), normalized[match.end():].strip()
            explicit_gap = re.search(
                r"\b(?:(?:no|without|lack|lacks|lacking) (?:any |prior |practical |professional )?"
                r"(?:experience|knowledge|skills?|proficiency)(?: (?:in|with|using|of))?"
                r"|(?:never|not|haven t|hasn t|didn t|don t|can t|cannot) "
                r"(?:used?|worked with|learned|studied|know|mastered|understand|have experience (?:in|with))"
                r"|(?:немає|не маю|без) (?:досвіду|знань)(?: роботи)?(?: з| у)?"
                r"|не (?:працював|працювала|працюю|вмію працювати) з"
                r"|(?:keine|ohne) (?:erfahrung|kenntnisse)(?: mit| in)?"
                r"|brak doświadczenia(?: z| w)?)$", before,
            )
            direct_gap = re.search(r"\b(?:no|lack|lacks|lacking)$", before) and re.match(
                r"(?:experience|knowledge|skills?|proficiency)\b", after)
            if explicit_gap or direct_gap:
                return "self_reported_gap"
    if FUTURE.search(clause):
        return "unknown"
    negative = NEGATIVE.search(clause)
    if negative:
        # Limited qualifications do not negate the task; other negation stays
        # unknown until clarified instead of becoming an invented absence.
        benign = re.search(r"\b(?:without errors?|with no errors?|without macros?)\b", clause, re.I)
        if not benign:
            return "unknown"
    if ACTION.search(clause) and not source.startswith("profile."):
        return "documented"
    return "partial"


def _starting_point(skill_id: str, label: str, records: list[dict]) -> tuple[str, list[dict]]:
    candidates = []
    for record in records:
        for sentence in _sentences(record["text"]):
            # Separate contrasting clauses so "Excel, but no SQL" cannot prove SQL.
            for clause in re.split(r"\b(?:but|however|але|проте|aber)\b", sentence, flags=re.I):
                matched = skill_id in _topics(clause) if skill_id in SKILLS else _contains(clause, label)
                if not matched:
                    continue
                status = _claim_status(clause, skill_id, label, record["source"])
                candidates.append({**record, "text": clause.strip(), "status": status})
    statuses = {item["status"] for item in candidates}
    if "self_reported_gap" in statuses and statuses & {"documented", "partial"}:
        status = "unknown"  # Conflicting claims need clarification, not a proficiency verdict.
    else:
        status = next((x for x in ("documented", "partial", "self_reported_gap") if x in statuses), "unknown")
    return status, candidates[:5]


def _requirement_clauses(sentence: str) -> list[tuple[str, bool]]:
    """Keep a coordinated skill list with its shared requirement predicate."""
    clauses = []
    for group in re.split(r"\b(?:but|however|але|проте|aber|mais)\b", sentence, flags=re.I):
        pending = []
        negative_prefix = False
        for clause in re.split(r",|\b(?:and|und|et)\b", group, flags=re.I):
            pending.append(clause)
            negative_prefix |= bool(re.match(r"\s*(?:no|without)\b", clause, re.I))
            predicate = re.search(r"\b(?:required|needed|necessary|essential)\b", clause, re.I)
            if predicate:
                negative = negative_prefix or bool(re.search(
                    r"\b(?:not|never)\s+(?:required|needed|necessary|essential)\b", clause, re.I))
                clauses.extend((item, negative) for item in pending)
                pending = []
                negative_prefix = False
        clauses.extend((item, negative_prefix) for item in pending)
    return clauses


def _job_requirements(jobs: list[dict]) -> tuple[dict, list[dict]]:
    requirements, unrecognized = {}, []
    for job in jobs:
        section = ""
        seen = set()
        for sentence in _sentences(plain_text(job.get("description", ""))):
            heading, separator, remainder = sentence.partition(":")
            if REQUIREMENT_HEADING.fullmatch(heading):
                section = "requirements"
                sentence = remainder.strip() if separator else ""
            elif OTHER_HEADING.fullmatch(heading):
                section = "excluded"
            if section == "excluded" or not sentence:
                continue
            if not (section == "requirements" or REQUIREMENT.search(sentence)):
                continue
            source = {key: job.get(key, "") for key in ("title", "url")}
            source.update(job_id=job.get("id", ""), snippet=sentence[:700])
            for clause, shared_negation in _requirement_clauses(sentence):
                if shared_negation:
                    continue
                topics = _topics(clause)
                for skill_id in topics:
                    negated = False
                    normalized = " ".join(re.findall(r"\w+", clause.casefold()))
                    for alias in SKILLS[skill_id]["aliases"]:
                        phrase = " ".join(re.findall(r"\w+", alias.casefold()))
                        match = re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized)
                        if not match:
                            continue
                        before, after = normalized[:match.start()], normalized[match.end():]
                        if NEGATIVE.search(before) or re.match(
                            r"\s*(?:(?:experience|knowledge|skills?|kenntnisse|досвід|знання)\s+)?"
                            r"(?:(?:is|are|ist|sind|не є|est)\s+)?"
                            r"(?:not|never|no|nicht|kein\w*|не|без|pas)\b", after,
                        ):
                            negated = True
                    if skill_id not in seen and not negated:
                        requirements.setdefault(skill_id, []).append(source)
                        seen.add(skill_id)
                if not topics and not NEGATIVE.search(clause) and len(clause.strip()) >= 20 and len(unrecognized) < 12:
                    unrecognized.append({**source, "snippet": clause.strip()[:700]})
    return requirements, unrecognized


def _fallback_task(label: str, role: str, lang: str) -> tuple:
    if lang == "uk":
        return (label, f"Для ролі «{role}» виберіть одну наведену вимогу або ціль «{label}». Опишіть реальний тип завдання, потрібні вхідні дані та критерії; виконайте малий приклад із вигаданими даними. Спочатку узгодьте спеціалізовані критерії з кандидатом або фахівцем.",
                "Опис завдання, пробний результат і перелік питань для перевірки.",
                "Результат відповідає погодженій вимозі; поясніть рішення й отримайте конкретний відгук. Автоматична оцінка спеціалізованої компетентності недоступна.",
                "Виберіть одну вимогу та запишіть, який результат роботи її продемонструє.")
    return (label, f"For '{role}', select one cited requirement or the goal '{label}'. Define a real task, its inputs and checks; produce a small example with fictional data. Agree on specialist checks with the candidate or a practitioner first.",
            "A task brief, work sample and questions for review.",
            "The sample meets the agreed requirement; explain decisions and obtain specific feedback. Specialist competence cannot be automatically assessed.",
            "Choose one requirement and write down the work output that would demonstrate it.")


def _analysis(root: Path) -> dict:
    profile = validate_profile(read_json(private(root, "profile.json")))
    records = _candidate_records(root, profile)
    saved_jobs = read_json(private(root, "jobs.json"), {})
    all_jobs = saved_jobs.get("jobs", [])
    jobs = [job for job in all_jobs if job.get("match_status") == "review" and not job.get("stale")]
    requirements, unrecognized = _job_requirements(jobs)
    lang = "uk" if profile.get("learning_language") == "uk" else "en"
    topics = {key: {"skill_id": key, "requirements": sources, "goal_reasons": []}
              for key, sources in requirements.items()}
    unknown_goals = []
    for goal in profile["learning_goals"]:
        known = _topics(goal["skill"])
        if not known:
            known = ["goal:" + goal["skill"].casefold()]
            unknown_goals.append(goal["skill"])
        for key in known:
            item = topics.setdefault(key, {"skill_id": key, "requirements": [], "goal_reasons": []})
            item["goal_reasons"].append(goal["reason"])
            item.setdefault("goal_label", goal["skill"])
    if not topics:
        topics["requirement_review"] = {"skill_id": "requirement_review", "requirements": unrecognized[:3],
                                       "goal_reasons": []}
    for key, topic in topics.items():
        label = topic.get("goal_label") or (SKILLS[key][lang][0] if key in SKILLS else
            ("Уточнення вимог ролі" if lang == "uk" else "Clarify role requirements"))
        topic.update(skill=label)
        topic["status"], topic["candidate_evidence"] = _starting_point(key, label, records)
        topic["requirement_job_count"] = len({row["url"] for row in topic["requirements"]})
    # Candidate priorities first, repeated requirements next, then proof needing clarification.
    ordered = sorted(topics.values(), key=lambda topic: (
        -bool(topic["goal_reasons"]), -topic["requirement_job_count"],
        topic["status"] == "documented", topic["skill_id"],
    ))
    priorities = ordered[:3]
    total_minutes = int(profile["weekly_hours"] * 60)
    count = len(priorities)
    for i, topic in enumerate(priorities):
        task = SKILLS[topic["skill_id"]][lang] if topic["skill_id"] in SKILLS else _fallback_task(
            topic["skill"], ", ".join(profile["target_roles"]), lang)
        topic.update(exercise=task[1], output=task[2], success_check=task[3], first_step=task[4])
        topic["minutes"] = total_minutes // count + (1 if i < total_minutes % count else 0)
        topic["hours"] = topic["minutes"] / 60
        topic["mode"] = ("paused" if not topic["minutes"] else "work_sample" if topic["status"] == "documented"
                         else "practice" if topic["status"] == "self_reported_gap" else "assessment")
    inputs = {"profile": {key: profile[key] for key in (
        "target_roles", "skills", "languages", "weekly_hours", "learning_goals")},
        "language": lang, "candidate_records": records,
        "jobs": [{key: job.get(key) for key in ("id", "title", "url", "description", "stale", "match_status")}
                 for job in all_jobs]}
    input_hash = hashlib.sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"version": 1, "input_sha256": input_hash, "language": lang,
            "weekly_hours": profile["weekly_hours"], "target_roles": profile["target_roles"],
            "job_sample_count": len(jobs), "excluded_stale_jobs": sum(bool(j.get("stale")) for j in all_jobs),
            "priorities": priorities, "unrecognized_goals": unknown_goals,
            "unrecognized_requirements": unrecognized, "other_topic_count": max(0, len(topics) - 3)}


def _markdown(report: dict) -> str:
    uk = report["language"] == "uk"
    hours, sample = report["weekly_hours"], report["job_sample_count"]
    lines = ["# План навчання" if uk else "# Learning plan", "",
             (f"Доступний час: {hours:g} год/тиждень." if uk else f"Available time: {hours:g} hours/week."),
             ("Цільові ролі: " if uk else "Target roles: ") + ", ".join(report["target_roles"]), "",
             (f"Основа: {sample} актуальних вакансій для перегляду, CV та відповіді кандидата."
              if uk else f"Basis: {sample} current review leads, the CV and candidate answers."),
             ("Це обмежена вибірка, не загальний висновок про ринок або придатність до роботи. Твердження CV надані кандидатом, не перевірені незалежно. Відсутність згадки означає невідомий рівень, а не відсутню навичку."
              if uk else "This is a limited sample, not a market-wide or eligibility conclusion. CV claims are candidate-provided, not independently verified. An absent mention means unknown ability, not a missing skill."),
             ("Практика підтверджує навчання, а не професійний досвід. Зберігайте результати в local/learning/."
              if uk else "Practice is evidence of learning, not professional employment. Save outputs under local/learning/."), ""]
    if not sample:
        lines += [("Актуальних вакансій для порівняння немає. Цілі нижче взяті з відповідей; вимоги ринку ще не підтверджені."
                   if uk else "No current review leads are available. Candidate goals below are provisional; market requirements are not established."), ""]
    if report["excluded_stale_jobs"]:
        lines += [(f"Не враховано застарілі вакансії: {report['excluded_stale_jobs']}."
                   if uk else f"Stale leads excluded: {report['excluded_stale_jobs']}."), ""]
    if not hours:
        lines += [("Навчання відкладене: час не виділено. Теми нижче — пропозиції; завдання не заплановані."
                   if uk else "Learning is paused: no study time was committed. Topics below are suggestions; no tasks are scheduled."), ""]
    status_labels = {
        "documented": ("Є опис виконаної роботи в CV; рівень треба підтвердити прикладом", "CV documents a candidate claim of completed work; validate proficiency with a sample"),
        "partial": ("Є згадка, але бракує прикладу роботи або ясного рівня", "A skill is mentioned, but a work example or proficiency level is unclear"),
        "unknown": ("Невідомо: немає однозначного свідчення; почніть з оцінювання", "Unknown: no unambiguous evidence; assess before prescribing training"),
        "self_reported_gap": ("Кандидат прямо вказав на відсутність досвіду; уточніть поточний стан", "The candidate explicitly reports no experience; confirm their current starting point"),
    }
    for index, topic in enumerate(report["priorities"], 1):
        lines += [f"## {index}. {topic['skill']}", "",
                  ("Початкова точка: " if uk else "Starting point: ") + status_labels[topic["status"]][0 if uk else 1] + ".",
                  (f"Бюджет на тиждень: {topic['minutes']} хв." if uk else f"Weekly budget: {topic['minutes']} minutes."),
                  (f"Вакансій із цією вимогою: {topic['requirement_job_count']} із {sample}."
                   if uk else f"Leads citing this requirement: {topic['requirement_job_count']} of {sample}."), ""]
        for reason in topic["goal_reasons"]:
            lines += [("- Мета кандидата: " if uk else "- Candidate goal: ") + reason]
        for claim in topic["candidate_evidence"]:
            reference = claim["id"] or claim["source"]
            lines += [f"- CV [{reference}]: {claim['text']}"]
        if not topic["candidate_evidence"]:
            lines += [("- У CV немає конкретного прикладу; це не доводить відсутність навички."
                       if uk else "- No specific CV example was found; this does not establish a skill gap.")]
        for requirement in topic["requirements"][:5]:
            lines += [f"- {requirement['title']} — {requirement['url']}",
                      f"  > {requirement['snippet']}"]
        if not topic["requirements"]:
            lines += [("- Вакансії не підтверджують цю тему; основа — ціль кандидата або потреба уточнення."
                       if uk else "- No extracted vacancy requirement supports this topic; it comes from a candidate goal or needs clarification.")]
        if topic["mode"] == "work_sample":
            lines += ["", ("Почніть із самостійного робочого прикладу; тренуйте лише те, що не вдалося."
                           if uk else "Start with an independent work sample; practice only what the attempt exposes.")]
        elif topic["mode"] == "assessment":
            lines += ["", ("Спочатку спробуйте завдання без навчального матеріалу. Якщо впораєтеся, збережіть доказ і перейдіть далі; інакше визначте конкретну тему для практики."
                           if uk else "First attempt the task without a tutorial. If it succeeds, keep the evidence and move on; otherwise identify a specific point to practice.")]
        lines += ["", ("Практична вправа: " if uk else "Exercise: ") + topic["exercise"],
                  ("Результат: " if uk else "Output: ") + topic["output"],
                  ("Перевірка: " if uk else "Completion check: ") + topic["success_check"]]
        if topic["minutes"]:
            first = min(15, topic["minutes"])
            lines += [(f"Перший крок (до {first} хв): " if uk else f"First action (up to {first} minutes): ") + topic["first_step"],
                      ("Працюйте в межах бюджету; незавершений приклад продовжіть наступного тижня."
                       if uk else "Stop at the weekly budget; continue an unfinished sample next week.")]
        lines += [("Огляд: наприкінці тижня запишіть результат, складнощі й відгук; оберіть наступну дію."
                   if uk else "Review: at the end of the week record the result, difficulty and feedback; choose the next action."), ""]
    if report["unrecognized_goals"] or report["unrecognized_requirements"]:
        lines += [("## Що потребує уточнення" if uk else "## Needs clarification"), "",
                  ("Локальний словник розпізнає лише частину навичок. Наведені спеціалізовані вимоги потрібно перевірити; згадка не доводить обов'язковість."
                   if uk else "The local dictionary recognizes only some skills. Review these specialist requirements; a mention alone does not establish a mandatory prerequisite.")]
        for requirement in report["unrecognized_requirements"][:3]:
            lines += [f"- {requirement['title']} — {requirement['url']}",
                      f"  > {requirement['snippet']}"]
        lines.append("")
    return "\n".join(lines)


def generate(root: Path) -> dict:
    """Refresh only unchanged generated output; preserve any candidate edits."""
    report = _analysis(root)
    content = _markdown(report)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    plan = private(root, "learning-plan.md")
    state_path = private(root, "learning-plan-state.json")
    previous = read_json(state_path, {})
    managed = not plan.exists() or previous.get("plan_sha256") == digest(plan)
    result = {"path": "local/learning-plan.md", "analysis_path": "local/learning-plan.json",
              "preserved": not managed, "updated": False}
    state = {"version": 1, "input_sha256": report["input_sha256"]}
    if managed:
        if not plan.exists() or digest(plan) != content_hash:
            write_text(plan, content)
            result["updated"] = True
        state["plan_sha256"] = content_hash
    else:
        state["plan_sha256"] = previous.get("plan_sha256")
        suggestion = private(root, "learning-plan.suggested.md")
        if suggestion.exists() and digest(suggestion) not in {previous.get("suggestion_sha256"), content_hash}:
            suggestion = private(root, f"learning-plan.suggested-{content_hash[:12]}.md")
            suffix = 2
            while suggestion.exists() and digest(suggestion) != content_hash:
                alternate = hashlib.sha256(f"{content_hash}:{suffix}".encode()).hexdigest()[:12]
                suggestion = private(root, f"learning-plan.suggested-{alternate}.md")
                suffix += 1
        if not suggestion.exists() or digest(suggestion) != content_hash:
            write_text(suggestion, content)
            result["updated"] = True
        state.update(suggestion_path=suggestion.relative_to(root).as_posix(), suggestion_sha256=content_hash)
        result["suggestion_path"] = state["suggestion_path"]
    report.update(preserved=result["preserved"], suggestion_path=result.get("suggestion_path", ""))
    write_json(private(root, "learning-plan.json"), report)
    write_json(state_path, state)
    return result
