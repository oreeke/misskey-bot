#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import aiohttp
from typing import Dict, Any, Optional
from loguru import logger
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.plugin_base import PluginBase

class WeatherPlugin(PluginBase):
    description = "天气查询插件，支持查询指定城市的天气信息"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        if not self.api_key:
            self.enabled = False
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"
        self.geocoding_url = "https://api.openweathermap.org/geo/1.0/direct"
        
    async def initialize(self) -> bool:
        if not self.api_key:
            logger.warning("天气插件未配置 API 密钥，插件将被禁用")
            self.enabled = False
            return False
        logger.info("天气插件初始化完成")
        return True
    
    async def cleanup(self) -> None:
        logger.info("天气插件清理完成")
    
    async def on_mention(self, mention_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        text = mention_data.get("text", "")
        user = mention_data.get("user", {})
        username = user.get("username", "用户")
        weather_match = re.search(r'天气\s*([\u4e00-\u9fa5a-zA-Z\s]+)', text)
        if weather_match:
            city = weather_match.group(1).strip()
            if city:
                weather_info = await self._get_weather(city)
                if weather_info:
                    logger.info(f"天气插件为 @{username} 查询 {city} 的天气")
                    return {
                        "handled": True,
                        "plugin_name": "Weather",
                        "response": f"@{username} {weather_info}"
                    }
        return None
    
    async def on_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        text = message_data.get("text", "")
        weather_match = re.search(r'天气\s*([\u4e00-\u9fa5a-zA-Z\s]+)', text)
        if weather_match:
            city = weather_match.group(1).strip()
            if city:
                weather_info = await self._get_weather(city)
                if weather_info:
                    logger.info(f"天气插件查询 {city} 的天气")
                    return {
                        "handled": True,
                        "plugin_name": "Weather",
                        "response": weather_info
                    }
        return None
    
    async def _get_coordinates(self, city: str) -> Optional[tuple]:
        try:
            params = {
                "q": city,
                "limit": 1,
                "appid": self.api_key
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(self.geocoding_url, params=params) as response:
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
                        logger.error(f"Geocoding API 请求失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"获取城市坐标时出错: {e}")
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
                "lang": "zh_cn",
                "exclude": "minutely,alerts"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_weather_info_v3(data, display_name)
                    else:
                        logger.error(f"One Call API 请求失败，状态码: {response.status}")
                        return "抱歉，天气服务暂时不可用。"
        except Exception as e:
            logger.error(f"获取天气信息时出错: {e}")
            return "抱歉，获取天气信息时出现错误。"
    
    def _format_weather_info_v3(self, data: Dict[str, Any], display_name: str) -> str:
        try:
            current = data["current"]
            temp = round(current["temp"])
            feels_like = round(current["feels_like"])
            humidity = current["humidity"]
            description = current["weather"][0]["description"]
            wind_speed = current.get("wind_speed", 0)
            uvi = current.get("uvi", 0)
            weather_text = f"🌤️ {display_name} 的天气:\n"
            weather_text += f"🌡️ 温度: {temp}°C (体感 {feels_like}°C)\n"
            weather_text += f"💧 湿度: {humidity}%\n"
            weather_text += f"☁️ 天气: {description}\n"
            weather_text += f"💨 风速: {wind_speed} m/s\n"
            weather_text += f"☀️ 紫外线指数: {uvi}"
            if "daily" in data and len(data["daily"]) >= 2:
                daily = data["daily"]
                today = daily[0]
                tomorrow = daily[1]
                weather_text += "\n\n📅 今日预报:\n"
                weather_text += f"🌅 最高: {round(today['temp']['max'])}°C\n"
                weather_text += f"🌙 最低: {round(today['temp']['min'])}°C\n"
                weather_text += "\n📅 明日预报:\n"
                weather_text += f"🌅 最高: {round(tomorrow['temp']['max'])}°C\n"
                weather_text += f"🌙 最低: {round(tomorrow['temp']['min'])}°C\n"
                weather_text += f"☁️ 天气: {tomorrow['weather'][0]['description']}"
            return weather_text
        except KeyError as e:
            logger.error(f"解析 One Call API 3.0 天气数据时出错: {e}")
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