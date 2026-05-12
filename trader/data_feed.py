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
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self._symbols = symbols
        self._on_bar = on_bar
        self._stream = StockDataStream(api_key, secret_key)

    def _make_handler(self) -> BarCallback:
        on_bar = self._on_bar

        async def handler(bar: Bar) -> None:
            try:
                await on_bar(bar.symbol, bar)
            except Exception as exc:
                log.error(f"Bar handler error for {bar.symbol}: {exc}")

        return handler

    async def start(self) -> None:
        handler = self._make_handler()
        self._stream.subscribe_bars(handler, *self._symbols)
        log.info(f"DataFeed: subscribing to bars for {self._symbols}")
        # run() calls asyncio.run() internally, so we must offload to a thread
        # to avoid "cannot run nested event loop" when called from async context.
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._stream.run)

    async def stop(self) -> None:
        try:
            await self._stream.stop()
        except Exception:
            pass
