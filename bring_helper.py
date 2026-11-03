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


def _attr(obj, name: str, default=None):
    """Liest ein Feld sowohl aus Dataclass-Objekten (neue bring-api, Zugriff
    per Attribut) als auch aus Dictionaries (ältere API, Zugriff per Key).

    Die aktuelle bring-api liefert typisierte Objekte wie BringListResponse
    oder BringList zurück, die NICHT per [] ansprechbar sind."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


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

        lists = _attr(await bring.load_lists(), "lists", [])
        if not lists:
            raise RuntimeError("Keine Bring!-Einkaufsliste im Konto gefunden.")

        # Gewünschte Liste anhand des Namens wählen, sonst die erste nehmen.
        target = lists[0]
        if list_name:
            for lst in lists:
                if _attr(lst, "name", "").strip().lower() == list_name.strip().lower():
                    target = lst
                    break

        list_uuid = _attr(target, "listUuid")

        # Bereits vorhandene Artikel lesen, um Duplikate zu vermeiden.
        existing_raw = await bring.get_list(list_uuid)
        # get_list liefert ein Objekt/Dict mit .items -> .purchase (Liste).
        items_container = _attr(existing_raw, "items", [])
        purchase = _attr(items_container, "purchase", items_container)
        if purchase is None:
            purchase = []
        existing_names = {
            (_attr(it, "itemId") or _attr(it, "name") or "").strip().lower()
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

        return BringResult(
            added=added, skipped=skipped, list_name=_attr(target, "name", "")
        )


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
        lists = _attr(await bring.load_lists(), "lists", [])
        return [_attr(lst, "name", "") for lst in lists]


def list_names(
    email: str,
    password: str,
    ca_cert_path: str | None = None,
    verify_ssl: bool = True,
) -> list[str]:
    """Gibt die Namen aller Einkaufslisten des Bring!-Kontos zurück."""
    return asyncio.run(_list_names_async(email, password, ca_cert_path, verify_ssl))
