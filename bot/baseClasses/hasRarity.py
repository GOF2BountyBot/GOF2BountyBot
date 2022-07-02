class HasRarityMixin:
    """A mixin that simply ensures the existence of the `rarityLevel` attribute.
    """

    def __init__(self, rarityLevel: int, *args, **kwargs):
        self.rarityLevel = rarityLevel
        super().__init__(*args, **kwargs)

    