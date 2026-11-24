
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
from collections import deque
import json
import os
import time
import re

USER_AGENT = "ZERO-Crawler/0.3"
INDEX_FILE = "zero_index.json"

MAX_NEW_PAGES = 300
MAX_VISITS = 1500
MAX_PER_DOMAIN = 15
DELAY = 1.2

START_URLS = [
    "https://www.mozilla.org/",
    "https://developer.mozilla.org/",
    "https://www.w3.org/",
    "https://www.nasa.gov/",
    "https://www.noaa.gov/",
    "https://www.britannica.com/",
    "https://www.un.org/",
    "https://www.unesco.org/",
    "https://www.loc.gov/",
    "https://www.si.edu/",
    "https://www.metmuseum.org/",
    "https://www.rfc-editor.org/",
    "https://www.gnu.org/",
    "https://www.debian.org/",
    "https://www.kernel.org/",
    "https://www.djangoproject.com/",
    "https://flask.palletsprojects.com/",
    "https://fastapi.tiangolo.com/",
    "https://www.khanacademy.org/",
    "https://www.openstreetmap.org/",
    "https://www.iana.org/",
    "https://home.cern/",
    "https://www.worldbank.org/",
    "https://www.unicef.org/",
    "https://arxiv.org/",
    "https://www.python.org/",
    "https://github.com/"
]

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

queue = deque()
visited = set()
robots_cache = {}
domain_count = {}
last_request = {}

index = []
known_urls = set()


def load_existing_index():
    global index, known_urls

    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)

            known_urls = {
                page.get("url", "") for page in index
            }

            print("EXISTING PAGES:", len(index))

        except Exception as error:
            print("INDEX LOAD ERROR:", error)
            index = []


def save_index():
    temp_file = INDEX_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

    os.replace(temp_file, INDEX_FILE)


def normalize_url(url):
    url, _ = urldefrag(url)
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    if not parsed.hostname:
        return None

    if parsed.hostname in ("localhost", "127.0.0.1"):
        return None

    if parsed.hostname.endswith(".local"):
        return None

    if parsed.port not in (None, 80, 443):
        return None

    return url


def domain_of(url):
    return urlparse(url).netloc.lower()


def allowed_by_robots(url):
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in robots_cache:
        robots_url = origin + "/robots.txt"

        try:
            response = session.get(
                robots_url,
                timeout=10
            )

            parser = RobotFileParser()
            parser.set_url(robots_url)

            if response.status_code == 404:
                parser.parse([])
            elif response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                robots_cache[origin] = None
                return False

            robots_cache[origin] = parser

        except requests.RequestException:
            robots_cache[origin] = None
            return False

    parser = robots_cache[origin]

    if parser is None:
        return False

    return parser.can_fetch(USER_AGENT, url)


def wait_for_domain(domain):
    previous = last_request.get(domain, 0)
    remaining = DELAY - (time.time() - previous)

    if remaining > 0:
        time.sleep(remaining)

    last_request[domain] = time.time()


def crawl_page(url):
    domain = domain_of(url)

    if not allowed_by_robots(url):
        print("ROBOTS BLOCK:", url)
        return []

    if domain_count.get(domain, 0) >= MAX_PER_DOMAIN:
        return []

    wait_for_domain(domain)

    try:
        response = session.get(
            url,
            timeout=15,
            allow_redirects=True
        )

        response.raise_for_status()

        if len(response.content) > 3_000_000:
            return []

        if "text/html" not in response.headers.get(
            "Content-Type", ""
        ).lower():
            return []

        final_url = normalize_url(response.url)

        if not final_url:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup([
            "script", "style", "noscript",
            "svg", "iframe"
        ]):
            tag.decompose()

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title else final_url
        )

        meta = soup.find(
            "meta",
            attrs={"name": re.compile("^description$", re.I)}
        )

        description = (
            meta.get("content", "")
            if meta else ""
        )

        text = " ".join(soup.get_text(" ", strip=True).split())
        text = text[:12000]

        if final_url not in known_urls:
            index.append({
                "title": title[:300],
                "url": final_url,
                "description": description[:1000],
                "text": text
            })

            known_urls.add(final_url)
            domain_count[domain] = domain_count.get(domain, 0) + 1

            print("INDEXED:", title[:100])

            save_index()

        links = []

        for tag in soup.find_all("a", href=True):
            link = normalize_url(
                urljoin(final_url, tag["href"])
            )

            if link and link not in visited:
                links.append(link)

        return links

    except requests.RequestException as error:
        print("REQUEST ERROR:", url, error)
        return []

    except Exception as error:
        print("ERROR:", url, error)
        return []


def main():
    load_existing_index()

    for url in START_URLS:
        queue.append(url)

    # Використовуємо частину старого індексу
    # як додаткові точки для пошуку посилань.
    for page in index[:40]:
        queue.append(page["url"])

    print("\n==============================")
    print("       ZERO CRAWLER v0.3")
    print("==============================")
    print("Starting pages:", len(START_URLS))
    print("Maximum new pages:", MAX_NEW_PAGES)
    print("Maximum per domain:", MAX_PER_DOMAIN)
    print("Starting index:", len(index))
    print("==============================\n")

    new_pages = 0
    visits = 0

    while queue and new_pages < MAX_NEW_PAGES and visits < MAX_VISITS:
        url = queue.popleft()

        if url in visited:
            continue

        visited.add(url)
        visits += 1

        before = len(index)
        links = crawl_page(url)

        new_pages += len(index) - before

        for link in links:
            if link not in visited and len(queue) < 10000:
                queue.append(link)

        if visits % 25 == 0:
            print(
                "\nPROGRESS:",
                new_pages,
                "new pages |",
                len(index),
                "total pages |",
                len(queue),
                "in queue\n"
            )

    save_index()

    print("\n==============================")
    print("CRAWLING FINISHED")
    print("New pages:", new_pages)
    print("Total indexed:", len(index))
    print("Visited:", visits)
    print("Saved:", INDEX_FILE)
    print("==============================")


if __name__ == "__main__":
    main()
