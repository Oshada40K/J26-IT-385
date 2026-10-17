# Owner: Dewmi - Component 04. Kept dependency-free so importing the router never loads C4 data.


class ModelsUnavailable(RuntimeError):
    """The trained model files are missing or cannot be loaded."""
