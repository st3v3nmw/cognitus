import logging
import re
import os
import sqlite3

import requests
from anki.collection import Collection
from anki.notes import Note
from dotenv import load_dotenv
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import var
from textual.widgets import Button, DataTable, Header, Input, Static
from thefuzz import fuzz

load_dotenv()
logging.basicConfig(
    filename="cognitus.log",
    filemode="a",
    format="%(message)s",
    level=logging.DEBUG,
)

PROMPT = """
Generate a large set of concise, atomic flashcards on %s.

The format should be:
Question? (A single, specific question or concept)
:::
Answer. (A brief, clear explanation or answer)

Create as many flashcards as possible, covering:
- Key terms and definitions
- Core principles
- Important facts
- Cause-and-effect relationships
- Distinguishing features between related concepts
- Historical basis
- Critiques
- Common misconceptions

Ensure each flashcard focuses on a single, discrete piece of information.
Avoid enumerated answers, and flashcards like "what is the main X",
"what is the most common", etc.
For math equations, use the format: <anki-mathjax>equation</anki-mathjax>.
Wrap code in italics <i>code</i>
Your response MUST only contain flashcards.
"""

anki = Collection(os.environ["ANKI_COLLECTION_PATH"])
anki.decks.set_current = anki.decks.id_for_name("Library")

db_conn = sqlite3.connect("db.sqlite3")
db_cursor = db_conn.cursor()
db_cursor.execute(
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
        id UNINDEXED,
        body,
    )
    """
)


def clean_string(text: str) -> str:
    return re.sub("[^A-Za-z0-9 ]+", "", text)


def sync_db_with_anki():
    all_anki_note_ids = set(anki.find_notes(""))
    db_cursor.execute("SELECT DISTINCT id FROM cards_fts")
    sqlite_note_ids = set(row[0] for row in db_cursor.fetchall())

    deleted_note_ids = sqlite_note_ids - all_anki_note_ids
    if len(deleted_note_ids) > 0:
        for note_id in deleted_note_ids:
            db_cursor.execute("DELETE FROM cards_fts WHERE id = ?", (note_id,))

    new_note_ids = all_anki_note_ids - sqlite_note_ids
    new_notes = [anki.get_note(nid) for nid in new_note_ids]
    for note in new_notes:
        db_cursor.execute(
            "INSERT OR REPLACE INTO cards_fts (id, body) VALUES (?, ?)",
            (
                note.id,
                clean_string(f"{note["Front"]} {note["Back"]}")
            ),
        )

    db_conn.commit()


def process_new_card(topic, front, back) -> bool:
    body = clean_string(f"{front} {back}")
    query = f"SELECT * FROM cards_fts(?)"
    db_cursor.execute(query, (body,))
    existing = db_cursor.fetchone()

    if existing:
        ratio = fuzz.ratio(body, existing[1])
        if ratio >= 90:
            logging.debug(
                f"Similar card found: {existing}, new: {body}, ratio: {ratio}",
            )
            return False

    new_card = Note(anki, anki.models.by_name("Cognitus"))
    new_card["Topic"] = topic
    new_card["Front"] = front
    new_card["Back"] = back
    anki.add_note(new_card, anki.decks.get_current_id())

    db_cursor.execute(
        "INSERT INTO cards_fts (id, body) VALUES (?, ?)",
        (new_card.id, body),
    )
    db_conn.commit()

    print(f"New card inserted: {body}")
    return True


def call_open_router(topic: str) -> str:
    api_key = os.environ["OPENROUTER_API_KEY"]
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": "anthropic/claude-3.5-sonnet",
            "prompt": PROMPT % topic,
        },
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    return response.json()["choices"][0]["text"]


class Cognitus(App):
    CSS = """
        Input {
            width: 1fr;
            margin-right: 1;
        }

        Button {
            width: 15;
            margin-right: 1;
        }

        DataTable {
            height: 90%;
        }
    """

    topic = var("")

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            yield Input(
                placeholder="Topic to generate flashcards for", id="topic-input"
            )
            yield Button("Generate", variant="primary", id="generate-cards")
            yield Button("Save", variant="primary", id="save-cards")

        yield DataTable(zebra_stripes=True)

    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        self.table.add_column("Question", width=90)
        self.table.add_column("Answer", width=90)
        self.table.add_column("Op", width=4)

    @on(Button.Pressed, "#generate-cards")
    def on_generate_cards(self) -> None:
        self.topic = self.query_one("#topic-input").value.strip()
        if len(self.topic) == 0:
            self.notify("Please provide a topic.", severity="warning")
            return

        self.table.clear()

        response = call_open_router(self.topic)
        cards = re.findall(r"^(.*)\n:::\n(.*)$", response, flags=re.MULTILINE)
        for card in cards:
            self.table.add_row(*card, "rm", height=3)

    @on(Button.Pressed, "#save-cards")
    def on_save_cards(self) -> None:
        n_cards = len(self.table.rows)
        if n_cards == 0:
            self.notify("Please generate some cards.", severity="warning")
            return

        cards = [self.table.get_row_at(i)[:2] for i in range(n_cards)]
        for card in cards:
            process_new_card(self.topic, card[0], card[1])

        self.table.clear()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        if event.coordinate.column == 2:
            key = self.table.coordinate_to_cell_key(event.coordinate)
            self.table.remove_row(key.row_key)


sync_db_with_anki()

app = Cognitus()
app.run()

anki.close()
db_conn.close()
