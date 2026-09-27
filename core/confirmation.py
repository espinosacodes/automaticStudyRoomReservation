"""Official confirmation PDFs (ConstanciaDeReservaDeEspacio).

The portal generates the receipt through JasperReports. The report URL is built
purely from booking fields, so any active booking can have its official receipt
regenerated, including bookings made by earlier runs:

    TIPO=F&FECHAINICIO=DD/MM/YYYY&FECHAFIN=&PIDM=<user>&HORAINICIO=<HHMM>
    &HORAFIN=<HHMM>&ESPACIOS=<roomCode>&ACTIVIDAD=<code>&USUARIO=<user>

Two discoveries baked in here, both measured against the live portal:

- The end time must be the *stored* end time, which is one minute before the
  booked end (a 08:00-10:00 block is stored as 0800-0959, exactly as Mis
  Reservas shows it). Passing the booked end yields a valid but blank PDF,
  which is also why the portal itself warns that receipts can come out blank.
- No prior validation call is needed. ``valRes`` returns "Y" for active
  bookings, but the report renders fully without it.

Shared by ``main.py`` (capture right after CONFIRMAR) and
``tools/fetch_confirmation.py`` (regenerate for existing bookings).
"""

from __future__ import annotations

import re
import zlib
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

REPORT_BASE = (
    "https://banner9.icesi.edu.co/icjasperserver/flow.html"
    "?_flowId=viewReportFlow&_flowId=viewReportFlow"
    "&ParentFolderUri=%2Freports%2FProgramacion_academica_y_registro_curricular%2FEspaciosFisicos"
    "&reportUnit=%2Freports%2FProgramacion_academica_y_registro_curricular%2FEspaciosFisicos"
    "%2FConstanciaDeReservaDeEspacio&standAlone=true&output=pdf"
)

ACTIVITY_CODES = {
    "Capacitación": "CAP",
    "Examen": "EXA-1",
    "Examen final": "EXA-3",
    "Examen multitudinario": "EXA-2",
    "Práctica de Laboratorio": "PL",
    "Reunión": "REU",
    "Seminario": "SEM",
    "Taller": "TAL",
}

MIN_CONTENT_BYTES = 5_000


def stored_end(end: str) -> str:
    """End time as the portal stores it: one minute before the booked end."""
    hours, minutes = (int(part) for part in end.split(":"))
    total = hours * 60 + minutes - 1
    return f"{total // 60:02d}{total % 60:02d}"


def activity_code(activity: str) -> str:
    """Map an activity label to its portal code, passing codes through."""
    if re.fullmatch(r"[A-Z]+(-\d)?", activity):
        return activity
    return ACTIVITY_CODES.get(activity, activity)


def room_code_from_label(label: str) -> str:
    """Extract the room code (e.g. 204BI) from a portal room label."""
    match = re.search(r"(\d+[A-Z]{2,})", label)
    return match.group(1) if match else ""


def report_url(
    target: date, start: str, end: str, room_code: str, activity: str, username: str
) -> str:
    """Build the Jasper report URL for one booking."""
    params = {
        "TIPO": "F",
        "FECHAINICIO": target.strftime("%d/%m/%Y"),
        "FECHAFIN": "",
        "PIDM": username,
        "HORAINICIO": start.replace(":", ""),
        "HORAFIN": stored_end(end),
        "ESPACIOS": room_code,
        "ACTIVIDAD": activity_code(activity),
        "CODIGOMATERIA": "",
        "CODIGODEPARTAMENTO": "",
        "GRUPO": "",
        "USUARIO": username,
    }
    return REPORT_BASE + "&" + urlencode(params)


def pdf_texts(raw: bytes) -> list[str]:
    """Best-effort readable strings out of a PDF, for content verification."""
    try:
        streams = re.findall(rb"stream\r?\n(.*?)endstream", raw, re.S)
        raw = b"\n".join(zlib.decompress(stream) for stream in streams)
    except Exception:
        pass
    texts = []
    for item in re.findall(rb"\((?:\\.|[^)]){4,120}\)", raw):
        try:
            text = item[1:-1].decode("latin-1")
        except Exception:
            continue
        if "Jasper" in text or "iText" in text or text.startswith("D:"):
            continue
        texts.append(text)
    return texts


def pdf_has_content(raw: bytes, room_code: str) -> bool:
    """True when the PDF is a real receipt, not the portal's blank one-pager."""
    if len(raw) < MIN_CONTENT_BYTES or not raw.startswith(b"%PDF-"):
        return False
    joined = " ".join(pdf_texts(raw))
    return "Constancia de reserva" in joined and room_code in joined


def fetch_official_pdf(
    page,
    *,
    target: date,
    start: str,
    end: str,
    room_code: str,
    activity: str,
    username: str,
    out: Path,
) -> Path:
    """Open the Jasper report in a logged-in page and save the official PDF.

    Raises when the portal returns its blank receipt instead of real content.
    """
    url = report_url(target, start, end, room_code, activity, username)
    with page.expect_download(timeout=30_000) as download_info:
        page.evaluate(f"window.open({url!r}, '_blank')")
    download = download_info.value
    tmp = out.with_suffix(".tmp")
    download.save_as(tmp)
    raw = tmp.read_bytes()
    if not pdf_has_content(raw, room_code):
        tmp.unlink(missing_ok=True)
        raise ValueError(f"portal returned a blank receipt for {target} {start}-{end}")
    tmp.rename(out)
    return out
