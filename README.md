# Cognitus

Cognitus is a script to generate flashcards on a topic and sync them to Anki.

## Setup

- Clone this repository: `git clone git@github.com:st3v3nmw/cognitus.git`
- Create the virtual environment with [Poetry](https://python-poetry.org/docs/basic-usage/): `poetry shell`
- Install the project's dependencies: `poetry install`
- Create a `.env` file with entries for `OPENROUTER_API_KEY` & `ANKI_COLLECTION_PATH`
    - The Anki collection path depends on your installation method. For instance, mine was at `/home/stephen/.var/app/net.ankiweb.Anki/data/Anki2/Stephen/collection.anki2` after installing with the [tarball](https://docs.ankiweb.net/platform/linux/installing.html)
- You can change the prompt if you wish by editing `PROMPT` in `cognitus.py`. This is the default:

```
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
```

`%s` is a placeholder for the topic and it must always be present in the prompt.

## Usage

When using the script, Anki should not be running. The script accesses the Anki collection database directly.
If Anki is already running, the database is locked and no other client can connect to it.

- Run `python cognitus.py` to launch the TUI. Make sure that the environment is activated (see steps above)
- Next, type in the topic and click `Generate`
- After a few seconds, the list of question & answer pairs will appear
- This approach generates a lot of flashcards and we need to weed out those we don't want. You can do this by clicking `rm` in the adjacent `Op` column.
- After you're done, click `Save`
