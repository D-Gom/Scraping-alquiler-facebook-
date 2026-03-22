"""
Main orchestration script (Phase 6).

Pipeline per execution cycle:
  1. Scraping  – fetch the latest posts from each configured Facebook group.
  2. Dedup     – skip posts already present in the database.
  3. Filter    – discard posts that fail the keyword heuristic.
  4. Gemini    – deep multimodal analysis for posts that passed the filter.
  5. Persist   – save every evaluated post to the database.
  6. Notify    – send a Telegram alert for posts where Gemini says es_apto=True.

Run once:
    python main.py

Run on a schedule (every INTERVALO_MINUTOS minutes):
    python main.py --schedule
"""

import argparse
import logging
import sys
import time

import schedule

import config
import database
import filter as kw_filter
import gemini_analyzer
import notifier
import scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def ejecutar_ciclo() -> None:
    """Run one full search-and-notify cycle."""
    logger.info("=== Iniciando ciclo de búsqueda ===")
    matches_encontrados = 0
    posts_nuevos = 0

    for group_url in config.FACEBOOK_GROUP_URLS:
        logger.info("Scrapeando grupo: %s", group_url)
        try:
            posts = scraper.extraer_posts(group_url)
        except Exception as exc:
            logger.error("Error al scrapear %s: %s", group_url, exc)
            continue

        logger.info("  Posts obtenidos: %d", len(posts))

        for post in posts:
            post_id = post["post_id"]

            # --- Deduplication ---
            if database.post_existe(post_id):
                logger.debug("  [DUP] %s ya procesado, omitiendo.", post_id)
                continue

            posts_nuevos += 1
            logger.info("  [NUEVO] %s", post_id)

            # --- Keyword filter ---
            if not kw_filter.pasar_filtro(post["texto"]):
                logger.info("  [FILTRO] %s descartado por palabras clave.", post_id)
                database.guardar_post(post_id, post["url"], post["texto"], es_match=False)
                continue

            logger.info("  [FILTRO OK] %s pasa el filtro de palabras clave.", post_id)

            # --- Gemini analysis ---
            try:
                analisis = gemini_analyzer.analizar_post(post)
            except Exception as exc:
                logger.error("  Error en Gemini para %s: %s", post_id, exc)
                database.guardar_post(post_id, post["url"], post["texto"], es_match=False)
                continue

            es_match = analisis.get("es_apto", False)
            logger.info(
                "  [GEMINI] %s → es_apto=%s | %s",
                post_id,
                es_match,
                analisis.get("razon", ""),
            )

            # --- Persist ---
            database.guardar_post(post_id, post["url"], post["texto"], es_match=es_match)

            # --- Notify ---
            if es_match:
                matches_encontrados += 1
                logger.info("  [MATCH] Enviando alerta para %s", post_id)
                try:
                    notifier.enviar_alerta(post, analisis)
                except Exception as exc:
                    logger.error("  Error al enviar alerta para %s: %s", post_id, exc)

    logger.info(
        "=== Ciclo finalizado — nuevos: %d, matches: %d ===",
        posts_nuevos,
        matches_encontrados,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Buscador inteligente de alquileres en Facebook con IA"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a schedule (every INTERVALO_MINUTOS minutes, default 60)",
    )
    args = parser.parse_args()

    # Ensure the database is ready.
    database.init_db()

    if args.schedule:
        logger.info(
            "Programando ejecución cada %d minuto(s)...", config.INTERVALO_MINUTOS
        )
        schedule.every(config.INTERVALO_MINUTOS).minutes.do(ejecutar_ciclo)
        # Run immediately on startup, then follow the schedule.
        ejecutar_ciclo()
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        ejecutar_ciclo()


if __name__ == "__main__":
    main()
