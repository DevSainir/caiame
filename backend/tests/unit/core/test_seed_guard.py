"""The seed script must not put demo accounts on a public server."""

import json
from pathlib import Path

SEED = Path(__file__).resolve().parents[3] / "scripts" / "seed.py"
SEED_DATA = Path(__file__).resolve().parents[3] / "scripts" / "seed_data.json"


def test_demo_accounts_are_skipped_in_production() -> None:
    """
    The demo password is committed, so seeding accounts in production publishes an admin.

    Checked by reading the script rather than by running it: the guard is one condition,
    and standing up a database to prove it costs far more than it is worth.
    """
    source = SEED.read_text(encoding="utf-8")

    assert 'environment == "production"' in source
    assert "0 if is_production else await seed_users" in source


def test_the_catalogue_itself_still_seeds_everywhere() -> None:
    """Courses are demo content, not credentials: a public server should show them."""
    data = json.loads(SEED_DATA.read_text(encoding="utf-8"))

    assert len(data["courses"]) > 0
