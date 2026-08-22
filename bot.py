import asyncio
import html
import json
import logging
import os
import random
import re
import secrets
import urllib.request
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN fehlt.")

KIE_API_KEY = os.getenv("KIE_API_KEY")
KIE_API_URL = "https://api.kie.ai/gemini-3-5-flash-openai/v1/chat/completions"

dp = Dispatcher()


VERBS = {
    "fahren": {
        "translation": "ехать",
        "distractors": ["fährt", "fahrt", "fahrst", "fuhrst"],
        "praeteritum": "fuhr",
        "partizip": "gefahren",
        "aux": "ist",
        "du": "fährst",
        "er": "fährt",
        "ihr": "fahrt",
        "definition": "sich mit einem Fahrzeug bewegen",
        "examples": [
            "Mia fährt jeden Morgen mit dem Bus.",
            "Gestern fuhr Mia mit dem Bus.",
            "Mia ist mit dem Bus gefahren.",
        ],
        "present": [
            ("Du ___ jeden Morgen mit dem Bus.", "fährst"),
            ("Ihr ___ am Wochenende nach Berlin.", "fahrt"),
        ],
        "praet_order": [
            ["Gestern", "fuhr", "Mia", "mit", "dem", "Bus."],
            ["Am", "Samstag", "fuhr", "Paul", "ans", "Meer."],
        ],
        "perf_order": [
            ["Wir", "sind", "gestern", "nach", "Bonn", "gefahren."],
            ["Lena", "ist", "mit", "dem", "Zug", "gefahren."],
        ],
        "error": [
            ("Du fahrst heute mit dem Fahrrad.", "fährst", "Du fährst heute mit dem Fahrrad."),
            ("Er hat nach Hamburg gefahren.", "ist gefahren", "Er ist nach Hamburg gefahren."),
        ],
        "fill": [
            (["Du ___ heute zur Arbeit.", "Gestern ___ er nach Köln.", "Wir ___ nach Hause ___."], ["fährst", "fuhr", "sind gefahren"]),
            (["Ihr ___ mit dem Taxi.", "Letzte Woche ___ Nora nach Wien.", "Paul ___ mit dem Bus ___."], ["fahrt", "fuhr", "ist gefahren"]),
        ],
    },
    "gehen": {
        "translation": "идти",
        "distractors": ["geht", "ging", "gingst", "gegangen"],
        "praeteritum": "ging",
        "partizip": "gegangen",
        "aux": "ist",
        "du": "gehst",
        "er": "geht",
        "ihr": "geht",
        "definition": "sich zu Fuß bewegen",
        "examples": [
            "Paul geht nach dem Kurs nach Hause.",
            "Gestern ging Paul früh nach Hause.",
            "Paul ist früh nach Hause gegangen.",
        ],
        "present": [
            ("Er ___ heute früh nach Hause.", "geht"),
            ("Du ___ zu Fuß zur Arbeit.", "gehst"),
        ],
        "praet_order": [
            ["Nach", "dem", "Essen", "ging", "Tom", "spazieren."],
            ["Gestern", "gingen", "wir", "früh", "nach", "Hause."],
        ],
        "perf_order": [
            ["Mara", "ist", "allein", "nach", "Hause", "gegangen."],
            ["Wir", "sind", "am", "Fluss", "spazieren", "gegangen."],
        ],
        "error": [
            ("Du gehstet jeden Tag zu Fuß.", "gehst", "Du gehst jeden Tag zu Fuß."),
            ("Wir haben früh nach Hause gegangen.", "sind gegangen", "Wir sind früh nach Hause gegangen."),
        ],
        "fill": [
            (["Du ___ heute zu Fuß.", "Gestern ___ er ins Kino.", "Wir ___ nach Hause ___."], ["gehst", "ging", "sind gegangen"]),
            (["Ihr ___ in den Park.", "Am Abend ___ Anna spazieren.", "Lena ___ schon ___."], ["geht", "ging", "ist gegangen"]),
        ],
    },
    "kommen": {
        "translation": "приходить",
        "distractors": ["kommt", "kam", "kamst", "gekommen"],
        "praeteritum": "kam",
        "partizip": "gekommen",
        "aux": "ist",
        "du": "kommst",
        "er": "kommt",
        "ihr": "kommt",
        "definition": "ein Ziel erreichen oder irgendwo eintreffen",
        "examples": [
            "Nora kommt um acht Uhr.",
            "Gestern kam Nora um acht Uhr.",
            "Nora ist um acht Uhr gekommen.",
        ],
        "present": [
            ("Du ___ heute pünktlich zum Unterricht.", "kommst"),
            ("Ihr ___ gerade aus der Schule.", "kommt"),
        ],
        "praet_order": [
            ["Der", "Bus", "kam", "zehn", "Minuten", "später."],
            ["Am", "Abend", "kam", "Nora", "zu", "Besuch."],
        ],
        "perf_order": [
            ["Meine", "Schwester", "ist", "pünktlich", "gekommen."],
            ["Meine", "Freunde", "sind", "gestern", "gekommen."],
        ],
        "error": [
            ("Du kommstet heute sehr spät.", "kommst", "Du kommst heute sehr spät."),
            ("Mara hat um neun Uhr gekommen.", "ist gekommen", "Mara ist um neun Uhr gekommen."),
        ],
        "fill": [
            (["Du ___ um acht Uhr.", "Gestern ___ er später.", "Wir ___ pünktlich ___."], ["kommst", "kam", "sind gekommen"]),
            (["Ihr ___ direkt aus Berlin.", "Am Montag ___ Paul zu Besuch.", "Lena ___ allein ___."], ["kommt", "kam", "ist gekommen"]),
        ],
    },
    "sehen": {
        "translation": "видеть",
        "distractors": ["sieht", "seht", "sahst", "gesehen"],
        "praeteritum": "sah",
        "partizip": "gesehen",
        "aux": "hat",
        "du": "siehst",
        "er": "sieht",
        "ihr": "seht",
        "definition": "etwas mit den Augen wahrnehmen",
        "examples": [
            "Tom sieht den Film heute zum ersten Mal.",
            "Gestern sah Tom den Film zum ersten Mal.",
            "Tom hat den Film schon gesehen.",
        ],
        "present": [
            ("Er ___ den neuen Film.", "sieht"),
            ("Ihr ___ das Schild nicht.", "seht"),
        ],
        "praet_order": [
            ["Gestern", "sah", "ich", "einen", "spannenden", "Film."],
            ["Im", "Park", "sahen", "wir", "einen", "Fuchs."],
        ],
        "perf_order": [
            ["Ich", "habe", "diesen", "Film", "schon", "gesehen."],
            ["Habt", "ihr", "meine", "Brille", "gesehen?"],
        ],
        "error": [
            ("Du seht den Fehler sofort.", "siehst", "Du siehst den Fehler sofort."),
            ("Er ist den Film schon gesehen.", "hat gesehen", "Er hat den Film schon gesehen."),
        ],
        "fill": [
            (["Du ___ das rote Haus.", "Gestern ___ er einen Unfall.", "Wir ___ den Film ___."], ["siehst", "sah", "haben gesehen"]),
            (["Ihr ___ den Bahnhof.", "Im Urlaub ___ Nina das Meer.", "Lena ___ alles ___."], ["seht", "sah", "hat gesehen"]),
        ],
    },
    "lesen": {
        "translation": "читать",
        "distractors": ["lest", "las", "lasst", "gelesen"],
        "praeteritum": "las",
        "partizip": "gelesen",
        "aux": "hat",
        "du": "liest",
        "er": "liest",
        "ihr": "lest",
        "definition": "geschriebene Zeichen verstehen",
        "examples": [
            "Anna liest einen langen Artikel.",
            "Gestern las Anna einen langen Artikel.",
            "Anna hat den Artikel schon gelesen.",
        ],
        "present": [
            ("Du ___ jeden Abend im Bett.", "liest"),
            ("Ihr ___ die Aufgabe noch einmal.", "lest"),
        ],
        "praet_order": [
            ["Im", "Zug", "las", "Mia", "einen", "Roman."],
            ["Gestern", "lasen", "wir", "einen", "kurzen", "Text."],
        ],
        "perf_order": [
            ["Ich", "habe", "die", "Nachricht", "schon", "gelesen."],
            ["Paul", "hat", "das", "ganze", "Buch", "gelesen."],
        ],
        "error": [
            ("Du lest die Zeitung jeden Morgen.", "liest", "Du liest die Zeitung jeden Morgen."),
            ("Anna ist den Brief schon gelesen.", "hat gelesen", "Anna hat den Brief schon gelesen."),
        ],
        "fill": [
            (["Du ___ eine Nachricht.", "Gestern ___ er die Zeitung.", "Wir ___ den Text ___."], ["liest", "las", "haben gelesen"]),
            (["Ihr ___ das Kapitel.", "Im Zug ___ Mia ein Buch.", "Lena ___ die E-Mail ___."], ["lest", "las", "hat gelesen"]),
        ],
    },
    "schreiben": {
        "translation": "писать",
        "distractors": ["schreibt", "schrieb", "schriebst", "geschrieben"],
        "praeteritum": "schrieb",
        "partizip": "geschrieben",
        "aux": "hat",
        "du": "schreibst",
        "er": "schreibt",
        "ihr": "schreibt",
        "definition": "Wörter oder Texte mit Zeichen festhalten",
        "examples": [
            "Paul schreibt seiner Kollegin eine Nachricht.",
            "Gestern schrieb Paul seiner Kollegin eine Nachricht.",
            "Paul hat seiner Kollegin eine Nachricht geschrieben.",
        ],
        "present": [
            ("Er ___ eine kurze E-Mail.", "schreibt"),
            ("Du ___ die Antwort ins Heft.", "schreibst"),
        ],
        "praet_order": [
            ["Gestern", "schrieb", "Nina", "einen", "langen", "Brief."],
            ["Im", "Kurs", "schrieben", "wir", "einen", "Dialog."],
        ],
        "perf_order": [
            ["Ich", "habe", "dir", "eine", "Nachricht", "geschrieben."],
            ["Tom", "hat", "den", "Bericht", "schon", "geschrieben."],
        ],
        "error": [
            ("Du schreibet eine E-Mail.", "schreibst", "Du schreibst eine E-Mail."),
            ("Er ist einen langen Text geschrieben.", "hat geschrieben", "Er hat einen langen Text geschrieben."),
        ],
        "fill": [
            (["Du ___ einen Brief.", "Gestern ___ er eine Nachricht.", "Wir ___ einen Dialog ___."], ["schreibst", "schrieb", "haben geschrieben"]),
            (["Ihr ___ die Antworten.", "Am Abend ___ Nora eine E-Mail.", "Lena ___ den Bericht ___."], ["schreibt", "schrieb", "hat geschrieben"]),
        ],
    },
    "sprechen": {
        "translation": "говорить",
        "distractors": ["spricht", "sprecht", "sprechst", "sprachst"],
        "praeteritum": "sprach",
        "partizip": "gesprochen",
        "aux": "hat",
        "du": "sprichst",
        "er": "spricht",
        "ihr": "sprecht",
        "definition": "mit der Stimme Gedanken ausdrücken",
        "examples": [
            "Lena spricht mit ihrer Kollegin.",
            "Gestern sprach Lena mit ihrer Kollegin.",
            "Lena hat mit ihrer Kollegin gesprochen.",
        ],
        "present": [
            ("Du ___ sehr deutlich.", "sprichst"),
            ("Ihr ___ im Unterricht Deutsch.", "sprecht"),
        ],
        "praet_order": [
            ["Gestern", "sprach", "ich", "mit", "meiner", "Chefin."],
            ["Im", "Kurs", "sprachen", "wir", "über", "Reisen."],
        ],
        "perf_order": [
            ["Ich", "habe", "mit", "Paul", "gesprochen."],
            ["Wir", "haben", "lange", "über", "das", "Problem", "gesprochen."],
        ],
        "error": [
            ("Du sprechst schon sehr gut Deutsch.", "sprichst", "Du sprichst schon sehr gut Deutsch."),
            ("Mara ist mit dem Arzt gesprochen.", "hat gesprochen", "Mara hat mit dem Arzt gesprochen."),
        ],
        "fill": [
            (["Du ___ sehr leise.", "Gestern ___ er mit Anna.", "Wir ___ darüber ___."], ["sprichst", "sprach", "haben gesprochen"]),
            (["Ihr ___ über die Reise.", "Am Montag ___ Nina mit dem Chef.", "Lena ___ mit ihm ___."], ["sprecht", "sprach", "hat gesprochen"]),
        ],
    },
    "nehmen": {
        "translation": "брать",
        "distractors": ["nimmt", "nehmt", "nehmst", "nahmst"],
        "praeteritum": "nahm",
        "partizip": "genommen",
        "aux": "hat",
        "du": "nimmst",
        "er": "nimmt",
        "ihr": "nehmt",
        "definition": "etwas greifen, auswählen oder benutzen",
        "examples": [
            "Tom nimmt morgens den Bus.",
            "Gestern nahm Tom den Bus.",
            "Tom hat den Bus genommen.",
        ],
        "present": [
            ("Er ___ morgens den Bus.", "nimmt"),
            ("Ihr ___ noch ein Stück Kuchen.", "nehmt"),
        ],
        "praet_order": [
            ["Gestern", "nahm", "ich", "ein", "Taxi."],
            ["Zum", "Frühstück", "nahm", "Nora", "nur", "Kaffee."],
        ],
        "perf_order": [
            ["Wir", "haben", "den", "frühen", "Zug", "genommen."],
            ["Paul", "hat", "meinen", "Regenschirm", "genommen."],
        ],
        "error": [
            ("Du nehmst heute den Bus.", "nimmst", "Du nimmst heute den Bus."),
            ("Er ist ein Taxi genommen.", "hat genommen", "Er hat ein Taxi genommen."),
        ],
        "fill": [
            (["Du ___ den Schlüssel.", "Gestern ___ er ein Taxi.", "Wir ___ den Bus ___."], ["nimmst", "nahm", "haben genommen"]),
            (["Ihr ___ die blaue Linie.", "Am Morgen ___ Mia den Zug.", "Lena ___ meinen Stift ___."], ["nehmt", "nahm", "hat genommen"]),
        ],
    },
    "geben": {
        "translation": "давать",
        "distractors": ["gibt", "gebt", "gebst", "gabst"],
        "praeteritum": "gab",
        "partizip": "gegeben",
        "aux": "hat",
        "du": "gibst",
        "er": "gibt",
        "ihr": "gebt",
        "definition": "jemandem etwas überreichen",
        "examples": [
            "Anna gibt Paul das Buch.",
            "Gestern gab Anna Paul das Buch.",
            "Anna hat Paul das Buch gegeben.",
        ],
        "present": [
            ("Du ___ mir bitte das Buch.", "gibst"),
            ("Er ___ der Kollegin einen Tipp.", "gibt"),
        ],
        "praet_order": [
            ["Gestern", "gab", "mir", "Anna", "einen", "Tipp."],
            ["Der", "Kellner", "gab", "uns", "die", "Speisekarte."],
        ],
        "perf_order": [
            ["Anna", "hat", "mir", "eine", "klare", "Antwort", "gegeben."],
            ["Wir", "haben", "dem", "Fahrer", "das", "Geld", "gegeben."],
        ],
        "error": [
            ("Du gebst mir das Wörterbuch.", "gibst", "Du gibst mir das Wörterbuch."),
            ("Er ist mir einen Rat gegeben.", "hat gegeben", "Er hat mir einen Rat gegeben."),
        ],
        "fill": [
            (["Du ___ mir das Buch.", "Gestern ___ er mir einen Tipp.", "Wir ___ ihr eine Antwort ___."], ["gibst", "gab", "haben gegeben"]),
            (["Ihr ___ dem Kind Wasser.", "Am Abend ___ Nora uns den Schlüssel.", "Lena ___ ihm das Geld ___."], ["gebt", "gab", "hat gegeben"]),
        ],
    },
    "essen": {
        "translation": "есть",
        "distractors": ["esst", "aß", "aßt", "gegessen"],
        "praeteritum": "aß",
        "partizip": "gegessen",
        "aux": "hat",
        "du": "isst",
        "er": "isst",
        "ihr": "esst",
        "definition": "Nahrung zu sich nehmen",
        "examples": [
            "Mia isst mittags eine Suppe.",
            "Gestern aß Mia eine Suppe.",
            "Mia hat eine Suppe gegessen.",
        ],
        "present": [
            ("Du ___ gern frisches Brot.", "isst"),
            ("Ihr ___ heute in der Kantine.", "esst"),
        ],
        "praet_order": [
            ["Gestern", "aß", "ich", "eine", "große", "Pizza."],
            ["Im", "Restaurant", "aßen", "wir", "eine", "Suppe."],
        ],
        "perf_order": [
            ["Ich", "habe", "heute", "noch", "nichts", "gegessen."],
            ["Die", "Kinder", "haben", "schon", "zu", "Mittag", "gegessen."],
        ],
        "error": [
            ("Du esst jeden Morgen Müsli.", "isst", "Du isst jeden Morgen Müsli."),
            ("Mia ist schon zu Mittag gegessen.", "hat gegessen", "Mia hat schon zu Mittag gegessen."),
        ],
        "fill": [
            (["Du ___ einen Apfel.", "Gestern ___ er eine Pizza.", "Wir ___ schon ___."], ["isst", "aß", "haben gegessen"]),
            (["Ihr ___ heute zu Hause.", "Am Abend ___ Mia eine Suppe.", "Lena ___ noch nichts ___."], ["esst", "aß", "hat gegessen"]),
        ],
    },
}


TASK_LABELS = {
    "forms": "Drei Formen",
    "present": "Präsens",
    "praet_order": "Präteritum",
    "perf_order": "Perfekt",
    "error": "Fehler finden",
    "fill": "Drei Zeiten",
}

SESSIONS = {}
AI_CONTEXTS = {}


def get_data_file() -> Path:
    preferred = Path("/app/data/verbtrainer_progress.json")
    if preferred.parent.exists():
        return preferred
    local = Path("data")
    local.mkdir(exist_ok=True)
    return local / "verbtrainer_progress.json"


DATA_FILE = get_data_file()


def load_stats() -> dict:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


STATS = load_stats()


def save_stats() -> None:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = DATA_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(STATS, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(DATA_FILE)
    except OSError:
        logging.exception("Der Lernfortschritt konnte nicht gespeichert werden.")


def user_stats(user_id: int) -> dict:
    key = str(user_id)
    if key not in STATS:
        STATS[key] = {"correct": 0, "wrong": 0, "mistakes": [], "last_verb": None}
    return STATS[key]


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(".!?")


def menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Training starten", callback_data="menu:train")],
            [InlineKeyboardButton(text="Fehler wiederholen", callback_data="menu:review")],
            [InlineKeyboardButton(text="Fortschritt", callback_data="menu:progress")],
            [InlineKeyboardButton(text="So funktioniert es", callback_data="menu:help")],
        ]
    )


def next_markup(
    mode: str,
    has_more: bool = True,
    ai_request_id: str | None = None,
) -> InlineKeyboardMarkup:
    if mode == "review":
        label = "Nächste Wiederholung" if has_more else "Zum Menü"
    else:
        label = "Weiter"
    rows = []
    if ai_request_id:
        rows.append(
            [InlineKeyboardButton(text="KI-Erklärung", callback_data=f"ai:{ai_request_id}")]
        )
    rows.extend(
        [
            [InlineKeyboardButton(text=label, callback_data="flow:next")],
            [InlineKeyboardButton(text="Training beenden", callback_data="menu:home")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plain_text(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


async def create_ai_explanation(context: dict) -> str:
    if not KIE_API_KEY:
        raise RuntimeError("KIE_API_KEY fehlt.")

    prompt = (
        f"Verb: {context['verb']}\n"
        f"Aufgabentyp: {context['task']}\n"
        f"Antwort der lernenden Person: {context['user_answer']}\n"
        f"Richtige Lösung: {context['correct_answer']}\n\n"
        "Erkläre den Fehler auf Deutsch in zwei bis drei kurzen Sätzen auf Niveau A2–B1. "
        "Nenne danach genau einen neuen Beispielsatz mit demselben Verb. "
        "Keine Übersetzung, keine Überschrift und keine Markdown-Zeichen."
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist eine freundliche, präzise Deutschlehrkraft. "
                    "Erkläre nur den konkreten Grammatikfehler und erfinde keine Regeln."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 180,
        "stream": False,
    }

    def request_explanation() -> str:
        request = urllib.request.Request(
            KIE_API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {KIE_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=35) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        explanation = str(content).strip()
        if not explanation:
            raise RuntimeError("Leere KI-Antwort.")
        return explanation

    return await asyncio.to_thread(request_explanation)


async def show_menu(message: Message) -> None:
    await message.answer(
        "<b>Drei Formen | Deutschtrainer</b>\n\n"
        "Trainiere starke und unregelmäßige Verben im Präsens, Präteritum und Perfekt.",
        reply_markup=menu_markup(),
    )


def register_result(user_id: int, correct: bool, task: str, verb_key: str, variant: int) -> None:
    stats = user_stats(user_id)
    if correct:
        stats["correct"] += 1
    else:
        stats["wrong"] += 1
        mistake = {"verb": verb_key, "task": task, "variant": variant}
        if mistake not in stats["mistakes"]:
            stats["mistakes"].append(mistake)
    save_stats()


def choose_verb(user_id: int) -> str:
    stats = user_stats(user_id)
    choices = [key for key in VERBS if key != stats.get("last_verb")]
    verb_key = random.choice(choices or list(VERBS))
    stats["last_verb"] = verb_key
    save_stats()
    return verb_key


def new_session(user_id: int, mode: str, verb_key: str, task: str | None = None, variant: int = 0) -> dict:
    session = {
        "mode": mode,
        "verb": verb_key,
        "step": -1 if mode == "train" else 0,
        "task": task,
        "variant": variant,
        "awaiting": None,
        "selected": [],
        "round_correct": 0,
        "round_total": 0,
    }
    SESSIONS[user_id] = session
    return session


async def show_card(message: Message, session: dict) -> None:
    verb_key = session["verb"]
    verb = VERBS[verb_key]
    text = (
        "<b>Formenkarte</b>\n\n"
        f"<b>{verb_key}</b> – {verb['translation']}\n"
        f"<b>{verb_key} – {verb['praeteritum']} – {verb['aux']} {verb['partizip']}</b>\n\n"
        "<b>Präsens</b>\n"
        f"du {verb['du']} · er/sie/es {verb['er']} · ihr {verb['ihr']}\n\n"
        "<b>Beispiele</b>\n"
        f"Präsens: <i>{verb['examples'][0]}</i>\n"
        f"Präteritum: <i>{verb['examples'][1]}</i>\n"
        f"Perfekt: <i>{verb['examples'][2]}</i>"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Übungen starten", callback_data="flow:next")]]
    )
    await message.answer(text, reply_markup=markup)


def form_keyboard(forms: list[str], selected: list[int]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=form, callback_data=f"form:{index}")
        for index, form in enumerate(forms)
        if index not in selected
    ]
    rows = [[button] for button in buttons]
    actions = []
    if selected:
        actions.append(InlineKeyboardButton(text="Zurück", callback_data="undo:form"))
    if len(selected) == len(forms):
        actions.append(InlineKeyboardButton(text="Prüfen", callback_data="check:form"))
    if actions:
        rows.append(actions)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def task_forms(message: Message, session: dict) -> None:
    verb_key = session["verb"]
    verb = VERBS[verb_key]
    forms = [verb_key, verb["praeteritum"], verb["partizip"]]
    random.shuffle(forms)
    session.update(
        task="forms",
        awaiting="forms",
        selected=[],
        forms=forms,
        target=[verb_key, verb["praeteritum"], verb["partizip"]],
    )
    await message.answer(
        "<b>1. Drei Formen</b>\n\n"
        "Tippe die Formen in dieser Reihenfolge an:\n"
        "Infinitiv → Präteritum → Partizip II",
        reply_markup=form_keyboard(forms, []),
    )


async def task_present(message: Message, session: dict) -> None:
    verb_key = session["verb"]
    verb = VERBS[verb_key]
    variant = session.get("variant", random.randrange(2))
    prompt, answer = verb["present"][variant]
    candidates = [verb["du"], verb["er"], verb["ihr"], *verb["distractors"]]
    distractors = list(dict.fromkeys(option for option in candidates if option != answer))
    random.shuffle(distractors)
    options = [answer, *distractors[:3]]
    random.shuffle(options)
    session.update(task="present", awaiting="choice", variant=variant, options=options, answer=answer)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=option, callback_data=f"choice:{index}")]
            for index, option in enumerate(options)
        ]
    )
    await message.answer(
        f"<b>2. Präsens</b>\n\nVerb: <b>{verb_key}</b>\n{prompt}",
        reply_markup=keyboard,
    )


def word_keyboard(words: list[str], selected: list[int]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=word, callback_data=f"word:{index}")
        for index, word in enumerate(words)
        if index not in selected
    ]
    rows = [buttons[index:index + 3] for index in range(0, len(buttons), 3)]
    actions = []
    if selected:
        actions.append(InlineKeyboardButton(text="Zurück", callback_data="undo:word"))
    if len(selected) == len(words):
        actions.append(InlineKeyboardButton(text="Prüfen", callback_data="check:word"))
    if actions:
        rows.append(actions)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def task_word_order(message: Message, session: dict, task: str) -> None:
    verb_key = session["verb"]
    verb = VERBS[verb_key]
    variant = session.get("variant", random.randrange(2))
    target = list(verb[task][variant])
    words = list(target)
    while words == target:
        random.shuffle(words)
    title = "3. Präteritum" if task == "praet_order" else "4. Perfekt"
    instruction = "Bilde einen Satz im Präteritum." if task == "praet_order" else "Bilde einen Satz im Perfekt."
    session.update(
        task=task,
        awaiting="words",
        variant=variant,
        words=words,
        target=target,
        selected=[],
        title=title,
        instruction=instruction,
    )
    await message.answer(
        f"<b>{title}</b>\n\n{instruction}\n\nDein Satz: <i>…</i>",
        reply_markup=word_keyboard(words, []),
    )


async def task_error(message: Message, session: dict) -> None:
    verb_key = session["verb"]
    verb = VERBS[verb_key]
    variant = session.get("variant", random.randrange(2))
    wrong, answer, correct_sentence = verb["error"][variant]
    session.update(
        task="error",
        awaiting="error_text",
        variant=variant,
        answer=answer,
        correct_sentence=correct_sentence,
    )
    await message.answer(
        "<b>5. Fehler finden</b>\n\n"
        f"<i>{wrong}</i>\n\n"
        "Schreibe nur die richtige Verbform."
    )


async def task_fill(message: Message, session: dict) -> None:
    verb_key = session["verb"]
    verb = VERBS[verb_key]
    variant = session.get("variant", random.randrange(2))
    prompts, answers = verb["fill"][variant]
    session.update(task="fill", awaiting="fill_text", variant=variant, answers=answers)
    await message.answer(
        "<b>6. Drei Zeiten</b>\n\n"
        f"Setze <b>{verb_key}</b> ein. Schreibe drei Lösungen, getrennt durch Kommas.\n\n"
        f"1. PRÄSENS: {prompts[0]}\n"
        f"2. PRÄTERITUM: {prompts[1]}\n"
        f"3. PERFEKT: {prompts[2]}"
    )


async def render_step(message: Message, user_id: int) -> None:
    session = SESSIONS[user_id]
    if session["mode"] == "review":
        task = session["task"]
    else:
        tasks = ["forms", "present", "praet_order", "perf_order", "error", "fill"]
        if session["step"] >= len(tasks):
            await finish_round(message, user_id)
            return
        task = tasks[session["step"]]
        session["variant"] = random.randrange(2)

    if task == "forms":
        await task_forms(message, session)
    elif task == "present":
        await task_present(message, session)
    elif task in {"praet_order", "perf_order"}:
        await task_word_order(message, session, task)
    elif task == "error":
        await task_error(message, session)
    elif task == "fill":
        await task_fill(message, session)


async def finish_round(message: Message, user_id: int) -> None:
    session = SESSIONS[user_id]
    total = session["round_total"]
    correct = session["round_correct"]
    stats = user_stats(user_id)
    await message.answer(
        "<b>Runde beendet</b>\n\n"
        f"Richtig: <b>{correct} von {total}</b>\n"
        f"In der Wiederholung: <b>{len(stats['mistakes'])}</b>",
        reply_markup=menu_markup(),
    )
    SESSIONS.pop(user_id, None)


async def show_progress(message: Message, user_id: int) -> None:
    stats = user_stats(user_id)
    total = stats["correct"] + stats["wrong"]
    rate = round(stats["correct"] / total * 100) if total else 0
    await message.answer(
        "<b>Dein Fortschritt</b>\n\n"
        f"Bearbeitete Aufgaben: <b>{total}</b>\n"
        f"Richtig: <b>{stats['correct']}</b>\n"
        f"Trefferquote: <b>{rate} %</b>\n"
        f"Offene Wiederholungen: <b>{len(stats['mistakes'])}</b>",
        reply_markup=menu_markup(),
    )


async def start_review(message: Message, user_id: int) -> None:
    stats = user_stats(user_id)
    if not stats["mistakes"]:
        SESSIONS.pop(user_id, None)
        await message.answer(
            "Im Moment gibt es keine offenen Fehler. Starte eine neue Trainingsrunde.",
            reply_markup=menu_markup(),
        )
        return
    mistake = stats["mistakes"].pop(0)
    save_stats()
    variant = 1 - int(mistake.get("variant", 0))
    new_session(user_id, "review", mistake["verb"], mistake["task"], variant)
    await message.answer(
        f"<b>Wiederholung</b>\n\n"
        f"Verb: <b>{mistake['verb']}</b>\n"
        f"Bereich: {TASK_LABELS[mistake['task']]}"
    )
    await render_step(message, user_id)


async def send_result(
    message: Message,
    user_id: int,
    correct: bool,
    correct_text: str,
    user_answer: str = "",
) -> None:
    session = SESSIONS[user_id]
    task = session["task"]
    verb_key = session["verb"]
    variant = int(session.get("variant", 0))
    register_result(user_id, correct, task, verb_key, variant)
    session["round_total"] += 1
    ai_request_id = None
    if correct:
        session["round_correct"] += 1
        text = "<b>Richtig.</b>"
    else:
        text = f"<b>Noch nicht.</b>\n\nRichtig: {correct_text}\n\nDiese Form kommt in die Wiederholung."
        if KIE_API_KEY:
            ai_request_id = secrets.token_hex(4)
            AI_CONTEXTS[(user_id, ai_request_id)] = {
                "verb": verb_key,
                "task": TASK_LABELS[task],
                "user_answer": plain_text(user_answer) or "keine Antwort",
                "correct_answer": plain_text(correct_text),
            }
    has_more = bool(user_stats(user_id)["mistakes"])
    session["awaiting"] = None
    await message.answer(
        text,
        reply_markup=next_markup(session["mode"], has_more, ai_request_id),
    )


@dp.callback_query(F.data.startswith("ai:"))
async def ai_explanation_callback(callback: CallbackQuery) -> None:
    request_id = callback.data.split(":", 1)[1]
    context = AI_CONTEXTS.pop((callback.from_user.id, request_id), None)
    if not context:
        await callback.answer("Diese Erklärung ist nicht mehr verfügbar.", show_alert=True)
        return
    await callback.answer("Die KI-Erklärung wird erstellt.")
    await callback.message.answer("Einen Moment …")
    try:
        explanation = await create_ai_explanation(context)
        await callback.message.answer(
            f"<b>KI-Erklärung</b>\n\n{html.escape(explanation)}"
        )
    except Exception:
        logging.exception("Die KI-Erklärung konnte nicht erstellt werden.")
        await callback.message.answer(
            "Die KI-Erklärung ist gerade nicht verfügbar. Bitte versuche es später noch einmal."
        )


@dp.message(CommandStart())
async def start_command(message: Message) -> None:
    SESSIONS.pop(message.from_user.id, None)
    await show_menu(message)


@dp.message(Command("training"))
async def training_command(message: Message) -> None:
    user_id = message.from_user.id
    session = new_session(user_id, "train", choose_verb(user_id))
    await show_card(message, session)


@dp.message(Command("wiederholen"))
async def review_command(message: Message) -> None:
    await start_review(message, message.from_user.id)


@dp.message(Command("fortschritt"))
async def progress_command(message: Message) -> None:
    await show_progress(message, message.from_user.id)


@dp.message(Command("hilfe"))
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>So funktioniert das Training</b>\n\n"
        "Jede Runde beginnt mit einer Formenkarte. Danach löst du sechs kurze Aufgaben. "
        "Falsche Formen werden gespeichert und später mit einem anderen Satz wiederholt. "
        "Nach einer falschen Antwort kann dir die KI den Fehler kurz erklären. "
        "Antworte bei Texteingaben nur mit der verlangten Verbform.",
        reply_markup=menu_markup(),
    )


@dp.message(Command("reset"))
async def reset_command(message: Message) -> None:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ja, Fortschritt löschen", callback_data="reset:confirm")],
            [InlineKeyboardButton(text="Abbrechen", callback_data="menu:home")],
        ]
    )
    await message.answer(
        "Fortschritt löschen?",
        reply_markup=markup,
    )


@dp.callback_query(F.data == "reset:confirm")
async def reset_confirm_callback(callback: CallbackQuery) -> None:
    STATS.pop(str(callback.from_user.id), None)
    SESSIONS.pop(callback.from_user.id, None)
    save_stats()
    await callback.answer()
    await callback.message.answer("Dein Lernfortschritt wurde gelöscht.", reply_markup=menu_markup())


@dp.message(Command("datenschutz"))
async def privacy_command(message: Message) -> None:
    await message.answer(
        "Gespeichert werden nur deine Telegram-ID, die Anzahl richtiger und falscher Antworten "
        "sowie offene Wiederholungen. Freie Nachrichten werden nicht gespeichert. "
        "Wenn du eine KI-Erklärung anforderst, werden nur die Aufgabe, deine Antwort und die "
        "richtige Lösung an Kie.ai übermittelt. Dein Name und deine Telegram-ID werden nicht übermittelt. "
        "Mit /reset löschst du deinen Lernfortschritt."
    )


@dp.callback_query(F.data == "menu:home")
async def menu_callback(callback: CallbackQuery) -> None:
    SESSIONS.pop(callback.from_user.id, None)
    await callback.answer()
    await show_menu(callback.message)


@dp.callback_query(F.data == "menu:train")
async def train_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = new_session(user_id, "train", choose_verb(user_id))
    await callback.answer()
    await show_card(callback.message, session)


@dp.callback_query(F.data == "menu:review")
async def review_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await start_review(callback.message, callback.from_user.id)


@dp.callback_query(F.data == "menu:progress")
async def progress_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await show_progress(callback.message, callback.from_user.id)


@dp.callback_query(F.data == "menu:help")
async def help_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await help_command(callback.message)


@dp.callback_query(F.data == "flow:next")
async def next_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)
    await callback.answer()
    if not session:
        await show_menu(callback.message)
        return
    if session["mode"] == "review":
        await start_review(callback.message, user_id)
        return
    session["step"] += 1
    await render_step(callback.message, user_id)


@dp.callback_query(F.data.startswith("form:"))
async def form_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)
    if not session or session.get("awaiting") != "forms":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    index = int(callback.data.split(":", 1)[1])
    if index in session["selected"]:
        await callback.answer()
        return
    session["selected"].append(index)
    selected_forms = [session["forms"][item] for item in session["selected"]]
    await callback.answer()
    await callback.message.edit_text(
        "<b>1. Drei Formen</b>\n\n"
        "Infinitiv → Präteritum → Partizip II\n\n"
        f"Deine Reihenfolge: <b>{' → '.join(selected_forms)}</b>",
        reply_markup=form_keyboard(session["forms"], session["selected"]),
    )


@dp.callback_query(F.data == "undo:form")
async def undo_form_callback(callback: CallbackQuery) -> None:
    session = SESSIONS.get(callback.from_user.id)
    if not session or session.get("awaiting") != "forms":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    if session["selected"]:
        session["selected"].pop()
    selected_forms = [session["forms"][item] for item in session["selected"]]
    selection = " → ".join(selected_forms) if selected_forms else "…"
    await callback.answer()
    await callback.message.edit_text(
        "<b>1. Drei Formen</b>\n\n"
        "Infinitiv → Präteritum → Partizip II\n\n"
        f"Deine Reihenfolge: <b>{selection}</b>",
        reply_markup=form_keyboard(session["forms"], session["selected"]),
    )


@dp.callback_query(F.data == "check:form")
async def check_form_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)
    if not session or session.get("awaiting") != "forms":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    if len(session["selected"]) != len(session["forms"]):
        await callback.answer("Wähle zuerst alle drei Formen.")
        return
    selected_forms = [session["forms"][item] for item in session["selected"]]
    correct = selected_forms == session["target"]
    answer = " → ".join(session["target"])
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_result(
        callback.message,
        user_id,
        correct,
        answer,
        " → ".join(selected_forms),
    )


@dp.callback_query(F.data.startswith("choice:"))
async def choice_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)
    if not session or session.get("awaiting") != "choice":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    index = int(callback.data.split(":", 1)[1])
    answer = session["options"][index]
    correct = normalize(answer) == normalize(session["answer"])
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_result(
        callback.message,
        user_id,
        correct,
        f"<b>{session['answer']}</b>",
        answer,
    )


@dp.callback_query(F.data.startswith("word:"))
async def word_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)
    if not session or session.get("awaiting") != "words":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    index = int(callback.data.split(":", 1)[1])
    if index in session["selected"]:
        await callback.answer()
        return
    session["selected"].append(index)
    selected_words = [session["words"][item] for item in session["selected"]]
    await callback.answer()
    await callback.message.edit_text(
        f"<b>{session['title']}</b>\n\n"
        f"{session['instruction']}\n\n"
        f"Dein Satz: <b>{' '.join(selected_words)}</b>",
        reply_markup=word_keyboard(session["words"], session["selected"]),
    )


@dp.callback_query(F.data == "undo:word")
async def undo_word_callback(callback: CallbackQuery) -> None:
    session = SESSIONS.get(callback.from_user.id)
    if not session or session.get("awaiting") != "words":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    if session["selected"]:
        session["selected"].pop()
    selected_words = [session["words"][item] for item in session["selected"]]
    selection = " ".join(selected_words) if selected_words else "…"
    await callback.answer()
    await callback.message.edit_text(
        f"<b>{session['title']}</b>\n\n"
        f"{session['instruction']}\n\n"
        f"Dein Satz: <b>{selection}</b>",
        reply_markup=word_keyboard(session["words"], session["selected"]),
    )


@dp.callback_query(F.data == "check:word")
async def check_word_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)
    if not session or session.get("awaiting") != "words":
        await callback.answer("Diese Aufgabe ist nicht mehr aktiv.")
        return
    if len(session["selected"]) != len(session["words"]):
        await callback.answer("Bilde zuerst den ganzen Satz.")
        return
    selected_words = [session["words"][item] for item in session["selected"]]
    correct = selected_words == session["target"]
    answer = " ".join(session["target"])
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_result(
        callback.message,
        user_id,
        correct,
        f"<i>{answer}</i>",
        " ".join(selected_words),
    )


@dp.message()
async def text_answer(message: Message) -> None:
    user_id = message.from_user.id
    session = SESSIONS.get(user_id)
    if not session or not session.get("awaiting"):
        await message.answer("Bitte wähle eine Funktion im Menü.", reply_markup=menu_markup())
        return

    if session["awaiting"] == "error_text":
        correct = normalize(message.text or "") == normalize(session["answer"])
        await send_result(
            message,
            user_id,
            correct,
            f"<b>{session['answer']}</b>\n<i>{session['correct_sentence']}</i>",
            message.text or "",
        )
        return

    if session["awaiting"] == "fill_text":
        parts = [normalize(part) for part in re.split(r"[,;\n]+", message.text or "") if part.strip()]
        expected = [normalize(answer) for answer in session["answers"]]
        correct = parts == expected
        answer_text = " · ".join(f"<b>{answer}</b>" for answer in session["answers"])
        await send_result(message, user_id, correct, answer_text, message.text or "")
        return

    await message.answer("Bitte benutze die Schaltflächen unter der Aufgabe.")


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Hauptmenü öffnen"),
            BotCommand(command="training", description="Neue Trainingsrunde"),
            BotCommand(command="wiederholen", description="Fehler wiederholen"),
            BotCommand(command="fortschritt", description="Lernfortschritt anzeigen"),
            BotCommand(command="hilfe", description="Anleitung anzeigen"),
            BotCommand(command="datenschutz", description="Gespeicherte Daten"),
            BotCommand(command="reset", description="Lernfortschritt löschen"),
        ]
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
