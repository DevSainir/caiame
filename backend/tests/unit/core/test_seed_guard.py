"""The seed script must not put demo accounts on a public server."""

import json
from pathlib import Path

SEED = Path(__file__).resolve().parents[3] / "scripts" / "seed.py"
SEED_DATA = Path(__file__).resolve().parents[3] / "scripts" / "seed_data.json"


def test_demo_accounts_are_skipped_in_production() -> None:
    """
    The demo password is committed, so seeding accounts in production publishes an admin.

    Reviews and progress are inside the same guard: both are signed by those accounts, and
    inventing students on a live server is worse than an empty block.

    Checked by reading the script rather than by running it: the guard is one condition,
    and standing up a database to prove it costs far more than it is worth.
    """
    source = SEED.read_text(encoding="utf-8")

    assert 'environment == "production"' in source
    guarded = source.split("if not is_production:")[1]
    for call in ("seed_users(", "seed_review_authors(", "seed_reviews(", "seed_progress("):
        assert call in guarded


def test_the_catalogue_and_its_outline_seed_everywhere() -> None:
    """Modules and questions are content, not credentials: a public server should show them."""
    source = SEED.read_text(encoding="utf-8")

    guarded = source.split("if not is_production:")[1]
    for call in ("seed_units(", "seed_questions("):
        assert call in source
        assert call not in guarded


def test_the_catalogue_itself_still_seeds_everywhere() -> None:
    """Courses are demo content, not credentials: a public server should show them."""
    data = json.loads(SEED_DATA.read_text(encoding="utf-8"))

    assert len(data["courses"]) > 0
