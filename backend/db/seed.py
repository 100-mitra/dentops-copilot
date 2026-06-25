"""Seed the DB with ~15 patients (CDT-coded procedures). Run: make seed.

`SEED_PATIENTS` is the single source of truth and is importable by tests.
`run(verbose=False)` is idempotent and STDOUT-silent by default — patients.py
auto-seeds an empty DB on first use, and printing to stdout would corrupt the
JSON-RPC stream when the MCP server runs over stdio (Claude Desktop).

All data is mock/illustrative. Patient #1042 anchors the canonical demo and must
stay consistent with backend/fixtures/detector_outputs.json (bitewing_1042).
"""
from __future__ import annotations

import sys

from backend.db.models import init_db, get_session, Patient, Procedure

# patient_id, name, last_visit, allergies[list], procedures[(code, desc, tooth, date)]
SEED_PATIENTS: list[dict] = [
    {
        "patient_id": "1042",
        "name": "Jordan Patient (demo)",
        "last_visit": "2025-11-12",
        "allergies": [],
        "procedures": [
            ("D2392", "resin composite filling, two surface posterior", "#14", "2025-11-12"),
            ("D1110", "prophylaxis (cleaning), adult", "", "2025-11-12"),
        ],
    },
    {
        "patient_id": "1040",
        "name": "Amara Osei",
        "last_visit": "2025-09-03",
        "allergies": ["penicillin"],
        "procedures": [
            ("D0120", "periodic oral evaluation", "", "2025-09-03"),
            ("D1208", "topical fluoride application", "", "2025-09-03"),
        ],
    },
    {
        "patient_id": "1041",
        "name": "Bao Nguyen",
        "last_visit": "2025-10-21",
        "allergies": [],
        "procedures": [
            ("D2750", "crown, porcelain fused to high noble metal", "#30", "2025-10-21"),
            ("D2950", "core buildup, including any pins", "#30", "2025-10-21"),
        ],
    },
    {
        "patient_id": "1043",
        "name": "Carmen Ruiz",
        "last_visit": "2025-08-14",
        "allergies": ["latex"],
        "procedures": [
            ("D4341", "periodontal scaling and root planing, per quadrant", "", "2025-08-14"),
            ("D0274", "bitewings, four radiographic images", "", "2025-08-14"),
        ],
    },
    {
        "patient_id": "1044",
        "name": "Derek Lindqvist",
        "last_visit": "2025-11-30",
        "allergies": [],
        "procedures": [
            ("D2140", "amalgam filling, one surface", "#19", "2025-11-30"),
        ],
    },
    {
        "patient_id": "1045",
        "name": "Elena Petrova",
        "last_visit": "2025-07-09",
        "allergies": ["sulfa"],
        "procedures": [
            ("D3310", "endodontic therapy, anterior tooth", "#8", "2025-07-09"),
            ("D2740", "crown, porcelain/ceramic", "#8", "2025-07-09"),
        ],
    },
    {
        "patient_id": "1046",
        "name": "Frank O'Donnell",
        "last_visit": "2025-12-02",
        "allergies": [],
        "procedures": [
            ("D7140", "extraction, erupted tooth", "#1", "2025-12-02"),
        ],
    },
    {
        "patient_id": "1047",
        "name": "Grace Kim",
        "last_visit": "2025-06-18",
        "allergies": [],
        "procedures": [
            ("D2331", "resin composite filling, anterior, two surface", "#9", "2025-06-18"),
            ("D1110", "prophylaxis (cleaning), adult", "", "2025-06-18"),
        ],
    },
    {
        "patient_id": "1048",
        "name": "Hassan Al-Farsi",
        "last_visit": "2025-10-05",
        "allergies": ["penicillin", "codeine"],
        "procedures": [
            ("D0150", "comprehensive oral evaluation, new patient", "", "2025-10-05"),
            ("D0210", "intraoral, complete series of radiographic images", "", "2025-10-05"),
        ],
    },
    {
        "patient_id": "1049",
        "name": "Ingrid Larsen",
        "last_visit": "2025-09-27",
        "allergies": [],
        "procedures": [
            ("D2392", "resin composite filling, two surface posterior", "#3", "2025-09-27"),
        ],
    },
    {
        "patient_id": "1050",
        "name": "Julio Marqués",
        "last_visit": "2025-11-19",
        "allergies": [],
        "procedures": [
            ("D6010", "surgical placement of implant body, endosteal", "#19", "2025-11-19"),
        ],
    },
    {
        "patient_id": "1051",
        "name": "Keiko Tanaka",
        "last_visit": "2025-08-30",
        "allergies": ["aspirin"],
        "procedures": [
            ("D1110", "prophylaxis (cleaning), adult", "", "2025-08-30"),
            ("D0120", "periodic oral evaluation", "", "2025-08-30"),
        ],
    },
    {
        "patient_id": "1052",
        "name": "Liam Murphy",
        "last_visit": "2025-12-08",
        "allergies": [],
        "procedures": [
            ("D2950", "core buildup, including any pins", "#18", "2025-12-08"),
            ("D2740", "crown, porcelain/ceramic", "#18", "2025-12-08"),
        ],
    },
    {
        "patient_id": "1053",
        "name": "Mei Lin",
        "last_visit": "2025-07-22",
        "allergies": [],
        "procedures": [
            ("D1351", "sealant, per tooth", "#4", "2025-07-22"),
            ("D1208", "topical fluoride application", "", "2025-07-22"),
        ],
    },
    {
        "patient_id": "1054",
        "name": "Noah Brooks",
        "last_visit": "2025-10-11",
        "allergies": ["latex"],
        "procedures": [
            ("D2160", "amalgam filling, three surface", "#31", "2025-10-11"),
        ],
    },
]


def run(verbose: bool = False) -> int:
    """Create tables and insert any patients not already present. Idempotent.

    Returns the number of patients inserted. Set verbose=True only from a CLI —
    never when invoked while serving stdio MCP (stdout is the protocol channel).
    """
    init_db()
    inserted = 0
    with get_session() as s:
        for p in SEED_PATIENTS:
            if s.get(Patient, p["patient_id"]):
                continue
            s.add(Patient(
                patient_id=p["patient_id"],
                name=p["name"],
                last_visit=p["last_visit"],
                allergies=",".join(p["allergies"]),
            ))
            for code, desc, tooth, date in p["procedures"]:
                s.add(Procedure(
                    patient_id=p["patient_id"], code=code, desc=desc, tooth=tooth, date=date
                ))
            inserted += 1
        s.commit()
    if verbose:
        # stderr, not stdout — safe alongside stdio transport.
        msg = f"Seeded {inserted} new patient(s); {len(SEED_PATIENTS)} total in source."
        print(msg, file=sys.stderr)
    return inserted


if __name__ == "__main__":
    run(verbose=True)
