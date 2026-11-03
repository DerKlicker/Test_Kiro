"""Hilfsfunktionen für den Zugriff auf die Notion-Datenbank.

Dieses Modul kapselt alle Notion-spezifischen Aufrufe:
  * Lesen der Einträge, bei denen die Checkbox "An bring senden" gesetzt ist
  * Zusammensetzen von Artikelname und Menge
  * Zurücksetzen der Checkbox nach erfolgreicher Übertragung
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from notion_client import Client


# Property-Namen in der Notion-Datenbank "Gesamt Event Ablaufplan".
# Falls du die Spalten in Notion anders benennst, hier anpassen.
PROP_NAME = "Name"                 # Titel-Spalte (z.B. "Z-Milch")
PROP_GESAMTMENGE = "Gesamtmenge"   # Zahl/Formel (z.B. 5750)
PROP_MENGE_PRO_GERICHT = "Menge pro Gericht"  # enthält die Einheit (z.B. "250 ml")
PROP_CHECKBOX = "An bring senden"  # Checkbox, die die Übertragung auslöst

# Nur Einträge, deren Name mit diesem Präfix beginnt, sind Zutaten.
ZUTAT_PRAEFIX = "Z-"


@dataclass
class ShoppingItem:
    """Ein für Bring! aufbereiteter Einkaufsartikel."""

    page_id: str
    name: str          # z.B. "Milch"
    specification: str  # z.B. "5750 ml"

    @property
    def display(self) -> str:
        return f"{self.name} ({self.specification})" if self.specification else self.name


class NotionHelper:
    def __init__(self, token: str, database_id: str):
        self.client = Client(auth=token)
        self.database_id = database_id

    # ------------------------------------------------------------------
    # Lesen
    # ------------------------------------------------------------------
    def fetch_checked_items(self) -> list[ShoppingItem]:
        """Liest alle Seiten, bei denen die Checkbox gesetzt ist und der
        Name mit dem Zutaten-Präfix (Z-) beginnt."""

        items: list[ShoppingItem] = []
        start_cursor: str | None = None

        while True:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": PROP_CHECKBOX,
                    "checkbox": {"equals": True},
                },
                start_cursor=start_cursor,
            )

            for page in response.get("results", []):
                item = self._page_to_item(page)
                if item is not None:
                    items.append(item)

            if not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")

        return items

    def _page_to_item(self, page: dict) -> ShoppingItem | None:
        props = page.get("properties", {})

        raw_name = self._read_title(props.get(PROP_NAME))
        if not raw_name:
            return None

        # Nur Zutaten übertragen, keine Rezepte (R-...).
        if not raw_name.startswith(ZUTAT_PRAEFIX):
            return None

        name = raw_name[len(ZUTAT_PRAEFIX):].strip()

        total = self._read_number(props.get(PROP_GESAMTMENGE))
        unit = self._read_unit(props.get(PROP_MENGE_PRO_GERICHT))

        specification = self._build_specification(total, unit)

        return ShoppingItem(page_id=page["id"], name=name, specification=specification)

    @staticmethod
    def _build_specification(total: float | None, unit: str) -> str:
        """Setzt Gesamtmenge + Einheit zusammen, z.B. 5750 + 'ml' -> '5750 ml'."""
        if total is None:
            return unit.strip()
        # Ganze Zahlen ohne Nachkommastelle darstellen (575 statt 575.0).
        if float(total).is_integer():
            total_str = str(int(total))
        else:
            total_str = str(total)
        return f"{total_str} {unit}".strip()

    # ------------------------------------------------------------------
    # Schreiben
    # ------------------------------------------------------------------
    def reset_checkbox(self, page_id: str) -> None:
        """Entfernt das Häkchen in der Checkbox 'An bring senden'."""
        self.client.pages.update(
            page_id=page_id,
            properties={PROP_CHECKBOX: {"checkbox": False}},
        )

    # ------------------------------------------------------------------
    # Property-Reader (robust gegen fehlende/leere Werte)
    # ------------------------------------------------------------------
    @staticmethod
    def _read_title(prop: dict | None) -> str:
        if not prop:
            return ""
        parts = prop.get("title", [])
        return "".join(p.get("plain_text", "") for p in parts).strip()

    @staticmethod
    def _read_number(prop: dict | None) -> float | None:
        if not prop:
            return None
        prop_type = prop.get("type")
        if prop_type == "number":
            return prop.get("number")
        if prop_type == "formula":
            formula = prop.get("formula", {})
            if formula.get("type") == "number":
                return formula.get("number")
            if formula.get("type") == "string":
                # Formel liefert evtl. Text -> erste Zahl herausziehen.
                match = re.search(r"-?\d+(?:[.,]\d+)?", formula.get("string") or "")
                if match:
                    return float(match.group().replace(",", "."))
        if prop_type == "rollup":
            rollup = prop.get("rollup", {})
            if rollup.get("type") == "number":
                return rollup.get("number")
        return None

    @staticmethod
    def _read_unit(prop: dict | None) -> str:
        """Extrahiert nur die Einheit (den nicht-numerischen Teil) aus
        'Menge pro Gericht', z.B. '250 ml' -> 'ml', '2 Stück' -> 'Stück'."""
        text = NotionHelper._read_plain(prop)
        if not text:
            return ""
        # Zahl am Anfang entfernen, Rest ist die Einheit.
        unit = re.sub(r"^\s*-?\d+(?:[.,]\d+)?\s*", "", text).strip()
        return unit

    @staticmethod
    def _read_plain(prop: dict | None) -> str:
        """Liest einen Property-Wert als einfachen Text, egal ob
        select, rich_text, formula oder number."""
        if not prop:
            return ""
        prop_type = prop.get("type")
        if prop_type == "select":
            sel = prop.get("select")
            return sel.get("name", "") if sel else ""
        if prop_type == "multi_select":
            return " ".join(s.get("name", "") for s in prop.get("multi_select", []))
        if prop_type == "rich_text":
            return "".join(p.get("plain_text", "") for p in prop.get("rich_text", []))
        if prop_type == "title":
            return "".join(p.get("plain_text", "") for p in prop.get("title", []))
        if prop_type == "number":
            n = prop.get("number")
            return "" if n is None else str(n)
        if prop_type == "formula":
            formula = prop.get("formula", {})
            if formula.get("type") == "string":
                return formula.get("string") or ""
            if formula.get("type") == "number":
                n = formula.get("number")
                return "" if n is None else str(n)
        return ""
