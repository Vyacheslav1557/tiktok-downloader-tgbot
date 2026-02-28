class FileTooLargeError(Exception):
    def __init__(self, size: int, limit: int):
        self.size = size
        self.limit = limit
        super().__init__(f"File is too large: {size} bytes (limit: {limit} bytes)")
