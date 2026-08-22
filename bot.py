import asyncio
import json
import logging
import os
import random
import re
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

dp = Dispatcher()


VERBS = {
    "fahren": {
        "praeteritum": "fuhr",
        "partizip": "gefahren",
        "aux": "ist",
        "du": "fährst",
        "er": "fährt",
        "ihr": "fahrt",
        "definition": "sich mit einem Fahrzeug bewegen",
        "example": "Ich fahre jeden Morgen mit dem Bus.",
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
            (["Ihr ___ mit dem Taxi.", "Letzte Woche ___ sie nach Wien.", "Paul ___ mit dem Bus ___."], ["fahrt", "fuhr", "ist gefahren"]),
        ],
    },
    "gehen": {
        "praeteritum": "ging",
        "partizip": "gegangen",
        "aux": "ist",
        "du": "gehst",
        "er": "geht",
        "ihr": "geht",
        "definition": "sich zu Fuß bewegen",
        "example": "Wir gehen nach dem Kurs nach Hause.",
        "present": [
            ("Er ___ heute früh nach Hause.", "geht"),
            ("Du ___ zu Fuß zur Arbeit.", "gehst"),
        ],
        "praet_order": [
            ["Nach", "dem", "Essen", "ging", "Tom", "spazieren."],
            ["Gestern", "gingen", "wir", "früh", "nach", "Hause."],
        ],
        "perf_order": [
            ["Sie", "ist", "allein", "nach", "Hause", "gegangen."],
            ["Wir", "sind", "am", "Fluss", "spazieren", "gegangen."],
        ],
        "error": [
            ("Du gehstet jeden Tag zu Fuß.", "gehst", "Du gehst jeden Tag zu Fuß."),
            ("Wir haben früh nach Hause gegangen.", "sind gegangen", "Wir sind früh nach Hause gegangen."),
        ],
        "fill": [
            (["Du ___ heute zu Fuß.", "Gestern ___ er ins Kino.", "Wir ___ nach Hause ___."], ["gehst", "ging", "sind gegangen"]),
            (["Ihr ___ in den Park.", "Am Abend ___ sie spazieren.", "Lena ___ schon ___."], ["geht", "ging", "ist gegangen"]),
        ],
    },
    "kommen": {
        "praeteritum": "kam",
        "partizip": "gekommen",
        "aux": "ist",
        "du": "kommst",
        "er": "kommt",
        "ihr": "kommt",
        "definition": "ein Ziel erreichen oder irgendwo eintreffen",
        "example": "Der Zug kommt um acht Uhr an.",
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
            ("Sie hat um neun Uhr gekommen.", "ist gekommen", "Sie ist um neun Uhr gekommen."),
        ],
        "fill": [
            (["Du ___ um acht Uhr.", "Gestern ___ er später.", "Wir ___ pünktlich ___."], ["kommst", "kam", "sind gekommen"]),
            (["Ihr ___ direkt aus Berlin.", "Am Montag ___ sie zu Besuch.", "Lena ___ allein ___."], ["kommt", "kam", "ist gekommen"]),
        ],
    },
    "sehen": {
        "praeteritum": "sah",
        "partizip": "gesehen",
        "aux": "hat",
        "du": "siehst",
        "er": "sieht",
        "ihr": "seht",
        "definition": "etwas mit den Augen wahrnehmen",
        "example": "Ich sehe den Film heute zum ersten Mal.",
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
            (["Ihr ___ den Bahnhof.", "Im Urlaub ___ sie das Meer.", "Lena ___ alles ___."], ["seht", "sah", "hat gesehen"]),
        ],
    },
    "lesen": {
        "praeteritum": "las",
        "partizip": "gelesen",
        "aux": "hat",
        "du": "liest",
        "er": "liest",
        "ihr": "lest",
        "definition": "geschriebene Zeichen verstehen",
        "example": "Am Wochenende lese ich gern lange Artikel.",
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
            ("Sie ist den Brief schon gelesen.", "hat gelesen", "Sie hat den Brief schon gelesen."),
        ],
        "fill": [
            (["Du ___ eine Nachricht.", "Gestern ___ er die Zeitung.", "Wir ___ den Text ___."], ["liest", "las", "haben gelesen"]),
            (["Ihr ___ das Kapitel.", "Im Zug ___ sie ein Buch.", "Lena ___ die E-Mail ___."], ["lest", "las", "hat gelesen"]),
        ],
    },
    "schreiben": {
        "praeteritum": "schrieb",
        "partizip": "geschrieben",
        "aux": "hat",
        "du": "schreibst",
        "er": "schreibt",
        "ihr": "schreibt",
        "definition": "Wörter oder Texte mit Zeichen festhalten",
        "example": "Ich schreibe meiner Freundin eine Nachricht.",
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
            (["Ihr ___ die Antworten.", "Am Abend ___ sie eine E-Mail.", "Lena ___ den Bericht ___."], ["schreibt", "schrieb", "hat geschrieben"]),
        ],
    },
    "sprechen": {
        "praeteritum": "sprach",
        "partizip": "gesprochen",
        "aux": "hat",
        "du": "sprichst",
        "er": "spricht",
        "ihr": "sprecht",
        "definition": "mit der Stimme Gedanken ausdrücken",
        "example": "Im Unterricht sprechen wir nur Deutsch.",
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
            ("Sie ist mit dem Arzt gesprochen.", "hat gesprochen", "Sie hat mit dem Arzt gesprochen."),
        ],
        "fill": [
            (["Du ___ sehr leise.", "Gestern ___ er mit Anna.", "Wir ___ darüber ___."], ["sprichst", "sprach", "haben gesprochen"]),
            (["Ihr ___ über die Reise.", "Am Montag ___ sie mit dem Chef.", "Lena ___ mit ihm ___."], ["sprecht", "sprach", "hat gesprochen"]),
        ],
    },
    "nehmen": {
        "praeteritum": "nahm",
        "partizip": "genommen",
        "aux": "hat",
        "du": "nimmst",
        "er": "nimmt",
        "ihr": "nehmt",
        "definition": "etwas greifen, auswählen oder benutzen",
        "example": "Ich nehme morgens immer den Bus.",
        "present": [
            ("Er ___ morgens den Bus.", "nimmt"),
            ("Ihr ___ noch ein Stück Kuchen.", "nehmt"),
        ],
        "praet_order": [
            ["Gestern", "nahm", "ich", "ein", "Taxi."],
            ["Zum", "Frühstück", "nahm", "sie", "nur", "Kaffee."],
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
            (["Ihr ___ die blaue Linie.", "Am Morgen ___ sie den Zug.", "Lena ___ meinen Stift ___."], ["nehmt", "nahm", "hat genommen"]),
        ],
    },
    "geben": {
        "praeteritum": "gab",
        "partizip": "gegeben",
        "aux": "hat",
        "du": "gibst",
        "er": "gibt",
        "ihr": "gebt",
        "definition": "jemandem etwas überreichen",
        "example": "Die Lehrerin gibt uns eine neue Aufgabe.",
        "present": [
            ("Du ___ mir bitte das Buch.", "gibst"),
            ("Er ___ der Kollegin einen Tipp.", "gibt"),
        ],
        "praet_order": [
            ["Gestern", "gab", "mir", "Anna", "einen", "Tipp."],
            ["Der", "Kellner", "gab", "uns", "die", "Speisekarte."],
        ],
        "perf_order": [
            ["Sie", "hat", "mir", "eine", "klare", "Antwort", "gegeben."],
            ["Wir", "haben", "dem", "Fahrer", "das", "Geld", "gegeben."],
        ],
        "error": [
            ("Du gebst mir das Wörterbuch.", "gibst", "Du gibst mir das Wörterbuch."),
            ("Er ist mir einen Rat gegeben.", "hat gegeben", "Er hat mir einen Rat gegeben."),
        ],
        "fill": [
            (["Du ___ mir das Buch.", "Gestern ___ er mir einen Tipp.", "Wir ___ ihr eine Antwort ___."], ["gibst", "gab", "haben gegeben"]),
            (["Ihr ___ dem Kind Wasser.", "Am Abend ___ sie uns den Schlüssel.", "Lena ___ ihm das Geld ___."], ["gebt", "gab", "hat gegeben"]),
        ],
    },
    "essen": {
        "praeteritum": "aß",
        "partizip": "gegessen",
        "aux": "hat",
        "du": "isst",
        "er": "isst",
        "ihr": "esst",
        "definition": "Nahrung zu sich nehmen",
        "example": "Mittags esse ich meistens in der Kantine.",
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
            ("Sie ist schon zu Mittag gegessen.", "hat gegessen", "Sie hat schon zu Mittag gegessen."),
        ],
        "fill": [
            (["Du ___ einen Apfel.", "Gestern ___ er eine Pizza.", "Wir ___ schon ___."], ["isst", "aß", "haben gegessen"]),
            (["Ihr ___ heute zu Hause.", "Am Abend ___ sie eine Suppe.", "Lena ___ noch nichts ___."], ["esst", "aß", "hat gegessen"]),
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


def next_markup(mode: str, has_more: bool = True) -> InlineKeyboardMarkup:
    if mode == "review":
        label = "Nächste Wiederholung" if has_more else "Zum Menü"
    else:
        label = "Weiter"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="flow:next")],
            [InlineKeyboardButton(text="Training beenden", callback_data="menu:home")],
        ]
    )


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
        f"<b>{verb_key}</b> – {verb['definition']}\n\n"
        f"Infinitiv: <b>{verb_key}</b>\n"
        f"Präteritum: <b>{verb['praeteritum']}</b>\n"
        f"Partizip II: <b>{verb['partizip']}</b>\n"
        f"Perfekt: <b>{verb['aux']} {verb['partizip']}</b>\n\n"
        f"du <b>{verb['du']}</b> · er/sie/es <b>{verb['er']}</b> · ihr <b>{verb['ihr']}</b>\n\n"
        f"Beispiel: <i>{verb['example']}</i>"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Übungen starten", callback_data="flow:next")]]
    )
    await message.answer(text, reply_markup=markup)


def form_keyboard(forms: list[str], selected: list[int]) -> InlineKeyboardMarkup | None:
    buttons = [
        InlineKeyboardButton(text=form, callback_data=f"form:{index}")
        for index, form in enumerate(forms)
        if index not in selected
    ]
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons])


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
    pool = {answer}
    while len(pool) < 4:
        other = VERBS[random.choice(list(VERBS))]
        pool.add(random.choice([other["du"], other["er"], other["ihr"]]))
    options = list(pool)
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


def word_keyboard(words: list[str], selected: list[int]) -> InlineKeyboardMarkup | None:
    buttons = [
        InlineKeyboardButton(text=word, callback_data=f"word:{index}")
        for index, word in enumerate(words)
        if index not in selected
    ]
    if not buttons:
        return None
    rows = [buttons[index:index + 3] for index in range(0, len(buttons), 3)]
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


async def send_result(message: Message, user_id: int, correct: bool, correct_text: str) -> None:
    session = SESSIONS[user_id]
    task = session["task"]
    verb_key = session["verb"]
    variant = int(session.get("variant", 0))
    register_result(user_id, correct, task, verb_key, variant)
    session["round_total"] += 1
    if correct:
        session["round_correct"] += 1
        text = "<b>Richtig.</b>"
    else:
        text = f"<b>Noch nicht.</b>\n\nRichtig: {correct_text}\n\nDiese Form kommt in die Wiederholung."
    has_more = bool(user_stats(user_id)["mistakes"])
    session["awaiting"] = None
    await message.answer(text, reply_markup=next_markup(session["mode"], has_more))


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
    if len(session["selected"]) == 3:
        correct = selected_forms == session["target"]
        answer = " → ".join(session["target"])
        await send_result(callback.message, user_id, correct, answer)


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
    await send_result(callback.message, user_id, correct, f"<b>{session['answer']}</b>")


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
    if len(session["selected"]) == len(session["words"]):
        correct = selected_words == session["target"]
        answer = " ".join(session["target"])
        await send_result(callback.message, user_id, correct, f"<i>{answer}</i>")


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
        )
        return

    if session["awaiting"] == "fill_text":
        parts = [normalize(part) for part in re.split(r"[,;\n]+", message.text or "") if part.strip()]
        expected = [normalize(answer) for answer in session["answers"]]
        correct = parts == expected
        answer_text = " · ".join(f"<b>{answer}</b>" for answer in session["answers"])
        await send_result(message, user_id, correct, answer_text)
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
