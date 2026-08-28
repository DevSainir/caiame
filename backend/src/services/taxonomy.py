from models.enums import DifficultyLevel
from repos.taxonomy import AccreditationRepo, SpecializationRepo
from schemas.taxonomy import AccreditationOut, CatalogFiltersOut, SpecializationOut


class TaxonomyService:
    """
    The two lookup lists the catalogue filters by.

    Specializations and accreditations share one service because neither has behaviour of
    its own: both are read-only lists that exist to be shown side by side in one filter bar.
    They get their own file the day one of them grows a rule.
    """

    def __init__(
        self,
        *,
        specialization_repo: SpecializationRepo,
        accreditation_repo: AccreditationRepo,
    ) -> None:
        self.specialization_repo = specialization_repo
        self.accreditation_repo = accreditation_repo

    async def get_filters(self) -> CatalogFiltersOut:
        """Collect every value the catalogue filter bar offers."""
        specializations = await self.specialization_repo.list_active()
        accreditations = await self.accreditation_repo.list_active()
        return CatalogFiltersOut(
            specializations=[SpecializationOut.model_validate(item) for item in specializations],
            accreditations=[AccreditationOut.model_validate(item) for item in accreditations],
            difficulties=list(DifficultyLevel),
        )
