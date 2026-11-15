import asyncio
import threading
import uuid
from pathlib import Path

from androidtvremote2 import AndroidTVRemote

BASE = Path(__file__).resolve().parent
DATA = BASE / "tvdata"
DATA.mkdir(exist_ok=True)


class TVRemoteManager:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True, name="TVRemoteLoop")
        self.thread.start()

        self.clients = {}
        self.pairing = {}

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, timeout=15):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def _files(self, target):
        safe = "".join(c if c.isalnum() else "_" for c in target)
        return DATA / f"{safe}.crt", DATA / f"{safe}.key"

    def _client(self, target):
        cert, key = self._files(target)
        return AndroidTVRemote(
            "RemoteControlHub",
            str(cert),
            str(key),
            target,
            api_port=6466,
            pair_port=6467,
        )

    async def _ensure_cert(self, target):
        client = self._client(target)
        try:
            await client.async_generate_cert_if_missing()
        finally:
            client.disconnect()

    def start_pairing(self, target):
        return self.run(self._start_pairing(target))

    async def _start_pairing(self, target):
        await self._ensure_cert(target)

        # IMPORTANT: AndroidTVRemote viene creato nello stesso event loop
        # in cui vengono eseguite le coroutine della libreria.
        client = self._client(target)
        try:
            await client.async_start_pairing()
        except Exception:
            client.disconnect()
            raise

        token = str(uuid.uuid4())
        self.pairing[token] = client
        return token

    def finish_pairing(self, token, code):
        return self.run(self._finish_pairing(token, code))

    async def _finish_pairing(self, token, code):
        client = self.pairing.pop(token, None)
        if client is None:
            raise RuntimeError("Sessione pairing scaduta")

        try:
            await client.async_finish_pairing(code)
            host = client.host
        except Exception:
            client.disconnect()
            raise

        client.disconnect()

        new_client = self._client(host)
        try:
            await new_client.async_connect()
        except Exception:
            new_client.disconnect()
            raise

        self.clients[host] = new_client
        return True

    def send_key(self, target, key):
        return self.run(self._send_key(target, key))

    async def _send_key(self, target, key):
        client = self.clients.get(target)

        if client is None:
            client = self._client(target)
            try:
                await client.async_connect()
            except Exception:
                client.disconnect()
                raise
            self.clients[target] = client

        # send_key_command è sincrono nella libreria.
        client.send_key_command(key)

    def disconnect(self, target):
        client = self.clients.pop(target, None)
        if client:
            client.disconnect()
