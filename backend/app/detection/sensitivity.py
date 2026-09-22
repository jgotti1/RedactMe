"""Detection sensitivity profiles. Low flags only what it is very sure about; High flags anything
that might be sensitive; Balanced is the default."""
LEVELS = ("low", "balanced", "high")
DEFAULT = "balanced"

PROFILES = {
    "low": {"person": 0.8, "location": None, "other": 0.6, "phone": False, "ein": False,
            "contextual": ("BANK_ROUTING",), "runs": ("SSN", "BANK_ROUTING"), "unlabeled": False,
            "name_parts": None, "name_pairs": False},
    "balanced": {"person": 0.6, "location": 0.6, "other": 0.4, "phone": True, "ein": True,
                 "contextual": ("BANK_ROUTING", "BANK_ACCOUNT", "DATE_OF_BIRTH", "ID_NUMBER"),
                 "runs": ("SSN", "BANK_ROUTING", "BANK_ACCOUNT"), "unlabeled": False,
                 "name_parts": 3, "name_pairs": False},
    "high": {"person": 0.4, "location": 0.4, "other": 0.3, "phone": True, "ein": True,
             "contextual": ("BANK_ROUTING", "BANK_ACCOUNT", "DATE_OF_BIRTH", "ID_NUMBER"),
             "runs": ("SSN", "BANK_ROUTING", "BANK_ACCOUNT"), "unlabeled": True,
             "name_parts": 2, "name_pairs": True},
}


def profile(level: str) -> dict:
    return PROFILES.get(level, PROFILES[DEFAULT])
