class NodeInitializationError(Exception):
    """Raised when a node fails to initialize properly."""
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Node initialization failed ({status_code}): {detail}")

