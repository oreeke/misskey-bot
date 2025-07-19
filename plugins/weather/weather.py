#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.plugin_base import PluginBase
import re
import aiohttp
from typing import Dict, Any, Optional
from loguru import logger
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class WeatherPlugin(PluginBase):
    description = "天气插件，查询指定城市的天气信息"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        if not self.api_key:
            self.enabled = False
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.geocoding_url = "https://api.openweathermap.org/geo/1.0/direct"
        self.session = None

    async def initialize(self) -> bool:
        if not self.api_key:
            logger.warning("天气插件未配置 API 密钥，插件将被禁用")
            self.enabled = False
            return False
        self.session = aiohttp.ClientSession()
        logger.info("天气插件初始化完成")
        return True

    async def cleanup(self) -> None:
        if self.session:
            await self.session.close()

    async def on_mention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            username = self._extract_username(data)
            text = data.get("text", "")
            if "天气" in text or "weather" in text:
                location_match = re.search(
                    r'(?:天气|weather)\s*([\u4e00-\u9fa5a-zA-Z\s]+)', text)
                return await self._handle_weather_request(username, location_match)
            return None
        except Exception as e:
            logger.error(f"Weather 插件处理提及时出错: {e}")
            return None

    async def on_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            username = self._extract_username(message_data)
            text = message_data.get("text", "")
            if "天气" in text:
                location_match = re.search(
                    r'(?:天气|weather)\s*([\u4e00-\u9fa5a-zA-Z\s]+)', text)
                return await self._handle_weather_request(username, location_match)
            return None
        except Exception as e:
            logger.error(f"Weather 插件处理消息时出错: {e}")
            return None

    async def _handle_weather_request(self, username: str, location_match) -> Optional[Dict[str, Any]]:
        if location_match:
            location = location_match.group(1).strip()
        else:
            location = "北京"
        self._log_plugin_action("处理天气查询", f"来自 @{username}，查询 {location}")
        weather_info = await self._get_weather(location)
        response_text = weather_info or f"抱歉，无法获取 {location} 的天气信息。"
        response = {
            "handled": True,
            "plugin_name": self.name,
            "response": response_text
        }
        if self._validate_plugin_response(response):
            return response
        else:
            logger.error(f"Weather 插件响应验证失败")
            return None

    async def _get_coordinates(self, city: str) -> Optional[tuple]:
        try:
            params = {
                "q": city,
                "limit": 1,
                "appid": self.api_key
            }
            async with self.session.get(self.geocoding_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        location = data[0]
                        lat = location["lat"]
                        lon = location["lon"]
                        display_name = location["name"]
                        if "country" in location:
                            display_name += f", {location['country']}"
                        return lat, lon, display_name
                    else:
                        return None
                else:
                    logger.warning(
                        f"Geocoding API 请求失败，状态码: {response.status}")
                    return None
        except Exception as e:
            logger.warning(f"获取城市坐标时出错: {e}")
            return None

    async def _get_weather(self, city: str) -> Optional[str]:
        try:
            coordinates = await self._get_coordinates(city)
            if not coordinates:
                return f"抱歉，找不到城市 '{city}' 的位置信息。"
            lat, lon, display_name = coordinates
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "zh_cn"
            }
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_weather_info_v25(data, display_name)
                else:
                    logger.warning(
                        f"Weather API 2.5 请求失败，状态码: {response.status}")
                    return "抱歉，天气服务暂时不可用。"
        except Exception as e:
            logger.warning(f"获取天气信息时出错: {e}")
            return "抱歉，获取天气信息时出现错误。"

    def _format_weather_info_v25(self, data: Dict[str, Any], display_name: str) -> str:
        try:
            temp = round(data["main"]["temp"])
            feels_like = round(data["main"]["feels_like"])
            humidity = data["main"]["humidity"]
            pressure = data["main"]["pressure"]
            description = data["weather"][0]["description"]
            wind_speed = data.get("wind", {}).get("speed", 0)
            visibility = data.get("visibility", 0) / \
                1000 if data.get("visibility") else 0
            weather_text = f"🌤️ {display_name} 的天气:\n"
            weather_text += f"🌡️ 温度: {temp}°C (体感 {feels_like}°C)\n"
            weather_text += f"💧 湿度: {humidity}%\n"
            weather_text += f"☁️ 天气: {description}\n"
            weather_text += f"💨 风速: {wind_speed} m/s\n"
            weather_text += f"🌊 气压: {pressure} hPa"
            if visibility > 0:
                weather_text += f"\n👁️ 能见度: {visibility:.1f} km"
            return weather_text
        except KeyError as e:
            logger.error(f"解析 Weather API 2.5 天气数据时出错: {e}")
            return "抱歉，天气数据格式异常。"

    def _format_weather_info(self, data: Dict[str, Any]) -> str:
        try:
            city = data["name"]
            country = data["sys"]["country"]
            temp = round(data["main"]["temp"])
            feels_like = round(data["main"]["feels_like"])
            humidity = data["main"]["humidity"]
            description = data["weather"][0]["description"]
            weather_text = f"🌤️ {city}, {country} 的天气:\n"
            weather_text += f"🌡️ 温度: {temp}°C (体感 {feels_like}°C)\n"
            weather_text += f"💧 湿度: {humidity}%\n"
            weather_text += f"☁️ 天气: {description}"
            return weather_text
        except KeyError as e:
            logger.error(f"解析天气数据时出错: {e}")
            return "抱歉，天气数据格式异常。"
