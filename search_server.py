
import json
import os
import re
import time
import math
from difflib import SequenceMatcher
from collections import Counter

from flask import Flask, request, render_template_string

app = Flask(__name__)

INDEX_FILE = "zero_index.json"
KNOWLEDGE_FILE = "zero_knowledge.json"

index = []
last_index_mtime = 0
vocabulary = Counter()

knowledge = {
    "queries": {},
    "relations": {},
    "learned_words": {}
}


# =====================================
# DATA
# =====================================

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, data):
    temp = path + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(temp, path)


def load_knowledge():
    global knowledge

    data = load_json(KNOWLEDGE_FILE, {})

    knowledge = {
        "queries": data.get("queries", {}),
        "relations": data.get("relations", {}),
        "learned_words": data.get("learned_words", {})
    }


def tokenize(text):
    return re.findall(
        r"[a-zа-яіїєґ0-9]+",
        str(text).lower()
    )


def normalize_query(query):
    return " ".join(tokenize(query))


def load_index():
    global index, last_index_mtime, vocabulary

    try:
        mtime = os.path.getmtime(INDEX_FILE)

        if mtime == last_index_mtime:
            return

        data = load_json(INDEX_FILE, [])

        if isinstance(data, dict):
            data = data.get("pages", [])

        if not isinstance(data, list):
            return

        index = data
        last_index_mtime = mtime

        # Build vocabulary from the whole index.
        words = Counter()

        for page in index:
            title = str(page.get("title", ""))
            description = str(page.get("description", ""))
            text = str(page.get("text", ""))

            words.update(tokenize(text))
            words.update(tokenize(description))
            words.update(tokenize(title))

        vocabulary = words

        print("INDEX UPDATED:", len(index), "pages")
        print("VOCABULARY:", len(vocabulary), "words")

    except OSError:
        index = []
        vocabulary = Counter()


# =====================================
# AUTOMATIC TRANSLITERATION
# =====================================

TRANSLITERATION = {
    "а": "a", "б": "b", "в": "v", "г": "h",
    "ґ": "g", "д": "d", "е": "e", "є": "ye",
    "ж": "zh", "з": "z", "и": "y", "і": "i",
    "ї": "yi", "й": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "",
    "ю": "yu", "я": "ya",
    "ы": "y", "э": "e", "ё": "yo"
}


def transliterate(word):
    result = ""

    for char in word.lower():
        result += TRANSLITERATION.get(char, char)

    return result


# =====================================
# LEARNING ENGINE
# =====================================

def find_word_candidates(word):
    if len(word) < 4:
        return []

    source = transliterate(word)
    candidates = []

    for candidate, frequency in vocabulary.items():

        if candidate == word:
            continue

        if len(candidate) < 4 or frequency < 2:
            continue

        target = transliterate(candidate)

        similarity = SequenceMatcher(
            None,
            source,
            target
        ).ratio()

        if similarity >= 0.68:
            # A small frequency bonus helps rank common
            # words above rare accidental matches.
            score = similarity + min(
                0.04,
                math.log1p(frequency) * 0.006
            )

            candidates.append({
                "word": candidate,
                "similarity": round(similarity, 3),
                "frequency": frequency,
                "score": score
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates[:5]


def learn_word(word):
    if len(word) < 4:
        return None

    # Reuse a previously learned relation.
    saved = knowledge["learned_words"].get(word)

    if saved:
        candidate = saved.get("word")

        if candidate in vocabulary:
            return candidate

    candidates = find_word_candidates(word)

    if not candidates:
        return None

    best = candidates[0]

    # Avoid learning if the best candidates are too similar
    # to each other. That would make the result ambiguous.
    if len(candidates) > 1:
        difference = best["score"] - candidates[1]["score"]

        if difference < 0.025:
            return None

    if best["similarity"] < 0.68:
        return None

    knowledge["learned_words"][word] = {
        "word": best["word"],
        "confidence": best["similarity"],
        "frequency": best["frequency"],
        "learned_at": int(time.time())
    }

    print(
        "LEARNED:",
        word,
        "->",
        best["word"],
        "confidence:",
        best["similarity"]
    )

    return best["word"]


def expand_query(query):
    words = tokenize(query)
    expanded = set(words)

    for word in words:
        candidate = learn_word(word)

        if candidate:
            expanded.add(candidate)

    return expanded


def register_query(query, results):
    key = normalize_query(query)

    if not key:
        return

    data = knowledge["queries"].setdefault(
        key,
        {
            "count": 0,
            "last_seen": 0,
            "result_urls": {}
        }
    )

    data["count"] += 1
    data["last_seen"] = int(time.time())

    for page in results[:20]:
        url = str(page.get("url", ""))

        if url:
            data["result_urls"][url] = (
                data["result_urls"].get(url, 0) + 1
            )

    save_json(KNOWLEDGE_FILE, knowledge)


# =====================================
# SEARCH ENGINE
# =====================================

def search(query):
    load_index()

    words = tokenize(query)

    if not words:
        return []

    expanded_words = expand_query(query)

    results = []

    for page in index:
        title = str(page.get("title", "")).lower()
        description = str(page.get("description", "")).lower()
        text = str(page.get("text", "")).lower()

        score = 0

        for word in expanded_words:

            if word in title:
                score += 15

            if word in description:
                score += 7

            if word in text:
                score += min(text.count(word), 10)

        if score > 0:
            results.append((score, page))

    results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    found = [page for score, page in results[:20]]

    register_query(query, found)

    return found


# =====================================
# WEBSITE
# =====================================

HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>ZERO Search</title>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    padding: 35px 20px;
    background: #071426;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 850px;
    margin: auto;
}

.logo {
    color: #268cff;
    font-size: 48px;
    font-weight: bold;
    text-align: center;
    letter-spacing: 8px;
    margin-bottom: 25px;
}

.search {
    display: flex;
    gap: 10px;
}

input {
    flex: 1;
    min-width: 0;
    padding: 16px;
    border: 1px solid #1b4775;
    border-radius: 12px;
    background: #10243e;
    color: white;
    font-size: 16px;
    outline: none;
}

button {
    border: 0;
    border-radius: 12px;
    padding: 0 23px;
    background: #147bff;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

.result {
    background: #10243e;
    border: 1px solid #1c3b60;
    border-radius: 12px;
    padding: 18px;
    margin-top: 15px;
}

.result a {
    color: #48a0ff;
    font-size: 19px;
    text-decoration: none;
}

.url {
    color: #64c7a0;
    font-size: 12px;
    margin: 7px 0;
    overflow-wrap: anywhere;
}

.description {
    color: #b8c8da;
    line-height: 1.5;
}

.stats {
    margin-top: 25px;
    color: #6685a8;
    font-size: 13px;
}

@media(max-width: 500px) {
    .search { flex-direction: column; }
    button { padding: 15px; }
}
</style>
</head>

<body>
<div class="container">

<div class="logo">ZERO</div>

<form class="search" method="GET">
    <input
        name="q"
        value="{{ query }}"
        placeholder="Що шукаємо?"
        autocomplete="off"
    >
    <button type="submit">SEARCH</button>
</form>

{% if query %}
<div class="stats">
    Запит: {{ query }} · Результатів: {{ results|length }}
</div>
{% endif %}

{% for page in results %}
<div class="result">

    <a href="{{ page.url }}" target="_blank">
        {{ page.title or page.url }}
    </a>

    <div class="url">{{ page.url }}</div>

    <div class="description">
        {{ page.description or page.text[:250] }}
    </div>

</div>
{% endfor %}

{% if query and not results %}
<div class="result">
    Нічого не знайдено. ZERO продовжує навчатися.
</div>
{% endif %}

</div>
</body>
</html>
"""


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    results = search(query) if query else []

    return render_template_string(
        HTML,
        query=query,
        results=results
    )


@app.route("/stats")
def stats():
    load_index()

    return {
        "indexed_pages": len(index),
        "vocabulary_size": len(vocabulary),
        "known_queries": len(knowledge["queries"]),
        "learned_words": knowledge["learned_words"],
        "relations": knowledge["relations"]
    }


if __name__ == "__main__":
    load_index()
    load_knowledge()

    print("ZERO SEARCH v0.5")
    print("Automatic Learning: ON")
    print("Open http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
