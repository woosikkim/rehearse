class Base:
    attr1 = 'a'  #: base attr1 doc

    def __init__(self):
        self.attr2 = 1  #: base attr2 doc


class Derived(Base):
    """Derived doc"""
