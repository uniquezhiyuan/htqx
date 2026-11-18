# =============================================================================
# 全国 0.1° 网格预报绘图脚本
#
# 功能说明
#   1. 调用海天气象网格预报 API，获取当前支持的 21 个气象变量。
#   2. 校验返回的经纬度和二维网格数据，并屏蔽 -9999 缺测值。
#   3. 绘制中国区域多变量填色等值图，叠加省界、海岸线、省名、省会、
#      经纬网和等值线；为每个变量标注中英文名称、单位及色标。
#   4. 输出高分辨率 PNG。若本地没有省界缓存，会下载并缓存到
#      data/china_provinces.geojson。
#
# 变量范围
#   气温/露点/体感温度、海平面/地面气压、相对湿度、10 米和 100 米
#   风速及风向、阵风、降水、降雪、云量、能见度、WMO 天气代码，以及
#   短波、直接、散射、直接法向和地球长波辐射。
#
# 时间与参数
#   --time   必填，API 预报时次，格式 YYYYMMDDHH，须在未来 10 日内。
#   --output 可选，图片输出路径；默认写入
#            figures/china_weather_all_<time>.png。
#   图片中的起报时间自动设为运行日的前一日 20:00（北京时间）；预报时间
#   显示 --time 对应的 API 参数时次。
#
# 运行方法（在项目根目录的 PowerShell 中执行）
#   python -m venv .venv
#   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
#   $env:HTMETEO_API_KEY = "<你的 API Key>"
#   .\.venv\Scripts\python.exe src\grid_forecast.py --time 2026111918
#   .\.venv\Scripts\python.exe src\grid_forecast.py --time 2026111918 --output figures\china_weather_all_2026111918.png
#
# 将示例时次替换为未来 10 日内需要查询的 YYYYMMDDHH；API Key 通过环境变量
# 提供，不要直接写入或提交到源代码。
# =============================================================================
"""Fetch and visualize all HtMeteo national 0.1-degree forecast variables."""

import argparse
import concurrent.futures
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.collections import LineCollection
from matplotlib.colors import (
    BoundaryNorm,
    ListedColormap,
)
from matplotlib import patheffects


API_URL = "https://htqx.cn/meteo/api/forecast/grid"
BOUNDARY_URL = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = PROJECT_ROOT / "data" / "china_provinces.geojson"

VARIABLES = {
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

PROVINCE_CAPITALS = {
    110000: ("北京", "北京", 116.4074, 39.9042),
    120000: ("天津", "天津", 117.2000, 39.0842),
    130000: ("河北", "石家庄", 114.5149, 38.0428),
    140000: ("山西", "太原", 112.5489, 37.8706),
    150000: ("内蒙古", "呼和浩特", 111.7490, 40.8426),
    210000: ("辽宁", "沈阳", 123.4315, 41.8057),
    220000: ("吉林", "长春", 125.3235, 43.8171),
    230000: ("黑龙江", "哈尔滨", 126.5350, 45.8038),
    310000: ("上海", "上海", 121.4737, 31.2304),
    320000: ("江苏", "南京", 118.7969, 32.0603),
    330000: ("浙江", "杭州", 120.1551, 30.2741),
    340000: ("安徽", "合肥", 117.2272, 31.8206),
    350000: ("福建", "福州", 119.2965, 26.0745),
    360000: ("江西", "南昌", 115.8582, 28.6829),
    370000: ("山东", "济南", 117.1201, 36.6512),
    410000: ("河南", "郑州", 113.6254, 34.7466),
    420000: ("湖北", "武汉", 114.3054, 30.5931),
    430000: ("湖南", "长沙", 112.9388, 28.2282),
    440000: ("广东", "广州", 113.2644, 23.1291),
    450000: ("广西", "南宁", 108.3669, 22.8170),
    460000: ("海南", "海口", 110.1999, 20.0440),
    500000: ("重庆", "重庆", 106.5516, 29.5630),
    510000: ("四川", "成都", 104.0665, 30.5723),
    520000: ("贵州", "贵阳", 106.6302, 26.6470),
    530000: ("云南", "昆明", 102.8329, 24.8801),
    540000: ("西藏", "拉萨", 91.1322, 29.6604),
    610000: ("陕西", "西安", 108.9398, 34.3416),
    620000: ("甘肃", "兰州", 103.8343, 36.0611),
    630000: ("青海", "西宁", 101.7782, 36.6171),
    640000: ("宁夏", "银川", 106.2309, 38.4872),
    650000: ("新疆", "乌鲁木齐", 87.6168, 43.8256),
    710000: ("台湾", "台北", 121.5654, 25.0330),
    810000: ("香港", "香港", 114.1694, 22.3193),
    820000: ("澳门", "澳门", 113.5439, 22.1987),
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


def fetch_grid(time: str, meteo_type: str, api_key: str) -> GridForecast:
    """Fetch and validate one forecast grid without exposing the API key."""
    url = f"{API_URL}/{time}/{meteo_type}/{api_key}"
    try:
        response = requests.get(url, timeout=(10, 90))
    except requests.RequestException as exc:
        raise RuntimeError(f"{meteo_type}: request failed ({type(exc).__name__}).") from None

    if response.status_code != 200:
        raise RuntimeError(f"{meteo_type}: API returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"{meteo_type}: API response was not valid JSON.") from None

    if not isinstance(payload, dict):
        raise RuntimeError(f"{meteo_type}: API response must be a JSON object.")

    required_keys = {"metadata", "lats", "lons", "data"}
    missing_keys = required_keys.difference(payload)
    if missing_keys:
        raise RuntimeError(
            f"{meteo_type}: API response is missing fields "
            + ", ".join(sorted(missing_keys))
        )
    metadata = payload["metadata"]
    if not isinstance(metadata, dict):
        raise RuntimeError(f"{meteo_type}: metadata must be a JSON object.")

    try:
        latitudes = np.asarray(payload["lats"], dtype=np.float32)
        longitudes = np.asarray(payload["lons"], dtype=np.float32)
        values = np.asarray(payload["data"], dtype=np.float32)
    except (TypeError, ValueError):
        raise RuntimeError(f"{meteo_type}: coordinates and data must be numeric.") from None

    if latitudes.ndim != 1 or longitudes.ndim != 1 or values.ndim != 2:
        raise RuntimeError(f"{meteo_type}: unexpected coordinate or data dimensions.")
    if values.shape != (latitudes.size, longitudes.size):
        raise RuntimeError(f"{meteo_type}: data shape does not match its coordinates.")
    declared_shape = metadata.get("shape")
    if declared_shape is not None and tuple(declared_shape) != values.shape:
        raise RuntimeError(f"{meteo_type}: data shape differs from API metadata.")

    metadata["nodata_value"] = metadata.get("nodata_value", -9999)
    return GridForecast(
        latitudes=latitudes,
        longitudes=longitudes,
        values=values,
        metadata=metadata,
    )


def fetch_all_grids(
    time: str, api_key: str
) -> tuple[np.ndarray, np.ndarray, dict[str, GridForecast], dict[str, str]]:
    """Fetch all requested variables, limiting concurrent API requests."""
    grids: dict[str, GridForecast] = {}
    errors: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_grid, time, variable, api_key): variable
            for variable in VARIABLES
        }
        for completed, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            variable = futures[future]
            try:
                grids[variable] = future.result()
            except RuntimeError as exc:
                errors[variable] = str(exc)
            else:
                print(f"Fetched {completed}/{len(VARIABLES)}: {variable}")

    if not grids:
        raise RuntimeError("All grid requests failed:\n" + "\n".join(errors.values()))

    reference_grid = next(iter(grids.values()))
    reference_latitudes = reference_grid.latitudes
    reference_longitudes = reference_grid.longitudes
    if reference_latitudes.size == 0 or reference_longitudes.size == 0:
        raise RuntimeError("Grid API returned empty coordinates.")
    for variable, grid in grids.items():
        if not np.array_equal(grid.latitudes, reference_latitudes) or not np.array_equal(
            grid.longitudes, reference_longitudes
        ):
            raise RuntimeError(f"{variable}: grid coordinates differ from other variables.")
    return reference_latitudes, reference_longitudes, grids, errors


def load_boundary_features() -> list[dict[str, Any]]:
    """Load cached province geometry or download it from the public map dataset."""
    if BOUNDARY_PATH.exists():
        try:
            with BOUNDARY_PATH.open(encoding="utf-8") as boundary_file:
                payload = json.load(boundary_file)
        except (OSError, json.JSONDecodeError):
            raise RuntimeError(f"Unable to read boundary data: {BOUNDARY_PATH}") from None
    else:
        try:
            response = requests.get(BOUNDARY_URL, timeout=30)
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Province boundary download failed ({type(exc).__name__})."
            ) from None
        if response.status_code != 200:
            raise RuntimeError(
                f"Province boundary source returned HTTP {response.status_code}."
            )
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError("Province boundary source returned invalid JSON.") from None
        BOUNDARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        BOUNDARY_PATH.write_bytes(response.content)

    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list) or not features:
        raise RuntimeError("Province boundary data contains no map features.")
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


def variable_style(
    variable: str, values: np.ma.MaskedArray
) -> PlotStyle:
    category = VARIABLES[variable][3]
    valid = values.compressed()
    if valid.size == 0:
        raise RuntimeError(f"{variable}: grid contains no valid values.")

    if category == "weather_code":
        levels = np.asarray(WEATHER_CODE_BOUNDS, dtype=float)
        cmap = ListedColormap(plt.get_cmap("viridis", len(levels) - 1).colors)
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
        cmap = plt.get_cmap("twilight_shifted", len(levels) - 1)
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
            limit = 1
        levels = np.linspace(-limit, limit, 13)
        cmap = plt.get_cmap("coolwarm", len(levels) + 1)
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
        cmap = plt.get_cmap("viridis", len(levels))
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
        cmap = plt.get_cmap("viridis", len(levels) - 1)
        return PlotStyle(
            levels,
            cmap,
            BoundaryNorm(levels, cmap.N, clip=True),
            [0, 20, 40, 60, 80, 100],
            None,
            "neither",
            [20, 40, 60, 80],
        )

    vmin = float(np.percentile(valid, 1))
    vmax = float(np.percentile(valid, 99))
    if vmax <= vmin:
        vmax = vmin + 1
    levels = np.linspace(vmin, vmax, 11)
    cmap = plt.get_cmap("viridis", len(levels) + 1)
    return PlotStyle(
        levels,
        cmap,
        BoundaryNorm(levels, cmap.N, extend="both"),
        [float(level) for level in levels[::2]],
        None,
        "both",
        [float(level) for level in levels[1:-1:2]],
    )


def draw_boundaries(
    axes: Any,
    features: list[dict[str, Any]],
    segments: list[np.ndarray],
) -> None:
    axes.add_collection(
        LineCollection(
            segments,
            colors="#37474f",
            linewidths=0.28,
            alpha=0.88,
            zorder=4,
        )
    )
    text_effect = [patheffects.withStroke(linewidth=0.55, foreground="white", alpha=0.9)]

    for feature in features:
        properties = feature.get("properties") or {}
        try:
            adcode = int(properties.get("adcode"))
        except (TypeError, ValueError):
            continue
        province_capital = PROVINCE_CAPITALS.get(adcode)
        if province_capital is None:
            continue

        province, capital, capital_lon, capital_lat = province_capital
        centroid = feature_centroid(feature)
        if centroid is not None:
            axes.text(
                centroid[0],
                centroid[1],
                province,
                fontsize=2.8,
                color="#263238",
                ha="center",
                va="center",
                zorder=5,
                path_effects=text_effect,
            )
        axes.plot(
            capital_lon,
            capital_lat,
            marker="o",
            markersize=1.5,
            color="#1b2631",
            markeredgecolor="white",
            markeredgewidth=0.35,
            zorder=6,
        )
        if capital != province:
            axes.annotate(
                capital,
                (capital_lon, capital_lat),
                xytext=(2, 2),
                textcoords="offset points",
                fontsize=2.6,
                color="#17202a",
                ha="left",
                va="bottom",
                zorder=6,
                path_effects=text_effect,
            )


def plot_all_grids(
    time: str,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    grids: dict[str, GridForecast],
    errors: dict[str, str],
    boundary_features: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    boundary_segments = []
    for feature in boundary_features:
        geometry = feature.get("geometry") or {}
        boundary_segments.extend(geometry_rings(geometry))
    if not boundary_segments:
        raise RuntimeError("Province boundary data contains no drawable outlines.")

    columns = 4
    rows = (len(VARIABLES) + columns - 1) // columns
    figure = plt.figure(figsize=(26, rows * 4.5), facecolor="white")
    figure.suptitle(
        "中国未来10日全要素逐小时气象预报",
        fontsize=22,
        fontweight="bold",
        y=0.982,
    )
    start_time = (datetime.now(timezone(timedelta(hours=8))) - timedelta(days=1)).replace(
        hour=20,
        minute=0,
        second=0,
        microsecond=0,
    )
    forecast_time = datetime.strptime(time, "%Y%m%d%H").strftime(
        "预报时间：%Y年%m月%d日 %H时（API时间参数）"
    )
    title_details = (
        f"起报时间：{start_time:%Y年%m月%d日 %H时}（北京时间）"
        f"  ·  {forecast_time}"
        f"  ·  气象变量数量：{len(VARIABLES)}"
    )
    figure.text(
        0.5,
        0.963,
        title_details,
        ha="center",
        fontsize=11,
        color="#455a64",
    )
    grid_spec = figure.add_gridspec(
        rows,
        columns,
        left=0.035,
        right=0.985,
        top=0.95,
        bottom=0.045,
        hspace=0.2,
        wspace=0.1,
    )

    for index, variable in enumerate(VARIABLES):
        row, column = divmod(index, columns)
        axes = figure.add_subplot(grid_spec[row, column])
        axes.set_xlim(float(longitudes.min()), float(longitudes.max()))
        axes.set_ylim(float(latitudes.min()), float(latitudes.max()))
        axes.set_aspect(0.82)
        x_ticks = np.arange(75, 136, 15)
        y_ticks = np.arange(15, 56, 10)
        axes.set_xticks(x_ticks)
        axes.set_xticklabels([f"{tick}°E" for tick in x_ticks], fontsize=4.5)
        axes.set_yticks(y_ticks)
        axes.set_yticklabels([f"{tick}°N" for tick in y_ticks], fontsize=4.5)
        axes.grid(color="white", linestyle="--", linewidth=0.35, alpha=0.48, zorder=3)
        axes.tick_params(length=1.8, width=0.4, pad=1.5)
        for spine in axes.spines.values():
            spine.set_linewidth(0.45)
            spine.set_color("#546e7a")

        chinese_name, english_name, default_unit, _ = VARIABLES[variable]
        grid = grids.get(variable)
        unit = variable_unit(variable, grid) if grid else default_unit
        axes.set_title(
            f"{chinese_name} · {unit}\n{english_name}",
            fontsize=7,
            pad=3,
            color="#263238",
        )
        if grid is None:
            draw_boundaries(axes, boundary_features, boundary_segments)
            axes.text(
                0.5,
                0.5,
                "数据暂不可用\n" + errors.get(variable, "未收到该变量的数据"),
                transform=axes.transAxes,
                ha="center",
                va="center",
                fontsize=6,
                color="#9b2c2c",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82},
                zorder=7,
            )
            continue

        values = masked_values(grid)
        style = variable_style(variable, values)
        filled = axes.contourf(
            longitudes,
            latitudes,
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
            axes.contour(
                longitudes,
                latitudes,
                values,
                levels=line_levels,
                colors="#243447",
                linewidths=0.28,
                alpha=0.36,
                zorder=2,
            )
        draw_boundaries(axes, boundary_features, boundary_segments)
        colorbar = figure.colorbar(
            filled,
            ax=axes,
            orientation="horizontal",
            pad=0.032,
            fraction=0.04,
            aspect=32,
            ticks=style.ticks,
        )
        colorbar.ax.tick_params(labelsize=4, length=1.5, width=0.35, pad=1)
        colorbar.outline.set_linewidth(0.4)
        colorbar.ax.xaxis.set_label_position("top")
        colorbar.set_label(
            f"[{unit}]",
            fontsize=5,
            labelpad=1,
        )
        if style.tick_labels:
            colorbar.ax.set_xticklabels(style.tick_labels)

    figure.text(
        0.5,
        0.018,
        "数据源：ECMWF 由海天气象提供API支持：https://htqx.cn/",
        ha="center",
        fontsize=8,
        color="#455a64",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=250, facecolor="white")
    plt.close(figure)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch all national 0.1-degree forecast variables and create a map panel."
    )
    parser.add_argument(
        "--time",
        required=True,
        help="Forecast valid time in YYYYMMDDHH format, within the next 10 days.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Image output path (default: figures/china_weather_all_<time>.png).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.time) != 10 or not args.time.isdigit():
        raise SystemExit("--time must contain exactly 10 digits in YYYYMMDDHH format.")
    try:
        datetime.strptime(args.time, "%Y%m%d%H")
    except ValueError:
        raise SystemExit("--time must be a valid date and hour in YYYYMMDDHH format.")

    api_key = os.environ.get("HTMETEO_API_KEY")
    if not api_key:
        raise SystemExit("Set the HTMETEO_API_KEY environment variable before running.")

    latitudes, longitudes, grids, errors = fetch_all_grids(args.time, api_key)
    boundary_features = load_boundary_features()
    output_path = args.output or (
        PROJECT_ROOT / "figures" / f"china_weather_all_{args.time}.png"
    )
    saved_path = plot_all_grids(
        args.time,
        latitudes,
        longitudes,
        grids,
        errors,
        boundary_features,
        output_path,
    )
    print(f"Saved all {len(grids)} variable maps to: {saved_path}")


if __name__ == "__main__":
    main()
