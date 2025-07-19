class MisskeyBotError(Exception):
    def __init__(self, message: str = None):
        self.message = message or "发生了未知错误"
        super().__init__(self.message)


class ConfigurationError(MisskeyBotError):
    def __init__(self, message: str = None, config_path: str = None):
        self.config_path = config_path
        if config_path:
            error_msg = f"配置错误 ({config_path}): {message or '配置文件存在问题'}"
        else:
            error_msg = message or "配置文件存在问题"
        super().__init__(error_msg)


class APIConnectionError(MisskeyBotError):
    def __init__(self, service_name: str, message: str = None):
        self.service_name = service_name
        if message:
            super().__init__(f"{service_name} API 连接失败: {message}")
        else:
            super().__init__(f"{service_name} API 连接失败")


class APIRateLimitError(MisskeyBotError):
    def __init__(self, service_name: str, retry_after: int = None):
        self.service_name = service_name
        self.retry_after = retry_after
        if retry_after:
            super().__init__(f"{service_name} API 速率限制，请在{retry_after}秒后重试")
        else:
            super().__init__(f"{service_name} API 速率限制")


class AuthenticationError(MisskeyBotError):
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"{service_name} 认证失败，请检查 API 密钥")


class WebSocketConnectionError(MisskeyBotError):
    def __init__(self, message: str = None, reconnect_attempts: int = None):
        self.reconnect_attempts = reconnect_attempts
        if reconnect_attempts is not None:
            error_msg = f"WebSocket 连接失败 (重试次数: {reconnect_attempts}): {message or 'WebSocket 连接中断'}"
        else:
            error_msg = message or "WebSocket 连接失败"
        super().__init__(error_msg)


class MisskeyAPIError(MisskeyBotError):
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        if status_code:
            super().__init__(f"Misskey API 错误 (HTTP {status_code}): {message}")
        else:
            super().__init__(f"Misskey API 错误: {message}")


class DeepSeekAPIError(MisskeyBotError):
    def __init__(self, message: str, error_code: str = None):
        self.error_code = error_code
        if error_code:
            super().__init__(f"DeepSeek API 错误 ({error_code}): {message}")
        else:
            super().__init__(f"DeepSeek API 错误: {message}")
