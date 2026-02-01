"""Custom exceptions for the services module"""


class DeadTokenError(Exception):
    """Exception raised when a token is detected as dead (progress stuck at 0%)"""
    def __init__(self, token_id: int, task_id: str, message: str = "Dead token detected"):
        self.token_id = token_id
        self.task_id = task_id
        super().__init__(message)


class InvalidTokenError(Exception):
    """Exception raised when a token is invalid (401 auth error)"""
    def __init__(self, token_id: int, message: str = "Token authentication failed"):
        self.token_id = token_id
        super().__init__(message)


class HeavyLoadError(Exception):
    """Exception raised when heavy_load error is encountered (需要切换 token 重试)"""
    def __init__(self, token_id: int, message: str = "Heavy load detected, please switch token"):
        self.token_id = token_id
        super().__init__(message)
