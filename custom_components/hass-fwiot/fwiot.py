class FWIOTSystem:
    """FWIOT System class."""

    def __init__(self, polling: bool) -> None:
        """Initialize the system."""
        self.polling = polling
        self.entity_ids: set[str | None] = set()
        self.logout_listener = None

class FWIOTDev():
    def __init__(self) -> None:
        self.name = ''

class FWIOTAuto():
    def __init__(self) -> None:
        self.name = ''
