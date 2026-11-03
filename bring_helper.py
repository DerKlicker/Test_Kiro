"""Hilfsfunktionen für die (inoffizielle) Bring!-API.

Die bring-api-Bibliothek ist asynchron. Dieses Modul kapselt die
async-Aufrufe in eine synchrone Funktion, damit sie bequem aus dem
Flask-Request heraus aufgerufen werden kann.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import aiohttp
from bring_api import Bring

from ssl_helper import build_ssl_context


@dataclass
class BringResult:
    added: list[str]
    skipped: list[str]
    list_name: str


def _make_session(ca_cert_path: str | None, verify_ssl: bool) -> aiohttp.ClientSession:
    """Erzeugt eine aiohttp-Session mit passendem SSL-Context."""
    ssl_context = build_ssl_context(ca_cert_path=ca_cert_path, verify=verify_ssl)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    return aiohttp.ClientSession(connector=connector)


async def _send_items_async(
    email: str,
    password: str,
    items: list[tuple[str, str]],
    list_name: str | None = None,
    ca_cert_path: str | None = None,
    verify_ssl: bool = True,
) -> BringResult:
    """items ist eine Liste aus (name, specification)-Tupeln."""

    async with _make_session(ca_cert_path, verify_ssl) as session:
        bring = Bring(session, email, password)
        await bring.login()

        lists = (await bring.load_lists())["lists"]
        if not lists:
            raise RuntimeError("Keine Bring!-Einkaufsliste im Konto gefunden.")

        # Gewünschte Liste anhand des Namens wählen, sonst die erste nehmen.
        target = lists[0]
        if list_name:
            for lst in lists:
                if lst.get("name", "").strip().lower() == list_name.strip().lower():
                    target = lst
                    break

        list_uuid = target["listUuid"]

        # Bereits vorhandene Artikel lesen, um Duplikate zu vermeiden.
        existing_raw = await bring.get_list(list_uuid)
        existing_items = existing_raw.get("items", {})
        # Je nach API-Version liegen die Einträge unter "purchase".
        purchase = (
            existing_items.get("purchase", [])
            if isinstance(existing_items, dict)
            else existing_items
        )
        existing_names = {
            (it.get("itemId") or it.get("name") or "").strip().lower()
            for it in purchase
        }

        added: list[str] = []
        skipped: list[str] = []

        for name, spec in items:
            if name.strip().lower() in existing_names:
                skipped.append(name)
                continue
            await bring.save_item(list_uuid, name, spec)
            added.append(name)
            existing_names.add(name.strip().lower())

        return BringResult(added=added, skipped=skipped, list_name=target.get("name", ""))


def send_items(
    email: str,
    password: str,
    items: list[tuple[str, str]],
    list_name: str | None = None,
    ca_cert_path: str | None = None,
    verify_ssl: bool = True,
) -> BringResult:
    """Synchroner Wrapper um die async Bring!-Übertragung."""
    return asyncio.run(
        _send_items_async(
            email, password, items, list_name, ca_cert_path, verify_ssl
        )
    )


async def _list_names_async(
    email: str,
    password: str,
    ca_cert_path: str | None = None,
    verify_ssl: bool = True,
) -> list[str]:
    async with _make_session(ca_cert_path, verify_ssl) as session:
        bring = Bring(session, email, password)
        await bring.login()
        lists = (await bring.load_lists())["lists"]
        return [lst.get("name", "") for lst in lists]


def list_names(
    email: str,
    password: str,
    ca_cert_path: str | None = None,
    verify_ssl: bool = True,
) -> list[str]:
    """Gibt die Namen aller Einkaufslisten des Bring!-Kontos zurück."""
    return asyncio.run(_list_names_async(email, password, ca_cert_path, verify_ssl))
