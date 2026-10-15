class A:
    """A."""

    @classmethod
    @property
    def f(cls):
        """Some class property."""
        return "property"

    @property
    def g(self):
        """Regular property."""
        return 1


class B(A):
    """Subclass inheriting f."""
