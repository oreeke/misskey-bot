from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

def validate_api_params(params: Dict[str, Any], required_params: list, optional_params: Dict[str, Any] = None) -> Dict[str, Any]:
    validated = {}
    for param in required_params:
        if param not in params:
            raise ValueError(f"缺少必需参数: {param}")
        validated[param] = params[param]
    if optional_params:
        for param, default_value in optional_params.items():
            validated[param] = params.get(param, default_value)
    return validated

def validate_string_param(value: Any, param_name: str, min_length: int = 0, max_length: int = None) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{param_name} 必须是字符串")
    if len(value) < min_length:
        raise ValueError(f"{param_name} 长度不能少于 {min_length} 个字符")
    if max_length and len(value) > max_length:
        raise ValueError(f"{param_name} 长度不能超过 {max_length} 个字符")
    return value

def validate_numeric_param(value: Any, param_name: str, min_value: Union[int, float] = None, max_value: Union[int, float] = None) -> Union[int, float]:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{param_name} 必须是数字")
    if min_value is not None and value < min_value:
        raise ValueError(f"{param_name} 不能小于 {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{param_name} 不能大于 {max_value}")
    return value

def validate_url_param(value: Any, param_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{param_name} 必须是字符串")
    if not value.startswith(('http://', 'https://')):
        raise ValueError(f"{param_name} 必须是有效的URL")
    return value

def validate_token_param(value: Any, param_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{param_name} 必须是字符串")
    if not value.strip():
        raise ValueError(f"{param_name} 不能为空")
    return value.strip()

def log_validation_error(error: Exception, context: str = "") -> None:
    if context:
        logger.error(f"参数验证失败 ({context}): {error}")
    else:
        logger.error(f"参数验证失败: {error}")