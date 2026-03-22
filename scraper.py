"""
Facebook scraper module (Phase 2).

Uses Playwright with a persistent browser profile so that the Facebook session
is preserved between runs (avoiding repeated logins).

Usage
-----
The scraper is intentionally stateless: call `extraer_posts(group_url)` to get
a list of raw post dictionaries.  The caller is responsible for deduplication
and filtering.

Note on anti-scraping measures
-------------------------------
Facebook actively fights automated access.  To reduce the risk of blocks:
- A persistent browser profile stores cookies/session between runs.
- Random delays are introduced between scroll events.
- Only the most-recent posts (up to MAX_POSTS_PER_GROUP) are fetched.
"""

import hashlib
import random
import time
from typing import Any

from playwright.sync_api import sync_playwright

import config

# Path to the persistent browser profile directory.
PROFILE_DIR = "fb_profile"


def _generar_post_id(url: str, texto: str) -> str:
    """
    Generate a stable post ID.

    Facebook post IDs are embedded in the post URL when available; otherwise we
    fall back to a hash of (url + first 200 chars of text).
    """
    # Try to extract a numeric ID from the URL, e.g. /permalink/12345678/
    import re

    match = re.search(r"(\d{10,})", url)
    if match:
        return match.group(1)
    return hashlib.sha256((url + texto[:200]).encode()).hexdigest()[:16]


def extraer_posts(group_url: str, max_posts: int | None = None) -> list[dict[str, Any]]:
    """
    Scrape the most-recent posts from a Facebook group.

    Parameters
    ----------
    group_url:
        Full URL of the Facebook group, e.g.
        ``"https://www.facebook.com/groups/12345678"``.
    max_posts:
        Maximum number of posts to return.  Defaults to
        :data:`config.MAX_POSTS_PER_GROUP`.

    Returns
    -------
    list of dict with keys:
        ``post_id``, ``url``, ``texto``, ``imagenes`` (list[str]), ``autor``, ``fecha``.
    """
    if max_posts is None:
        max_posts = config.MAX_POSTS_PER_GROUP

    posts: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = browser.new_page()

        # Navigate to the group's "most recent" feed.
        sorted_url = group_url.rstrip("/") + "?sorting_setting=RECENT_ACTIVITY"
        page.goto(sorted_url, wait_until="domcontentloaded", timeout=60_000)
        time.sleep(random.uniform(3, 5))

        seen_ids: set[str] = set()

        for _ in range(max_posts * 3):  # scroll attempts
            if len(posts) >= max_posts:
                break

            # Collect post containers visible on the page.
            post_elements = page.query_selector_all(
                "div[data-pagelet^='FeedUnit'], div[role='article']"
            )

            for el in post_elements:
                if len(posts) >= max_posts:
                    break

                try:
                    # --- Text ---
                    texto_el = el.query_selector(
                        "div[data-ad-preview='message'], div[dir='auto']"
                    )
                    texto = texto_el.inner_text().strip() if texto_el else ""

                    # --- Link to post ---
                    link_el = el.query_selector("a[href*='/posts/'], a[href*='/permalink/']")
                    post_url = link_el.get_attribute("href") if link_el else group_url
                    if post_url and not post_url.startswith("http"):
                        post_url = "https://www.facebook.com" + post_url

                    # --- Post ID ---
                    post_id = _generar_post_id(post_url or "", texto)
                    if post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)

                    # --- Images ---
                    img_elements = el.query_selector_all("img[src*='fbcdn']")
                    imagenes = [
                        img.get_attribute("src")
                        for img in img_elements
                        if img.get_attribute("src")
                    ]

                    # --- Author ---
                    autor_el = el.query_selector("a[href*='/user/'], strong a")
                    autor = autor_el.inner_text().strip() if autor_el else "Desconocido"

                    # --- Date ---
                    fecha_el = el.query_selector("abbr[data-utime], span[id*='jsc']")
                    fecha = (
                        fecha_el.get_attribute("data-utime")
                        or fecha_el.inner_text().strip()
                        if fecha_el
                        else ""
                    )

                    if not texto:
                        continue

                    posts.append(
                        {
                            "post_id": post_id,
                            "url": post_url or group_url,
                            "texto": texto,
                            "imagenes": imagenes,
                            "autor": autor,
                            "fecha": fecha,
                        }
                    )
                except Exception:
                    continue

            # Scroll down to load more posts.
            page.evaluate("window.scrollBy(0, 1200)")
            time.sleep(random.uniform(1.5, 3.0))

        browser.close()

    return posts
