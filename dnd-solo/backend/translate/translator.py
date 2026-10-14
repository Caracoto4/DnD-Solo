"""Переводчик RU↔EN: googletrans с retry/backoff и fallback на deep-translator.

Кэш переводов в SQLite (hash текста → перевод), иначе Google блокирует по лимиту (ТЗ, раздел 4).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging

log = logging.getLogger("translate")


def _cache_key(text: str, src: str, tgt: str) -> str:
    h = hashlib.sha256(f"{src}|{tgt}|{text}".encode("utf-8")).hexdigest()
    return h


class Translator:
    def __init__(self, db_path: str, enabled: bool = True,
                 retries: int = 3, backoff_base: float = 1.0):
        self.db_path = db_path
        self.enabled = enabled
        self.retries = retries
        self.backoff_base = backoff_base

    # ── кэш ────────────────────────────────────────────────────────
    def _cache_get(self, key: str) -> str | None:
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as con:
                row = con.execute(
                    "SELECT text FROM translation_cache WHERE key=?", (key,)
                ).fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            log.warning("translation cache read error: %s", e)
            return None

    def _cache_put(self, key: str, text: str, src: str, tgt: str) -> None:
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute(
                    "INSERT OR REPLACE INTO translation_cache(key, text, source_lang, target_lang) VALUES (?,?,?,?)",
                    (key, text, src, tgt),
                )
        except sqlite3.Error as e:
            log.warning("translation cache write error: %s", e)

    # ── перевод ────────────────────────────────────────────────────
    async def translate(self, text: str, src: str = "ru", tgt: str = "en") -> str:
        if not self.enabled or not text.strip():
            return text
        key = _cache_key(text, src, tgt)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        result: str | None = None
        try:
            from googletrans import Translator as GoogleTranslator  # type: ignore
            gt = GoogleTranslator()
            for attempt in range(self.retries):
                try:
                    result = gt.translate(text, src=src, dest=tgt).text
                    break
                except Exception as e:  # googletrans кидает разное
                    wait = self.backoff_base * (2 ** attempt)
                    log.warning("googletrans attempt %d failed: %s; wait %.1fs", attempt + 1, e, wait)
                    await asyncio.sleep(wait)
        except ImportError:
            log.warning("googletrans не установлен, пробуем deep-translator")

        if result is None:
            try:
                from deep_translator import GoogleTranslator as DeepGoogle  # type: ignore
                result = await asyncio.to_thread(DeepGoogle(source=src, target=tgt).translate, text)
            except Exception as e:
                log.error("deep-translator тоже не сработал: %s", e)

        if result is None:
            # фолбэк: отдаём оригинал, чтобы игра не вставала
            return text

        self._cache_put(key, result, src, tgt)
        return result

    async def ru_to_en(self, text: str) -> str:
        return await self.translate(text, src="ru", tgt="en")

    async def en_to_ru(self, text: str) -> str:
        return await self.translate(text, src="en", tgt="ru")
