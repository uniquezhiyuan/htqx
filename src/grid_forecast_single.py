# =============================================================================
# 中国未来 10 日任意区域 0.1° 网格预报单要素等值线绘图脚本
#
# 功能说明
#   1. 调用海天气象网格预报 API（https://htqx.cn/），获取指定时次与指定
#      气象变量的全国 0.1° 网格预报数据。
#   2. 校验经纬度坐标与二维网格数据，屏蔽 -9999 缺测值，并按用户指定
#      的经纬度方格裁剪区域数据。
#   3. 绘制现代简约、配色鲜明的高分辨率单要素填色等值线图，叠加行政
#      边界、省名标注、正方形经纬度网格与图例（标注气象变量名称及单位）。
#   4. 若本地没有省界缓存，会自动下载并缓存至 data/china_provinces.geojson。
#
# -----------------------------------------------------------------------------
# 用户可变参数说明与限制
# -----------------------------------------------------------------------------
# 1. API_KEY (str)
#      海天气象接口密钥，不能为空。在海天气象个人中心查看26位 API Key。
#
# 2. FORECAST_TIME (str)
#      预报时次，格式必须为 10 位数字 YYYYMMDDHH（北京时间），且必须在
#      未来 10 日（起报时间至起报后 240 小时）范围内。
#
# 3. VARIABLE (str)
#      气象变量英文标识符，只能从以下 21 个变量中选择其一：
#        - "temperature_2m"          : 2米气温 (2 m air temperature, °C)
#        - "dew_point_2m"            : 2米露点温度 (2 m dew point temperature, °C)
#        - "apparent_temperature"    : 体感温度 (Apparent temperature, °C)
#        - "pressure_msl"            : 海平面气压 (Mean sea-level pressure, hPa)
#        - "surface_pressure"        : 地面气压 (Surface pressure, hPa)
#        - "relative_humidity_2m"    : 2米相对湿度 (2 m relative humidity, %)
#        - "wind_speed_10m"          : 10米风速 (10 m wind speed, m/s)
#        - "wind_speed_100m"         : 100米风速 (100 m wind speed, m/s)
#        - "wind_gusts_10m"          : 10米阵风 (10 m wind gusts, m/s)
#        - "wind_direction_10m"      : 10米风向 (10 m wind direction, °)
#        - "wind_direction_100m"     : 100米风向 (100 m wind direction, °)
#        - "precipitation"           : 总降水量 (Total precipitation, mm)
#        - "snowfall"                : 降雪量 (Snowfall, cm)
#        - "cloud_cover"             : 总云量 (Total cloud cover, %)
#        - "visibility"              : 能见度 (Visibility, m)
#        - "weather_code"            : 天气现象代码 (Weather code (WMO), WMO code)
#        - "shortwave_radiation"     : 短波辐射 (Shortwave radiation, W/m²)
#        - "direct_radiation"        : 直接辐射 (Direct radiation, W/m²)
#        - "diffuse_radiation"       : 散射辐射 (Diffuse radiation, W/m²)
#        - "direct_normal_irradiance": 直接法向辐照度 (Direct normal irradiance, W/m²)
#        - "terrestrial_radiation"   : 地球长波辐射 (Terrestrial radiation, W/m²)
#
# 4. LON_MIN, LON_MAX, LAT_MIN, LAT_MAX (float)
#      目标区域经纬度方格边界，需位于中国大致范围（经度 73.0°E ~ 136.0°E，
#      纬度 3.0°N ~ 54.0°N）内，且满足 LON_MIN < LON_MAX、LAT_MIN < LAT_MAX。
#
# 5. OUTPUT_DIR (Path)
#      输出图片目录，脚本会自动创建目录并保存 PNG 文件。
# =============================================================================
"""Fetch and visualize a single HtMeteo 0.1-degree forecast variable over a custom region."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib import patheffects
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap

# =============================================================================
# 用户运行参数常量（请根据需要手动修改）
# =============================================================================
# API_KEY = os.getenv("HTMETEO_API_KEY", "").strip()

API_KEY = "2js7rY7j89JgbNH76Ggh7TF5r6"  # 请在海天气象个人中心查看26位 API Key：https://htqx.cn/
FORECAST_TIME = "2026120214"  # 格式 YYYYMMDDHH，须在未来 10 日内
VARIABLE = "relative_humidity_2m"  # 须为下方 VARIABLES 中的 21 个变量之一
LON_MIN = 73.0  # 区域西边界经度 (°E)，建议范围 73.0 ~ 136.0
LON_MAX = 114.0  # 区域东边界经度 (°E)，建议范围 73.0 ~ 136.0
LAT_MIN = 24.0  # 区域南边界纬度 (°N)，建议范围 3.0 ~ 54.0
LAT_MAX = 51.0  # 区域北边界纬度 (°N)，建议范围 3.0 ~ 54.0
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "figures"

API_URL = "https://htqx.cn/meteo/api/forecast/grid"
BOUNDARY_URL = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = PROJECT_ROOT / "data" / "china_provinces.geojson"
CHINA_LON_BOUNDS = (73.0, 136.0)
CHINA_LAT_BOUNDS = (3.0, 54.0)
MAX_FORECAST_HOURS = 240  # 未来 10 日 = 240 小时

VARIABLES: dict[str, tuple[str, str, str, str]] = {
    "temperature_2m": ("2米气温", "2 m air temperature", "°C", "temperature"),
    "dew_point_2m": ("2米露点温度", "2 m dew point temperature", "°C", "temperature"),
    "apparent_temperature": ("体感温度", "Apparent temperature", "°C", "temperature"),
    "pressure_msl": ("海平面气压", "Mean sea-level pressure", "hPa", "pressure"),
    "surface_pressure": ("地面气压", "Surface pressure", "hPa", "pressure"),
    "relative_humidity_2m": ("2米相对湿度", "2 m relative humidity", "%", "humidity"),
    "wind_speed_10m": ("10米风速", "10 m wind speed", "m/s", "wind_speed"),
    "wind_speed_100m": ("100米风速", "100 m wind speed", "m/s", "wind_speed"),
    "wind_gusts_10m": ("10米阵风", "10 m wind gusts", "m/s", "wind_speed"),
    "wind_direction_10m": ("10米风向", "10 m wind direction", "°", "wind_direction"),
    "wind_direction_100m": ("100米风向", "100 m wind direction", "°", "wind_direction"),
    "precipitation": ("总降水量", "Total precipitation", "mm", "precipitation"),
    "snowfall": ("降雪量", "Snowfall", "cm", "precipitation"),
    "cloud_cover": ("总云量", "Total cloud cover", "%", "humidity"),
    "visibility": ("能见度", "Visibility", "m", "visibility"),
    "weather_code": ("天气现象代码", "Weather code (WMO)", "WMO code", "weather_code"),
    "shortwave_radiation": ("短波辐射", "Shortwave radiation", "W/m²", "radiation"),
    "direct_radiation": ("直接辐射", "Direct radiation", "W/m²", "radiation"),
    "diffuse_radiation": ("散射辐射", "Diffuse radiation", "W/m²", "radiation"),
    "direct_normal_irradiance": (
        "直接法向辐照度",
        "Direct normal irradiance",
        "W/m²",
        "radiation",
    ),
    "terrestrial_radiation": (
        "地球长波辐射",
        "Terrestrial radiation",
        "W/m²",
        "radiation",
    ),
}

PROVINCE_NAMES = {
    110000: "北京",
    120000: "天津",
    130000: "河北",
    140000: "山西",
    150000: "内蒙古",
    210000: "辽宁",
    220000: "吉林",
    230000: "黑龙江",
    310000: "上海",
    320000: "江苏",
    330000: "浙江",
    340000: "安徽",
    350000: "福建",
    360000: "江西",
    370000: "山东",
    410000: "河南",
    420000: "湖北",
    430000: "湖南",
    440000: "广东",
    450000: "广西",
    460000: "海南",
    500000: "重庆",
    510000: "四川",
    520000: "贵州",
    530000: "云南",
    540000: "西藏",
    610000: "陕西",
    620000: "甘肃",
    630000: "青海",
    640000: "宁夏",
    650000: "新疆",
    710000: "台湾",
    810000: "香港",
    820000: "澳门",
}

WEATHER_CODE_BOUNDS = [-0.5, 0.5, 3.5, 48.5, 57.5, 67.5, 77.5, 82.5, 86.5, 99.5]
WEATHER_CODE_TICKS = [0, 2, 46, 54, 64, 74, 81, 85, 93]
WEATHER_CODE_LABELS = [
    "晴",
    "多云",
    "雾",
    "毛毛雨",
    "降雨",
    "降雪",
    "阵雨",
    "阵雪",
    "雷暴",
]

# 现代极简高活力自定义色板
VIBRANT_WEATHER_COLORS = [
    "#FFD60A",  # 晴 - 明亮阳光黄
    "#7DD3FC",  # 多云 - 清透天蓝
    "#E2E8F0",  # 雾 - 柔亮云雾灰白
    "#38BDF8",  # 毛毛雨 - 鲜亮水蓝
    "#0284C7",  # 降雨 - 活力蔚蓝
    "#A855F7",  # 降雪 - 明快电光紫
    "#06B6D4",  # 阵雨 - 动感青蓝
    "#EC4899",  # 阵雪 - 鲜艳玫粉
    "#F97316",  # 雷暴 - 炽热活力橙
]

TEMP_CMAP = LinearSegmentedColormap.from_list(
    "vibrant_temp",
    [
        "#1D4ED8",  # 强冷钴蓝
        "#0284C7",  # 活力蓝
        "#22D3EE",  # 明亮青
        "#F8FAFC",  # 零度/中性极简白
        "#FACC15",  # 暖阳黄
        "#FB923C",  # 活力橙
        "#EF4444",  # 热情红
        "#BE123C",  # 高温玫红
    ],
    N=256,
)

PRECIP_CMAP = LinearSegmentedColormap.from_list(
    "vibrant_precip",
    [
        "#F8FAFC",  # 极简净白
        "#BAE6FD",  # 浅天蓝
        "#38BDF8",  # 明亮水蓝
        "#2563EB",  # 活力宝蓝
        "#7C3AED",  # 电光紫
        "#EC4899",  # 鲜艳洋红
        "#F97316",  # 强降水橙
    ],
    N=256,
)

HUMIDITY_CMAP = LinearSegmentedColormap.from_list(
    "vibrant_humidity",
    [
        "#FEF3C7",  # 干燥暖浅黄
        "#67E8F9",  # 清新青
        "#38BDF8",  # 活力天蓝
        "#2563EB",  # 亮蓝
        "#4F46E5",  # 饱和靛蓝
    ],
    N=256,
)

WIND_SPEED_CMAP = LinearSegmentedColormap.from_list(
    "vibrant_wind",
    [
        "#F0FDF4",  # 微风浅薄荷
        "#34D399",  # 清新翠绿
        "#FACC15",  # 活力黄
        "#FB923C",  # 动感橙
        "#F43F5E",  # 强风珊瑚红
        "#9333EA",  # 疾风紫
    ],
    N=256,
)

RADIATION_CMAP = LinearSegmentedColormap.from_list(
    "vibrant_radiation",
    [
        "#EEF2FF",  # 极简浅靛白
        "#93C5FD",  # 晨光蓝
        "#FDE047",  # 明亮日照黄
        "#FB923C",  # 暖橙
        "#EF4444",  # 强辐射红
    ],
    N=256,
)

GENERAL_CMAP = LinearSegmentedColormap.from_list(
    "vibrant_general",
    [
        "#06B6D4",  # 鲜亮青
        "#10B981",  # 活力绿
        "#FACC15",  # 明黄
        "#F97316",  # 活力橙
        "#EC4899",  # 亮玫红
        "#8B5CF6",  # 活力紫
    ],
    N=256,
)


@dataclass
class GridForecast:
    latitudes: np.ndarray
    longitudes: np.ndarray
    values: np.ndarray
    metadata: dict[str, Any]


@dataclass
class PlotStyle:
    levels: np.ndarray
    cmap: Any
    norm: Any
    ticks: list[float]
    tick_labels: list[str] | None
    extend: str
    contour_levels: list[float]


def get_issue_time_bjt() -> datetime:
    """返回当前日期前一日 20:00（北京时间 UTC+8）。"""
    bjt = timezone(timedelta(hours=8))
    now_bjt = datetime.now(bjt)
    return (now_bjt - timedelta(days=1)).replace(
        hour=20,
        minute=0,
        second=0,
        microsecond=0,
    )


def validate_inputs(
    api_key: str,
    forecast_time: str,
    variable: str,
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    issue_time: datetime,
) -> datetime:
    """校验用户配置参数，不符合限制时抛出明确异常。"""
    if not api_key or not api_key.strip() or api_key == "你的_API_KEY":
        raise ValueError("请先在代码顶部常量区配置有效的 API_KEY。")

    if not forecast_time or len(forecast_time) != 10 or not forecast_time.isdigit():
        raise ValueError("FORECAST_TIME 必须为 10 位数字，格式 YYYYMMDDHH。")
    try:
        forecast_dt = datetime.strptime(forecast_time, "%Y%m%d%H").replace(
            tzinfo=timezone(timedelta(hours=8))
        )
    except ValueError as exc:
        raise ValueError("FORECAST_TIME 不是合法的日期与小时。") from exc

    lead_seconds = (forecast_dt - issue_time).total_seconds()
    if lead_seconds < 0 or lead_seconds > MAX_FORECAST_HOURS * 3600:
        raise ValueError(
            f"FORECAST_TIME 须在未来 10 日内（起报时间 {issue_time:%Y-%m-%d %H:%M} "
            f"至 +{MAX_FORECAST_HOURS} 小时）。"
        )

    if variable not in VARIABLES:
        valid_vars = ", ".join(VARIABLES.keys())
        raise ValueError(
            f"不支持的气象变量 '{variable}'，请从以下 21 个变量中选择：{valid_vars}"
        )

    if not (
        np.isfinite(lon_min)
        and np.isfinite(lon_max)
        and np.isfinite(lat_min)
        and np.isfinite(lat_max)
    ):
        raise ValueError("经纬度范围必须为有限数值。")
    if lon_min >= lon_max:
        raise ValueError("经度下界 LON_MIN 必须小于经度上界 LON_MAX。")
    if lat_min >= lat_max:
        raise ValueError("纬度下界 LAT_MIN 必须小于纬度上界 LAT_MAX。")
    if lon_min < CHINA_LON_BOUNDS[0] or lon_max > CHINA_LON_BOUNDS[1]:
        raise ValueError(
            f"经度范围须位于中国区域 {CHINA_LON_BOUNDS[0]}°E ~ {CHINA_LON_BOUNDS[1]}°E 内。"
        )
    if lat_min < CHINA_LAT_BOUNDS[0] or lat_max > CHINA_LAT_BOUNDS[1]:
        raise ValueError(
            f"纬度范围须位于中国区域 {CHINA_LAT_BOUNDS[0]}°N ~ {CHINA_LAT_BOUNDS[1]}°N 内。"
        )

    return forecast_dt


def fetch_grid(time: str, meteo_type: str, api_key: str) -> GridForecast:
    """获取并校验单个气象变量的网格预报数据（不泄露 API Key）。"""
    url = f"{API_URL}/{time}/{meteo_type}/{api_key}"
    try:
        response = requests.get(url, timeout=(10, 90))
    except requests.RequestException as exc:
        raise RuntimeError(f"{meteo_type}: 请求失败 ({type(exc).__name__})。") from None

    if response.status_code != 200:
        raise RuntimeError(f"{meteo_type}: 接口返回 HTTP {response.status_code}。")

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"{meteo_type}: 接口返回内容不是合法 JSON。") from None

    if not isinstance(payload, dict):
        raise RuntimeError(f"{meteo_type}: 接口返回根节点须为 JSON 对象。")

    required_keys = {"metadata", "lats", "lons", "data"}
    missing_keys = required_keys.difference(payload)
    if missing_keys:
        raise RuntimeError(
            f"{meteo_type}: 接口返回缺少字段 " + ", ".join(sorted(missing_keys))
        )

    metadata = payload["metadata"]
    if not isinstance(metadata, dict):
        raise RuntimeError(f"{meteo_type}: metadata 须为 JSON 对象。")

    try:
        latitudes = np.asarray(payload["lats"], dtype=np.float32)
        longitudes = np.asarray(payload["lons"], dtype=np.float32)
        values = np.asarray(payload["data"], dtype=np.float32)
    except (TypeError, ValueError):
        raise RuntimeError(f"{meteo_type}: 经纬度和网格数据必须为数值。") from None

    if latitudes.ndim != 1 or longitudes.ndim != 1 or values.ndim != 2:
        raise RuntimeError(f"{meteo_type}: 坐标或网格数据维度异常。")
    if values.shape != (latitudes.size, longitudes.size):
        raise RuntimeError(f"{meteo_type}: 网格数据形状与经纬度长度不匹配。")

    declared_shape = metadata.get("shape")
    if declared_shape is not None and tuple(declared_shape) != values.shape:
        raise RuntimeError(f"{meteo_type}: 网格数据形状与 metadata.shape 不一致。")

    metadata["nodata_value"] = metadata.get("nodata_value", -9999)
    return GridForecast(
        latitudes=latitudes,
        longitudes=longitudes,
        values=values,
        metadata=metadata,
    )


def subset_grid_to_box(
    grid: GridForecast,
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
) -> GridForecast:
    """按指定经纬度方格裁剪网格数据（兼容升序或降序坐标轴）。"""
    lons = grid.longitudes
    lats = grid.latitudes
    vals = grid.values

    lon_order = np.argsort(lons)
    lons_sorted = lons[lon_order]
    vals_lon_sorted = vals[:, lon_order]

    lat_order = np.argsort(lats)
    lats_sorted = lats[lat_order]
    vals_sorted = vals_lon_sorted[lat_order, :]

    lon_idx = np.where((lons_sorted >= lon_min - 0.1) & (lons_sorted <= lon_max + 0.1))[0]
    lat_idx = np.where((lats_sorted >= lat_min - 0.1) & (lats_sorted <= lat_max + 0.1))[0]

    if lon_idx.size < 2 or lat_idx.size < 2:
        raise ValueError(
            f"所选区域 [{lon_min}°E~{lon_max}°E, {lat_min}°N~{lat_max}°N] 内有效网格点不足。"
        )

    sub_lons = lons_sorted[lon_idx[0] : lon_idx[-1] + 1]
    sub_lats = lats_sorted[lat_idx[0] : lat_idx[-1] + 1]
    sub_vals = vals_sorted[lat_idx[0] : lat_idx[-1] + 1, lon_idx[0] : lon_idx[-1] + 1]

    updated_meta = dict(grid.metadata)
    updated_meta["shape"] = sub_vals.shape
    return GridForecast(
        latitudes=sub_lats,
        longitudes=sub_lons,
        values=sub_vals,
        metadata=updated_meta,
    )


def load_boundary_features() -> list[dict[str, Any]]:
    """读取本地缓存的省界 GeoJSON，若不存在则下载并缓存。"""
    if BOUNDARY_PATH.exists():
        try:
            with BOUNDARY_PATH.open(encoding="utf-8") as boundary_file:
                payload = json.load(boundary_file)
        except (OSError, json.JSONDecodeError):
            raise RuntimeError(f"无法读取省界缓存文件: {BOUNDARY_PATH}") from None
    else:
        try:
            response = requests.get(BOUNDARY_URL, timeout=30)
        except requests.RequestException as exc:
            raise RuntimeError(f"省界数据下载失败 ({type(exc).__name__})。") from None
        if response.status_code != 200:
            raise RuntimeError(f"省界数据源返回 HTTP {response.status_code}。")
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError("省界数据源返回非合法 JSON。") from None
        BOUNDARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        BOUNDARY_PATH.write_bytes(response.content)

    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list) or not features:
        raise RuntimeError("省界数据中不包含有效要素。")
    return features


def geometry_rings(geometry: dict[str, Any]) -> list[np.ndarray]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        polygons = [coordinates]
    elif geometry_type == "MultiPolygon":
        polygons = coordinates
    else:
        return []

    rings = []
    for polygon in polygons:
        for ring in polygon:
            points = np.asarray(ring, dtype=np.float32)
            if points.ndim == 2 and points.shape[0] > 1 and points.shape[1] >= 2:
                rings.append(points[:, :2])
    return rings


def feature_centroid(feature: dict[str, Any]) -> tuple[float, float] | None:
    properties = feature.get("properties", {})
    centroid = properties.get("centroid")
    if isinstance(centroid, list) and len(centroid) >= 2:
        return float(centroid[0]), float(centroid[1])

    geometry = feature.get("geometry") or {}
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        polygons = [coordinates]
    elif geometry_type == "MultiPolygon":
        polygons = coordinates
    else:
        return None

    largest_center = None
    largest_area = 0.0
    for polygon in polygons:
        if not polygon:
            continue
        ring = np.asarray(polygon[0], dtype=np.float64)
        if ring.ndim != 2 or ring.shape[0] < 3:
            continue
        x = ring[:, 0]
        y = ring[:, 1]
        cross = x[:-1] * y[1:] - x[1:] * y[:-1]
        area_twice = float(cross.sum())
        area = abs(area_twice)
        if area <= largest_area:
            continue
        if area < 1e-8:
            center = (float(x.mean()), float(y.mean()))
        else:
            center = (
                float(((x[:-1] + x[1:]) * cross).sum() / (3 * area_twice)),
                float(((y[:-1] + y[1:]) * cross).sum() / (3 * area_twice)),
            )
        largest_area = area
        largest_center = center
    return largest_center


def masked_values(grid: GridForecast) -> np.ma.MaskedArray:
    values = grid.values
    nodata = float(grid.metadata["nodata_value"])
    return np.ma.masked_where(~np.isfinite(values) | (values == nodata), values)


def variable_unit(variable: str, grid: GridForecast) -> str:
    if variable == "weather_code":
        return "WMO code"
    unit = str(grid.metadata.get("units", "")).strip()
    if unit and "\ufffd" not in unit:
        return unit
    return VARIABLES[variable][2]


def variable_style(variable: str, values: np.ma.MaskedArray) -> PlotStyle:
    category = VARIABLES[variable][3]
    valid = values.compressed()
    if valid.size == 0:
        raise RuntimeError(f"{variable}: 裁剪区域内无有效观测/预报数据。")

    if category == "weather_code":
        levels = np.asarray(WEATHER_CODE_BOUNDS, dtype=float)
        cmap = ListedColormap(VIBRANT_WEATHER_COLORS)
        return PlotStyle(
            levels,
            cmap,
            BoundaryNorm(levels, cmap.N, clip=True),
            WEATHER_CODE_TICKS,
            WEATHER_CODE_LABELS,
            "neither",
            [],
        )

    if category == "wind_direction":
        levels = np.linspace(0, 360, 13)
        hsv_cmap = plt.get_cmap("hsv")
        cmap = ListedColormap(hsv_cmap(np.linspace(0, 1, len(levels) - 1, endpoint=False)))
        return PlotStyle(
            levels,
            cmap,
            BoundaryNorm(levels, cmap.N, clip=True),
            [0, 90, 180, 270, 360],
            None,
            "neither",
            [90, 180, 270],
        )

    if category == "temperature":
        limit = max(abs(float(valid.min())), abs(float(valid.max())))
        if limit == 0:
            limit = 1.0
        levels = np.linspace(-limit, limit, 15)
        cmap = ListedColormap(TEMP_CMAP(np.linspace(0.04, 0.96, len(levels) + 1)))
        return PlotStyle(
            levels,
            cmap,
            BoundaryNorm(levels, cmap.N, extend="both"),
            [float(level) for level in levels[::2]],
            None,
            "both",
            [float(level) for level in levels[2:-1:2]],
        )

    if category == "precipitation":
        levels = np.asarray(
            [0, 0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 200],
            dtype=float,
        )
        cmap = ListedColormap(PRECIP_CMAP(np.linspace(0.05, 0.98, len(levels))))
        return PlotStyle(
            levels,
            cmap,
            BoundaryNorm(levels, cmap.N, extend="max"),
            [0, 1, 5, 10, 25, 50, 100, 200],
            None,
            "max",
            [1, 5, 10, 25, 50, 100],
        )

    if category == "humidity":
        levels = np.linspace(0, 100, 11)
        cmap = ListedColormap(HUMIDITY_CMAP(np.linspace(0.06, 0.96, len(levels) - 1)))
        return PlotStyle(
            levels,
            cmap,
            BoundaryNorm(levels, cmap.N, clip=True),
            [0, 20, 40, 60, 80, 100],
            None,
            "neither",
            [20, 40, 60, 80],
        )

    if category == "wind_speed":
        source_cmap = WIND_SPEED_CMAP
    elif category == "radiation":
        source_cmap = RADIATION_CMAP
    else:
        source_cmap = GENERAL_CMAP

    vmin = float(np.percentile(valid, 1))
    vmax = float(np.percentile(valid, 99))
    if vmax <= vmin:
        vmax = vmin + 1.0
    levels = np.linspace(vmin, vmax, 13)
    cmap = ListedColormap(source_cmap(np.linspace(0.05, 0.96, len(levels) + 1)))
    return PlotStyle(
        levels,
        cmap,
        BoundaryNorm(levels, cmap.N, extend="both"),
        [float(level) for level in levels[::2]],
        None,
        "both",
        [float(level) for level in levels[1:-1:2]],
    )


def choose_grid_step(span: float) -> float:
    """根据经纬度跨度选择清晰疏朗的统一经纬度网格步长。"""
    if span <= 4.0:
        return 0.5
    if span <= 10.0:
        return 1.0
    if span <= 20.0:
        return 2.0
    if span <= 35.0:
        return 5.0
    return 10.0


def draw_boundaries_and_labels(
    axes: Any,
    features: list[dict[str, Any]],
    segments: list[np.ndarray],
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
) -> None:
    """绘制清晰醒目的行政边界与区域内省名标注。"""
    axes.add_collection(
        LineCollection(
            segments,
            colors="#1E293B",
            linewidths=1.15,
            alpha=0.92,
            zorder=4,
        )
    )

    text_effect = [patheffects.withStroke(linewidth=1.4, foreground="white", alpha=0.9)]
    province_box = {
        "boxstyle": "round,pad=0.22",
        "facecolor": "white",
        "edgecolor": "#94A3B8",
        "linewidth": 0.45,
        "alpha": 0.42,
    }

    for feature in features:
        properties = feature.get("properties") or {}
        try:
            adcode = int(properties.get("adcode"))
        except (TypeError, ValueError):
            continue
        province = PROVINCE_NAMES.get(adcode)
        if province is None:
            continue

        centroid = feature_centroid(feature)
        if centroid is None:
            continue
        cx, cy = centroid
        if lon_min <= cx <= lon_max and lat_min <= cy <= lat_max:
            axes.text(
                cx,
                cy,
                province,
                fontsize=9.2,
                fontweight="bold",
                color="#0F172A",
                ha="center",
                va="center",
                bbox=province_box,
                zorder=5,
                path_effects=text_effect,
            )


def plot_regional_grid(
    variable: str,
    grid: GridForecast,
    boundary_features: list[dict[str, Any]],
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    issue_time: datetime,
    forecast_dt: datetime,
    output_path: Path,
) -> Path:
    """绘制指定区域、指定时次、指定气象变量的现代紧凑等值线图。"""
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    boundary_segments = []
    for feature in boundary_features:
        geometry = feature.get("geometry") or {}
        boundary_segments.extend(geometry_rings(geometry))
    if not boundary_segments:
        raise RuntimeError("省界数据中不包含可绘制的边界线段。")

    chinese_name, english_name, _, _ = VARIABLES[variable]
    unit = variable_unit(variable, grid)
    values = masked_values(grid)
    style = variable_style(variable, values)

    figure = plt.figure(figsize=(11.4, 9.8), facecolor="#F8FAFC")

    # 主标题与下方说明小字拉开距离，避免压盖，同时整体紧凑排版
    figure.suptitle(
        "中国未来10日任意区域0.1°网格预报",
        fontsize=19,
        fontweight="bold",
        color="#0F172A",
        y=0.968,
    )
    region_subtitle = (
        f"区域范围：{lon_min:.1f}°E ~ {lon_max:.1f}°E，{lat_min:.1f}°N ~ {lat_max:.1f}°N"
        f"  ·  要素：{chinese_name} ({english_name})"
    )
    figure.text(
        0.5,
        0.922,
        region_subtitle,
        ha="center",
        fontsize=10.5,
        fontweight="bold",
        color="#334155",
    )

    axes = figure.add_axes([0.09, 0.20, 0.85, 0.685])
    axes.set_facecolor("#F1F5F9")
    axes.set_xlim(lon_min, lon_max)
    axes.set_ylim(lat_min, lat_max)

    # 统一经纬度坐标间隔，并将经纬网设为正方形比例
    grid_step = choose_grid_step(max(lon_max - lon_min, lat_max - lat_min))
    axes.set_aspect("equal", adjustable="box")

    x_start = np.ceil(lon_min / grid_step) * grid_step
    y_start = np.ceil(lat_min / grid_step) * grid_step
    x_ticks = np.arange(x_start, lon_max + grid_step * 0.01, grid_step)
    y_ticks = np.arange(y_start, lat_max + grid_step * 0.01, grid_step)

    axes.set_xticks(x_ticks)
    axes.set_xticklabels([f"{tick:g}°E" for tick in x_ticks], fontsize=8.8, color="#334155")
    axes.set_yticks(y_ticks)
    axes.set_yticklabels([f"{tick:g}°N" for tick in y_ticks], fontsize=8.8, color="#334155")
    axes.grid(
        which="major",
        color="#FFFFFF",
        linestyle="--",
        linewidth=0.75,
        alpha=0.85,
        zorder=3,
    )
    axes.tick_params(length=3.5, width=0.65, pad=2.5, colors="#334155")
    for spine in axes.spines.values():
        spine.set_linewidth(0.85)
        spine.set_color("#64748B")

    filled = axes.contourf(
        grid.longitudes,
        grid.latitudes,
        values,
        levels=style.levels,
        cmap=style.cmap,
        norm=style.norm,
        extend=style.extend,
        antialiased=True,
        zorder=1,
    )

    valid = values.compressed()
    line_levels = [
        level
        for level in style.contour_levels
        if float(valid.min()) < level < float(valid.max())
    ]
    if line_levels:
        contour_lines = axes.contour(
            grid.longitudes,
            grid.latitudes,
            values,
            levels=line_levels,
            colors="#0F172A",
            linewidths=0.65,
            alpha=0.45,
            zorder=2,
        )
        axes.clabel(
            contour_lines,
            inline=True,
            fontsize=7.5,
            fmt="%.1f",
            colors="#0F172A",
        )

    draw_boundaries_and_labels(
        axes,
        boundary_features,
        boundary_segments,
        lon_min,
        lon_max,
        lat_min,
        lat_max,
    )

    # 紧凑色标与底部小字间距
    cbar_ax = figure.add_axes([0.14, 0.105, 0.75, 0.022])
    colorbar = figure.colorbar(
        filled,
        cax=cbar_ax,
        orientation="horizontal",
        ticks=style.ticks,
    )
    colorbar.ax.tick_params(labelsize=8.2, length=3, width=0.6, pad=2, colors="#334155")
    colorbar.outline.set_linewidth(0.7)
    colorbar.outline.set_edgecolor("#94A3B8")
    colorbar.ax.xaxis.set_label_position("bottom")
    colorbar.set_label(
        f"{chinese_name} ({english_name}) [{unit}]",
        fontsize=9.8,
        fontweight="bold",
        color="#0F172A",
        labelpad=4,
    )
    if style.tick_labels:
        colorbar.ax.set_xticklabels(style.tick_labels)

    lead_hours = int((forecast_dt - issue_time).total_seconds() // 3600)
    lead_str = f"+{lead_hours}小时" if lead_hours >= 0 else f"{lead_hours}小时"

    footer_text = (
        f"起报时间：{issue_time:%Y年%m月%d日 %H时}（北京时间）"
        f"  ·  预报时间：{forecast_dt:%Y年%m月%d日 %H时}"
        f"  ·  时间间隔：{lead_str}"
        f"  ·  气象要素：{chinese_name} ({variable})"
        f"  ·  数据源：ECMWF / 海天气象 https://htqx.cn/"
    )
    figure.text(
        0.5,
        0.018,
        footer_text,
        ha="center",
        fontsize=8.5,
        color="#475569",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=260, facecolor=figure.get_facecolor())
    plt.close(figure)
    return output_path


def main() -> None:
    issue_time = get_issue_time_bjt()
    forecast_dt = validate_inputs(
        api_key=API_KEY,
        forecast_time=FORECAST_TIME,
        variable=VARIABLE,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        issue_time=issue_time,
    )

    full_grid = fetch_grid(FORECAST_TIME, VARIABLE, API_KEY)
    region_grid = subset_grid_to_box(
        full_grid,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
    )
    boundary_features = load_boundary_features()

    file_name = (
        f"china_region_{VARIABLE}_{FORECAST_TIME}_"
        f"{LON_MIN:g}_{LON_MAX:g}_{LAT_MIN:g}_{LAT_MAX:g}.png"
    )
    output_path = OUTPUT_DIR / file_name
    saved_path = plot_regional_grid(
        variable=VARIABLE,
        grid=region_grid,
        boundary_features=boundary_features,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        issue_time=issue_time,
        forecast_dt=forecast_dt,
        output_path=output_path,
    )
    print(f"已生成区域等值线图: {saved_path}")


if __name__ == "__main__":
    main()