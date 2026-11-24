
from flask import Flask, request, render_template_string
import json
import os
import re
import math
import time

app = Flask(__name__)

INDEX_FILE = "zero_index.json"
index = []
last_modified = 0

HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZERO Search</title>
<style>
* {box-sizing:border-box;margin:0;padding:0}
body {
    min-height:100vh;
    background:radial-gradient(circle at 50% 15%,#123765,#071326 60%,#030812);
    color:white;font-family:Arial,sans-serif;
}
header {
    padding:24px 7%;display:flex;justify-content:space-between;
    align-items:center;border-bottom:1px solid #18385e;
}
.logo {font-size:25px;font-weight:900;letter-spacing:5px;color:#65baff}
.label {color:#729cc5;font-size:11px;letter-spacing:2px}
main {width:min(850px,92%);margin:75px auto}
h1 {text-align:center;font-size:clamp(55px,10vw,85px);
letter-spacing:12px;text-shadow:0 0 35px #168cff}
.subtitle {text-align:center;color:#86b9e8;margin:12px 0 35px;
letter-spacing:4px;font-size:12px}
form {display:flex;height:60px;background:#0b1e37;
border:1px solid #2875bd;border-radius:12px;overflow:hidden;
box-shadow:0 0 30px #0875d533}
input {flex:1;min-width:0;padding:0 20px;background:transparent;
border:0;outline:0;color:white;font-size:16px}
input::placeholder {color:#7797b9}
button {width:70px;border:0;background:linear-gradient(135deg,#168cff,#45c4ff);
font-size:23px;cursor:pointer}
.results {margin-top:40px}
.count {color:#789fc5;font-size:13px;margin-bottom:22px}
.result {padding:20px;margin-bottom:14px;background:#0c1e35;
border:1px solid #193d65;border-radius:10px;transition:.2s}
.result:hover {border-color:#45baff;transform:translateY(-2px)}
.result a {color:#72bdff;font-size:19px;font-weight:bold;text-decoration:none}
.result a:hover {text-decoration:underline}
.url {color:#65a7d8;font-size:12px;margin:8px 0;overflow-wrap:anywhere}
.description {color:#a1b9d4;line-height:1.5;font-size:14px}
.empty {text-align:center;padding:35px;color:#8caacb}
footer {text-align:center;padding:25px;color:#52769b;
font-size:11px;letter-spacing:2px}
@media(max-width:500px){main{margin-top:50px}}
</style>
</head>
<body>
<header>
 <div class="logo">ZERO</div>
 <div class="label">SEARCH ENGINE v0.3</div>
</header>
<main>
 <h1>ZERO</h1>
 <div class="subtitle">SEARCH WITHOUT LIMITS</div>
 <form action="/" method="GET">
  <input name="q" value="{{ query }}" placeholder="Що шукаємо?"
  autocomplete="off" autofocus>
  <button type="submit">⌕</button>
 </form>
 <div class="results">
 {% if query %}
  <div class="count">
   Знайдено: {{ results|length }} · ZERO INDEX
  </div>
  {% for result in results %}
  <div class="result">
   <a href="{{ result.url }}" target="_blank" rel="noopener">
    {{ result.title }}
   </a>
   <div class="url">{{ result.url }}</div>
   <div class="description">{{ result.description }}</div>
  </div>
  {% endfor %}
  {% if not results %}
   <div class="empty">Нічого не знайдено. Спробуй інший запит.</div>
  {% endif %}
 {% else %}
  <div class="empty">Введи запит, щоб почати пошук.</div>
 {% endif %}
 </div>
</main>
<footer>ZERO SEARCH · POWERED BY ZERO ENGINE</footer>
</body>
</html>
"""

def load_index():
    global index, last_modified

    if not os.path.exists(INDEX_FILE):
        index = []
        return

    modified = os.path.getmtime(INDEX_FILE)

    if modified != last_modified:
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)
            last_modified = modified
            print("ZERO INDEX LOADED:", len(index), "pages")
        except Exception as error:
            print("INDEX ERROR:", error)

def tokenize(text):
    return re.findall(r"[a-zа-яіїєґ0-9]+", text.lower())

def search(query):
    words = tokenize(query)

    if not words:
        return []

    results = []

    for page in index:
        title = page.get("title", "")
        description = page.get("description", "")
        text = page.get("text", "")

        title_lower = title.lower()
        description_lower = description.lower()
        text_lower = text.lower()

        score = 0

        for word in words:
            if word in title_lower:
                score += 10
            if word in description_lower:
                score += 5
            if word in text_lower:
                score += min(text_lower.count(word), 10)

        if score > 0:
            results.append((score, page))

    results.sort(key=lambda item: item[0], reverse=True)

    return [page for score, page in results[:20]]

@app.route("/")
def home():
    load_index()
    query = request.args.get("q", "").strip()[:150]
    results = search(query) if query else []

    return render_template_string(
        HTML,
        query=query,
        results=results
    )

if __name__ == "__main__":
    load_index()
    print("================================")
    print("       ZERO SEARCH v0.3")
    print("================================")
    print("Indexed pages:", len(index))
    print("Open http://127.0.0.1:5000")

    app.run(host="127.0.0.1", port=5000, debug=False)
