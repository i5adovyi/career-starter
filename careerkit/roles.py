"""Offline, curated job-title aliases; matching is a lead, not eligibility."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache


# Keep different professions separate. In particular, generic "support",
# "account", "operations" and "analyst" are deliberately not aliases.
ROLE_ALIASES = {
    "Customer Support": (
        "customer support", "customer service", "customer care", "client support",
        "client services", "customer service representative", "customer support specialist",
        "customer support representative", "customer support agent", "customer service agent",
        "customer care specialist", "customer care representative", "client support specialist",
        "підтримка клієнтів", "служба підтримки клієнтів", "обслуговування клієнтів",
        "фахівець з підтримки клієнтів", "спеціаліст підтримки клієнтів",
        "kundenservice", "kundensupport", "kundenbetreuung", "kundenberater",
        "kundenberaterin", "kundenservicemitarbeiter", "kundenservicemitarbeiterin",
        "mitarbeiter kundenservice", "mitarbeiterin kundenservice", "mitarbeiter im kundenservice",
        "mitarbeiterin im kundenservice",
        "obsługa klienta", "specjalista ds obsługi klienta", "specjalistka ds obsługi klienta",
        "service client", "service clientèle", "support client", "chargé de support client",
        "chargée de support client", "conseiller clientèle", "conseillère clientèle",
    ),
    "Technical Support": (
        "technical support", "it support", "it helpdesk", "help desk technician",
        "service desk analyst", "технічна підтримка", "фахівець технічної підтримки",
        "technischer support", "technischer kundensupport", "it kundenbetreuung",
        "wsparcie techniczne", "pomoc techniczna", "support technique",
    ),
    "Customer Success": (
        "customer success", "client success", "успіх клієнтів",
        "sukces klienta", "succès client",
    ),
    "Operations Assistant": (
        "operations assistant", "operations coordinator", "operations associate",
        "операційний асистент", "операційна асистентка", "асистент операційного відділу",
        "координатор операцій", "координаторка операцій",
        "operations assistenz", "operationsassistent", "operationsassistentin",
        "assistenz operations", "operativer assistent", "operative assistentin",
        "asystent operacyjny", "asystentka operacyjna", "koordynator operacyjny",
        "assistant opérations", "assistante opérations", "assistant aux opérations",
    ),
    "Administrative Assistant": (
        "administrative assistant", "admin assistant", "office assistant", "office administrator",
        "адміністративний асистент", "адміністративна асистентка", "офісний асистент",
        "офісна асистентка", "büroassistenz", "büroassistent", "büroassistentin",
        "verwaltungsassistent", "verwaltungsassistentin", "assistenz verwaltung",
        "asystent administracyjny", "asystentka administracyjna", "asystent biura",
        "assistant administratif", "assistante administrative",
    ),
    "Accountant": (
        "accountant", "financial accountant", "бухгалтер", "бухгалтерка", "buchhalter", "buchhalterin",
        "finanzbuchhalter", "finanzbuchhalterin", "księgowy", "księgowa", "comptable",
    ),
    "Accounting Assistant": (
        "accounting assistant", "accounts assistant", "accounting clerk", "assistant accountant",
        "помічник бухгалтера", "помічниця бухгалтера", "асистент бухгалтера",
        "buchhaltungsassistent", "buchhaltungsassistentin", "assistenz buchhaltung",
        "asystent księgowości", "asystentka księgowości", "assistant comptable",
        "assistante comptable",
    ),
    "Marketing": (
        "marketing", "marketing specialist", "marketing associate", "marketing coordinator", "marketer",
        "маркетинг", "маркетолог", "маркетологиня", "фахівець з маркетингу",
        "marketingmitarbeiter", "marketingmitarbeiterin", "marketing spezialist",
        "marketing spezialistin", "specjalista ds marketingu", "specjalistka ds marketingu",
        "chargé de marketing", "chargée de marketing",
    ),
    "Digital Marketing": (
        "digital marketing", "digital marketer", "online marketing",
        "інтернет маркетолог", "цифровий маркетинг", "онлайн маркетинг",
        "onlinemarketing", "marketing internetowy", "marketing numérique",
    ),
    "Sales Representative": (
        "sales representative", "sales associate", "sales consultant",
        "торговий представник", "торгова представниця", "консультант з продажу",
        "vertriebsmitarbeiter", "vertriebsmitarbeiterin", "verkaufsberater", "verkaufsberaterin",
        "przedstawiciel handlowy", "przedstawicielka handlowa", "doradca sprzedaży",
        "représentant commercial", "représentante commerciale", "conseiller commercial",
    ),
    "Recruiter": (
        "recruiter", "recruitment specialist", "talent acquisition specialist",
        "рекрутер", "рекрутерка", "фахівець з підбору персоналу", "personalvermittler",
        "personalvermittlerin", "rekruter", "rekruterka", "specjalista ds rekrutacji",
        "chargé de recrutement", "chargée de recrutement",
    ),
    "Project Manager": (
        "project manager", "project management specialist", "менеджер проєктів",
        "менеджер проектів", "керівник проєкту", "керівниця проєкту",
        "projektmanager", "projektmanagerin", "projektleiter", "projektleiterin",
        "kierownik projektu", "kierowniczka projektu", "chef de projet", "cheffe de projet",
    ),
    "Product Manager": (
        "product manager", "менеджер продукту", "продуктовий менеджер",
        "produktmanager", "produktmanagerin", "menedżer produktu", "kierownik produktu",
        "chef de produit", "cheffe de produit",
    ),
    "Account Manager": (
        "account manager", "key account manager", "менеджер по роботі з клієнтами",
        "менеджер з роботи з клієнтами", "аккаунт менеджер", "акаунт менеджер",
        "key account betreuer", "opiekun klienta", "gestionnaire de comptes",
    ),
    "Software Developer": (
        "software developer", "software engineer", "розробник програмного забезпечення",
        "розробниця програмного забезпечення", "програміст", "програмістка",
        "softwareentwickler", "softwareentwicklerin", "software entwickler",
        "programista", "programistka", "développeur logiciel", "développeuse logiciel",
    ),
    "QA Engineer": (
        "qa engineer", "quality assurance engineer", "software tester", "qa tester",
        "тестувальник програмного забезпечення", "тестувальниця програмного забезпечення",
        "інженер з тестування", "softwaretester", "softwaretesterin", "software tester",
        "tester oprogramowania", "ingénieur qa", "testeur logiciel", "testeuse logiciel",
    ),
    "Data Analyst": (
        "data analyst", "аналітик даних", "аналітикиня даних", "datenanalyst",
        "datenanalystin", "analityk danych", "analyste de données",
    ),
    "Business Analyst": (
        "business analyst", "бізнес аналітик", "бізнес аналітикиня",
        "geschäftsanalyst", "geschäftsanalystin", "analityk biznesowy", "analyste métier",
    ),
}

_LEVELS = {
    "intern": ("intern", "internship", "praktikant", "praktikantin", "стажер", "стажерка",
              "стажист", "стажистка", "stażysta", "stażystka", "stagiaire"),
    "trainee": ("trainee", "auszubildende", "auszubildender"),
    "junior": ("junior", "jr", "entry level", "entry", "молодший", "молодша",
               "młodszy", "młodsza", "débutant", "débutante"),
    "middle": ("middle", "mid", "mid level"),
    "senior": ("senior", "sr", "старший", "старша", "starszy", "starsza",
               "sénior", "confirmé", "confirmée"),
    "lead": ("lead", "principal", "провідний", "провідна"),
}
_MANAGEMENT = {
    "executive": ("chief", "vp", "vice president"),
    "director": ("director", "директор", "директорка", "dyrektor", "directeur", "directrice"),
    "head": ("head", "leiter", "leiterin", "leitung"),
    "lead": ("lead", "teamlead", "team lead", "teamleiter", "teamleiterin"),
    "manager": ("manager", "керівник", "керівниця", "менеджер", "менеджерка",
                "kierownik", "kierowniczka", "menedżer", "menedżerka",
                "responsable", "chef", "cheffe"),
}
_SUPPORT_TECHNICAL = (
    "it", "technical", "technischer", "technische", "technischen", "software", "engineer",
    "технічна", "технічний", "технічної", "techniczne", "techniczny", "technique",
)
_BROAD_ALIASES = {
    "customer support", "customer service", "customer care", "client support", "client services",
    "підтримка клієнтів", "служба підтримки клієнтів", "обслуговування клієнтів",
    "kundenservice", "kundensupport", "kundenbetreuung", "obsługa klienta",
    "service client", "service clientèle", "support client",
    "technical support", "it support", "it helpdesk", "технічна підтримка",
    "technischer support", "technischer kundensupport", "it kundenbetreuung",
    "wsparcie techniczne", "pomoc techniczna", "support technique",
    "customer success", "client success", "успіх клієнтів", "sukces klienta", "succès client",
    "marketing", "маркетинг", "digital marketing", "online marketing", "onlinemarketing",
    "цифровий маркетинг", "онлайн маркетинг", "marketing internetowy", "marketing numérique",
}


def words(text: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def _phrase(text: str, phrase: str) -> bool:
    return bool(phrase) and f" {phrase} " in f" {text} "


_ALIASES = tuple(sorted(
    ((words(alias), canonical) for canonical, aliases in ROLE_ALIASES.items() for alias in aliases),
    key=lambda entry: (-len(entry[0].split()), -len(entry[0]), entry[0]),
))
_BY_ROLE = {canonical: tuple(alias for alias, role in _ALIASES if role == canonical)
            for canonical in ROLE_ALIASES}
_QUALIFIERS = {
    word for phrase in (*(alias for aliases in _MANAGEMENT.values() for alias in aliases),
                        *(alias for aliases in _LEVELS.values() for alias in aliases),
                        "of", "team", "de", "du", "des", "ds", "з", "відділу")
    for word in words(phrase).split()
}


def title_seniority(title: str) -> str:
    normalized = words(title)
    # Highest stated level wins when a title advertises a range.
    return next((level for level in reversed(_LEVELS)
                 if any(_phrase(normalized, words(alias)) for alias in _LEVELS[level])), "")


def _management(title: str) -> str:
    return next((level for level, aliases in _MANAGEMENT.items()
                 if any(_phrase(title, alias) for alias in aliases)), "")


@lru_cache(maxsize=256)
def _known_role(query: str) -> tuple[str, str] | None:
    for alias, canonical in _ALIASES:
        if _phrase(query, alias):
            remainder = query.replace(alias, "", 1).split()
            if all(word in _QUALIFIERS for word in remainder):
                return alias, canonical
    return None


def _compatible(query: str, title: str, requested_alias: str, matched_alias: str,
                canonical: str) -> bool:
    # A manager in an intrinsic title (e.g. Project Manager) is part of the
    # profession; only qualifiers outside the matched alias are compared.
    query_extra = query.replace(requested_alias, "", 1).strip()
    title_extra = title.replace(matched_alias, "", 1).strip()
    requested_management, actual_management = _management(query_extra), _management(title_extra)
    if requested_management and requested_management != actual_management:
        return False
    # Broad departments (e.g. Marketing) do not imply a staff-level position.
    # Explicit professions/qualifiers (e.g. Marketing Specialist) do.
    if not requested_management and actual_management and requested_alias not in _BROAD_ALIASES:
        return False
    requested_level, actual_level = title_seniority(query), title_seniority(title)
    if requested_level and actual_level and requested_level != actual_level:
        return False
    if canonical == "Customer Support" and any(
            _phrase(title, words(term)) for term in _SUPPORT_TECHNICAL):
        return False
    if canonical == "Accountant" and any(
            _phrase(title, alias) for alias in _BY_ROLE["Accounting Assistant"]):
        return False
    return True


def match_titles(title: str, requested_roles: list[str]) -> list[dict]:
    """Return one explainable match per requested role, without fuzzy guesses.

    Curated aliases may expand only a recognized role with level/management
    qualifiers. An unknown specialization retains exact phrase matching.
    """
    normalized_title = words(title)
    evidence = []
    for requested in requested_roles:
        # A slash is an explicit alternative, not a requirement for a combined
        # title. Whitespace is required so words such as UI/UX stay intact.
        alternatives = re.split(r"\s+[|/]\s+|\s*;\s*", requested)
        for alternative in alternatives:
            query = words(alternative)
            known = _known_role(query)
            if not known:
                if _phrase(normalized_title, query):
                    evidence.append({"requested_role": requested, "matched_phrase": alternative.strip(),
                                     "kind": "exact", "canonical_role": alternative.strip()})
                    break
                continue
            requested_alias, canonical = known
            candidates = [alias for alias in _BY_ROLE[canonical] if _phrase(normalized_title, alias)]
            matched = next((alias for alias in candidates
                            if _compatible(query, normalized_title, requested_alias, alias, canonical)),
                           None)
            if matched is None:
                continue
            exact = _phrase(normalized_title, query)
            evidence.append({"requested_role": requested,
                             "matched_phrase": alternative.strip() if exact else matched,
                             "kind": "exact" if exact else "synonym_translation",
                             "canonical_role": canonical})
            break
    return evidence
