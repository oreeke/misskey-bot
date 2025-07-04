"""项目核心异常类定义"""

class MisskeyBotError(Exception):
    """机器人基础异常类，所有项目特定异常的基类"""
    pass


class ConfigurationError(MisskeyBotError):
    """配置错误异常，当配置文件缺失、格式错误或包含无效值时抛出"""
    pass


class APIConnectionError(MisskeyBotError):
    """API连接错误异常，当无法连接到外部API服务时抛出"""
    
    def __init__(self, service_name: str, message: str = None):
        self.service_name = service_name
        if message:
            super().__init__(f"{service_name} API连接失败: {message}")
        else:
            super().__init__(f"{service_name} API连接失败")


class APIRateLimitError(MisskeyBotError):
    """API速率限制错误异常，当API调用超过速率限制时抛出"""
    
    def __init__(self, service_name: str, retry_after: int = None):
        self.service_name = service_name
        self.retry_after = retry_after
        if retry_after:
            super().__init__(f"{service_name} API速率限制，请在{retry_after}秒后重试")
        else:
            super().__init__(f"{service_name} API速率限制")


class AuthenticationError(MisskeyBotError):
    """认证错误异常，当API密钥无效或认证失败时抛出"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"{service_name} 认证失败，请检查API密钥")


class WebSocketConnectionError(MisskeyBotError):
    """WebSocket连接错误异常，当WebSocket连接失败或断开时抛出"""
    pass


class MisskeyAPIError(MisskeyBotError):
    """Misskey API错误异常，当Misskey API调用失败时抛出"""
    
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        if status_code:
            super().__init__(f"Misskey API错误 (HTTP {status_code}): {message}")
        else:
            super().__init__(f"Misskey API错误: {message}")


class DeepSeekAPIError(MisskeyBotError):
    """DeepSeek API错误异常，当DeepSeek API调用失败时抛出"""
    
    def __init__(self, message: str, error_code: str = None):
        self.error_code = error_code
        if error_code:
            super().__init__(f"DeepSeek API错误 ({error_code}): {message}")
        else:
            super().__init__(f"DeepSeek API错误: {message}")