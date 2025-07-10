class MisskeyBotError(Exception):
    pass

class ConfigurationError(MisskeyBotError):
    pass

class APIConnectionError(MisskeyBotError):
    def __init__(self, service_name: str, message: str = None):
        self.service_name = service_name
        if message:
            super().__init__(f"{service_name} API连接失败: {message}")
        else:
            super().__init__(f"{service_name} API连接失败")

class APIRateLimitError(MisskeyBotError):
    def __init__(self, service_name: str, retry_after: int = None):
        self.service_name = service_name
        self.retry_after = retry_after
        if retry_after:
            super().__init__(f"{service_name} API速率限制，请在{retry_after}秒后重试")
        else:
            super().__init__(f"{service_name} API速率限制")

class AuthenticationError(MisskeyBotError):
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"{service_name} 认证失败，请检查API密钥")

class WebSocketConnectionError(MisskeyBotError):
    pass

class MisskeyAPIError(MisskeyBotError):
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        if status_code:
            super().__init__(f"Misskey API错误 (HTTP {status_code}): {message}")
        else:
            super().__init__(f"Misskey API错误: {message}")

class DeepSeekAPIError(MisskeyBotError):
    def __init__(self, message: str, error_code: str = None):
        self.error_code = error_code
        if error_code:
            super().__init__(f"DeepSeek API错误 ({error_code}): {message}")
        else:
            super().__init__(f"DeepSeek API错误: {message}")