"""Real-time 1-minute bar feed via Alpaca WebSocket (alpaca-py StockDataStream)."""

import asyncio
import os
from typing import Callable, Awaitable

from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar

from utils.logger import log


BarCallback = Callable[[str, Bar], Awaitable[None]]


class DataFeed:
    def __init__(self, symbols: list[str], on_bar: BarCallback) -> None:
        self._api_key = os.getenv("ALPACA_API_KEY", "")
        self._secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self._symbols = symbols
        self._on_bar = on_bar
        self._stream = None

    def _make_handler(self) -> BarCallback:
        on_bar = self._on_bar

        async def handler(bar: Bar) -> None:
            try:
                await on_bar(bar.symbol, bar)
            except Exception as exc:
                log.error(f"Bar handler error for {bar.symbol}: {exc}")

        return handler

    async def start(self) -> None:
        loop = asyncio.get_event_loop()
        handler = self._make_handler()
        max_retries = 10
        backoff = 5  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                self._stream = StockDataStream(self._api_key, self._secret_key)
                self._stream.subscribe_bars(handler, *self._symbols)
                log.info(f"DataFeed: subscribing to {self._symbols} (attempt {attempt})")
                await loop.run_in_executor(None, self._stream.run)
                # stream.run() returned cleanly — session ended normally
                return
            except asyncio.CancelledError:
                return
            except Exception as exc:
                log.error(f"DataFeed: stream error — {exc}")
                if attempt < max_retries:
                    wait = backoff * attempt
                    log.info(f"DataFeed: reconnecting in {wait}s (attempt {attempt}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    log.error("DataFeed: max retries reached, giving up")
                    raise

    async def stop(self) -> None:
        try:
            await self._stream.stop()
        except Exception:
            pass
