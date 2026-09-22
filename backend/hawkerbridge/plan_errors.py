"""Consistent optimistic concurrency errors across persistence adapters."""


class PlanMutationError(RuntimeError):
    status_code = 409


class PlanConflictError(PlanMutationError):
    def __init__(self):
        super().__init__(
            "This plan changed in another tab. Reopen it to review the latest version before saving."
        )


class PlanNotFoundError(PlanMutationError):
    status_code = 404

    def __init__(self):
        super().__init__("Plan not found in this workspace. It may have been deleted.")
