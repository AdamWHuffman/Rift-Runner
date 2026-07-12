"""Deterministic fantasy region name generator.

Seeded from the real place label so the same real place always regenerates
the same fantasy name -- the real label is never shown in the UI, only used
here to pick a stable name. Uses a SHA-256-based seed rather than Python's
built-in hash(), since str hashing is randomized per-process by default and
would silently break "same place -> same name" across restarts.
"""

import hashlib
import random

from app.services.region_engine.geocode import (
    THEME_GREENWOOD,
    THEME_HIGHLANDS,
    THEME_METROPOLIS,
    THEME_RIVERLANDS,
)

_WORD_BANKS: dict[str, dict[str, list[str]]] = {
    THEME_RIVERLANDS: {
        "prefixes": ["Potomac's", "Rivermouth", "The Fourmile", "Streamwatch", "Tidewater", "The Millrace"],
        "nouns": ["Landing", "Reaches", "Crossing", "Shallows", "Confluence", "Bend"],
    },
    THEME_HIGHLANDS: {
        "prefixes": ["The Ridgeway", "Stonewatch", "Ridgemont", "Highcrag", "The Windridge", "Craghollow"],
        "nouns": ["Spires", "Heights", "Crest", "Overlook", "Summit", "Rise"],
    },
    THEME_GREENWOOD: {
        "prefixes": ["Glasshaven", "Thornwood", "Mossgate", "The Fernhollow", "Fernbrook", "Willowmere"],
        "nouns": ["Heights", "Glade", "Vale", "Thicket", "Grove", "Dell"],
    },
    THEME_METROPOLIS: {
        "prefixes": ["Ironhold", "Steelgate", "The Glassward", "Brightforge", "Skyline", "Emberfall"],
        "nouns": ["Quarter", "District", "Spires", "Crossing", "Row", "Commons"],
    },
}


def _stable_seed(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16)


def generate_region_name(real_place_label: str, theme: str) -> str:
    bank = _WORD_BANKS.get(theme, _WORD_BANKS[THEME_GREENWOOD])
    rng = random.Random(_stable_seed(f"{real_place_label}|{theme}"))
    prefix = rng.choice(bank["prefixes"])
    noun = rng.choice(bank["nouns"])
    return f"{prefix} {noun}"
