"""Seed sample/test data for development.

Creates sample sanctions entries and flag data for testing the agent
without requiring live API connections.
"""
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def seed_paris_mou():
    """Create Paris MoU White/Grey/Black list data."""
    data = {
        "source": "Paris MoU Annual Report 2024-2025",
        "last_updated": "2025-07-01",
        "white_list": [
            "BAHAMAS", "BERMUDA", "CAYMAN ISLANDS", "DENMARK", "FRANCE",
            "GERMANY", "GREECE", "HONG KONG", "ISLE OF MAN", "JAPAN",
            "MARSHALL ISLANDS", "NETHERLANDS", "NORWAY", "SINGAPORE",
            "SWEDEN", "UNITED KINGDOM", "UNITED STATES", "AUSTRALIA",
            "CANADA", "NEW ZEALAND", "IRELAND", "PORTUGAL", "SPAIN",
            "ITALY", "BELGIUM", "FINLAND", "LUXEMBOURG",
        ],
        "grey_list": [
            "CHINA", "INDIA", "INDONESIA", "KOREA", "MALAYSIA",
            "SAUDI ARABIA", "THAILAND", "TURKEY", "VIETNAM",
            "PHILIPPINES", "EGYPT", "BANGLADESH", "UKRAINE",
        ],
        "black_list": [
            "CAMEROON", "COMOROS", "MOLDOVA", "SIERRA LEONE",
            "TANZANIA", "TOGO", "PALAU",
        ],
    }
    path = DATA_DIR / "flags" / "paris_mou.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"✓ Paris MoU data: {path}")


def seed_uscg_targeted():
    """Create USCG Targeted Flag List data."""
    data = {
        "source": "USCG Annual Targeted Flag List 2025",
        "targeted_flags": [
            "CAMEROON", "COMOROS", "KIRIBATI", "MOLDOVA",
            "MONGOLIA", "PALAU", "SIERRA LEONE", "TANZANIA", "TOGO",
        ],
    }
    path = DATA_DIR / "flags" / "uscg_targeted.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"✓ USCG Targeted data: {path}")


def seed_itf_foc():
    """Create ITF Flag of Convenience list data."""
    data = {
        "source": "ITF Flag of Convenience List 2025",
        "foc_flags": [
            "ANTIGUA AND BARBUDA", "BAHAMAS", "BARBADOS", "BELIZE",
            "BERMUDA", "BOLIVIA", "CAMBODIA", "CAYMAN ISLANDS",
            "COMOROS", "CURACAO", "CYPRUS", "EQUATORIAL GUINEA",
            "FAROE ISLANDS", "GEORGIA", "GIBRALTAR", "HONDURAS",
            "JAMAICA", "LEBANON", "LIBERIA", "MALTA",
            "MARSHALL ISLANDS", "MAURITIUS", "MOLDOVA", "MONGOLIA",
            "MYANMAR", "NORTH KOREA", "PALAU", "PANAMA",
            "SAO TOME AND PRINCIPE", "SIERRA LEONE", "SRI LANKA",
            "ST KITTS AND NEVIS", "ST VINCENT AND THE GRENADINES",
            "TOGO", "TONGA", "VANUATU",
        ],
    }
    path = DATA_DIR / "flags" / "itf_foc.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"✓ ITF FOC data: {path}")


def seed_sample_sanctions():
    """Create sample sanctions entries for testing."""
    data = {
        "note": "SAMPLE DATA FOR TESTING ONLY - Not real sanctions entries",
        "entries": [
            {"name": "TEST SHIPPING CORP", "program": "IRAN-EO13846", "list": "OFAC SDN"},
            {"name": "DARK FLEET TANKERS LLC", "program": "RUSSIA-EO14024", "list": "OFAC SDN"},
            {"name": "SANCTIONED MARITIME LTD", "program": "SYRIA", "list": "EU Consolidated"},
        ],
    }
    path = DATA_DIR / "sample" / "test_sanctions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"✓ Sample sanctions data: {path}")


def main():
    print("=== Seeding Development Data ===\n")

    # Create directories
    for subdir in ["sanctions", "flags", "sample"]:
        (DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)

    seed_paris_mou()
    seed_uscg_targeted()
    seed_itf_foc()
    seed_sample_sanctions()

    print("\nDone. Data directory:", DATA_DIR)


if __name__ == "__main__":
    main()
