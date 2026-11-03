"""Zentrale Stelle für die SSL/TLS-Konfiguration.

In Firmennetzwerken wird HTTPS häufig von einer Firewall/einem Proxy
aufgebrochen. Dann präsentiert der Proxy ein eigenes ("self-signed")
Zertifikat, das Python standardmäßig nicht kennt -> der Fehler
"CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain".

Dieses Modul bietet zwei Lösungen:
  1. Ein Firmen-Root-Zertifikat (.pem/.crt) als vertrauenswürdig angeben.
  2. Die Zertifikatsprüfung komplett deaktivieren (nur bei Bedarf!).
"""

from __future__ import annotations

import ssl

import certifi


def build_ssl_context(ca_cert_path: str | None = None, verify: bool = True) -> ssl.SSLContext | bool:
    """Erzeugt einen SSLContext für aiohttp/HTTP-Aufrufe.

    Args:
        ca_cert_path: Optionaler Pfad zu einem Firmen-Root-Zertifikat
            (PEM/CRT). Wird es angegeben, vertraut das Tool zusätzlich
            diesem Zertifikat.
        verify: Wenn False, wird die Zertifikatsprüfung komplett
            deaktiviert (unsicher, nur für vertrauenswürdige Netze).

    Returns:
        Einen konfigurierten ssl.SSLContext. Bei verify=False wird ein
        Context ohne Prüfung zurückgegeben.
    """
    if not verify:
        # Prüfung komplett aus -> akzeptiert jedes Zertifikat.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    # Standardmäßig die certifi-Root-Zertifikate verwenden ...
    context = ssl.create_default_context(cafile=certifi.where())

    # ... und optional das Firmen-Zertifikat zusätzlich laden.
    if ca_cert_path:
        context.load_verify_locations(cafile=ca_cert_path)

    return context
