r"""海天气象某地点某年逐小时历史气象数据统计分析与可视化。
    源数据下载地址：https://htqx.cn/

数据源与数据说明
    * 通过海天气象历史天气 API 获取 ERA5 地点逐小时历史数据：
      https://htqx.cn/meteo/api/history/yearly/{城市}/{年份}/{API密钥}
    * API 年度接口通常返回 8760 个逐小时记录；闰年为 8784 个时次。
      脚本按 API 返回的时间字段原样统计，不对时间做时区转换。
    * 分析温度、湿度、露点、体感温度、降水、天气现象、气压、云量、
      风、辐射、土壤、边界层及整层水汽等 API 返回的气象变量。
    * 年度及月度统计包含最大值、最小值、平均值、中位数、标准差、
      有效/缺失时次数；降水、雨雪和蒸散统计累积量。
    * 风向平均值使用圆周平均，避免 0°/360°边界造成错误，并转换为
      16 方位；辐射平均值使用 W/m²，逐小时积分的年度能量另以 kWh/m²
      报告。日尺度辐射字段为日平均通量，日积分能量另列于日统计 CSV。
    * 图表包括年统计摘要、月变化、风玫瑰、月小时热力图、逐日降水和
      辐射日历、逐日温度范围、天气频率及气象要素相关性。

运行方法（在项目根目录的 PowerShell 中执行）
    先在当前终端设置 API Key，再运行脚本：
        $env:HTMETEO_API_KEY = "你的海天气象API密钥"
        .\.venv\Scripts\python.exe src\histor_single_year.py
    API Key 通过环境变量读取，不要将密钥写入源代码或提交到版本库。

可修改参数（位于下方“用户设置”区域）
    API_KEY：从 HTMETEO_API_KEY 环境变量读取的 API 凭据。
    CITY_NAME：接口支持的城市/区县名称，默认上海市。
    YEAR：要查询的年份，范围为 2000 年至当前年份；历史数据可能有延迟。
    PROJECT_ROOT：项目根目录，默认由本脚本所在路径自动确定。
    API_URL：历史年度数据 API 地址。

输出结果
    figures/{城市}_{年份}_全年逐小时历史气象分析.png
        高分辨率综合分析图。
    data/{城市}_{年份}_全年统计.csv
        所有变量的全年统计摘要。
    data/{城市}_{年份}_月统计.csv
        每个变量按月统计的最大、最小、平均、累计等结果。
    data/{城市}_{年份}_日统计.csv
        每日变量统计、每日温度极值及天气现象。
    data/{城市}_{年份}_相关性矩阵.csv
        关键变量逐小时 Pearson 相关系数矩阵。
    CSV 使用 UTF-8 BOM 编码，便于常见表格软件识别中文。
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.colors import PowerNorm


# =============================================================================
# User settings
# =============================================================================
# API_KEY = os.getenv("HTMETEO_API_KEY", "").strip()
API_KEY = "2js7rY7j89JgbNH76Ggh7TF5r6"  # 请在海天气象个人中心查看26位 API Key：https://htqx.cn/
CITY_NAME = "番禺区"
YEAR = 2004

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://htqx.cn/meteo/api/history/yearly"

# Variable name: (Chinese label, unit)
VARIABLES = {
    "temperature_2m": ("2米气温", "℃"),
    "relative_humidity_2m": ("2米相对湿度", "%"),
    "dew_point_2m": ("2米露点温度", "℃"),
    "apparent_temperature": ("体感温度", "℃"),
    "precipitation": ("降水量", "mm"),
    "rain": ("雨量", "mm"),
    "snowfall": ("降雪量", "cm"),
    "snow_depth": ("积雪深度", "m"),
    "weather_code": ("天气现象代码", "WMO代码"),
    "pressure_msl": ("海平面气压", "hPa"),
    "surface_pressure": ("地面气压", "hPa"),
    "cloud_cover": ("总云量", "%"),
    "cloud_cover_low": ("低云量", "%"),
    "cloud_cover_mid": ("中云量", "%"),
    "cloud_cover_high": ("高云量", "%"),
    "et0_fao_evapotranspiration": ("参考蒸散量", "mm"),
    "vapour_pressure_deficit": ("水汽压亏缺", "kPa"),
    "wind_speed_10m": ("10米风速", "m/s"),
    "wind_speed_100m": ("100米风速", "m/s"),
    "wind_direction_10m": ("10米风向", "°"),
    "wind_direction_100m": ("100米风向", "°"),
    "wind_gusts_10m": ("10米阵风", "m/s"),
    "soil_temperature_0_to_7cm": ("0–7厘米土壤温度", "℃"),
    "soil_moisture_0_to_7cm": ("0–7厘米土壤湿度", "m³/m³"),
    "shortwave_radiation": ("短波辐射", "W/m²"),
    "direct_radiation": ("直接辐射", "W/m²"),
    "diffuse_radiation": ("散射辐射", "W/m²"),
    "direct_normal_irradiance": ("法向直接辐照度", "W/m²"),
    "global_tilted_irradiance": ("倾斜面总辐照度", "W/m²"),
    "terrestrial_radiation": ("地球辐射", "W/m²"),
    "soil_temperature_7_to_28cm": ("7–28厘米土壤温度", "℃"),
    "soil_temperature_28_to_100cm": ("28–100厘米土壤温度", "℃"),
    "soil_temperature_100_to_255cm": ("100–255厘米土壤温度", "℃"),
    "soil_moisture_7_to_28cm": ("7–28厘米土壤湿度", "m³/m³"),
    "soil_moisture_28_to_100cm": ("28–100厘米土壤湿度", "m³/m³"),
    "soil_moisture_100_to_255cm": ("100–255厘米土壤湿度", "m³/m³"),
    "boundary_layer_height": ("边界层高度", "m"),
    "wet_bulb_temperature_2m": ("2米湿球温度", "℃"),
    "total_column_integrated_water_vapour": ("整层可降水量", "kg/m²"),
}

ACCUMULATED_VARIABLES = {
    "precipitation",
    "rain",
    "snowfall",
    "et0_fao_evapotranspiration",
}
RADIATION_VARIABLES = {
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "global_tilted_irradiance",
    "terrestrial_radiation",
}
RADIATION_FIELDS = tuple(
    field for field in VARIABLES if field in RADIATION_VARIABLES
)
DIRECTION_VARIABLES = {"wind_direction_10m", "wind_direction_100m"}
COMPASS_16 = (
    "北",
    "北东北",
    "东北",
    "东东北",
    "东",
    "东东南",
    "东南",
    "南东南",
    "南",
    "南西南",
    "西南",
    "西西南",
    "西",
    "西西北",
    "西北",
    "北西北",
)
WEATHER_NAMES = {
    0: "晴",
    1: "大部晴",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "毛毛细雨",
    53: "细雨",
    55: "强细雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "霰",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "强雷暴伴冰雹",
}

COLORS = {
    "ink": "#18344d",
    "muted": "#71869a",
    "blue": "#2787b7",
    "cyan": "#62b6cf",
    "teal": "#3e9a8f",
    "orange": "#e89555",
    "red": "#cf6d62",
    "purple": "#8c78b5",
    "green": "#72a878",
    "grid": "#dce6ed",
    "paper": "#f1f5f8",
    "panel": "#ffffff",
}


def _ordered_values(value: Any, field: str) -> list[Any]:
    if isinstance(value, dict):
        try:
            return [value[key] for key in sorted(value, key=lambda item: int(item))]
        except (TypeError, ValueError):
            raise RuntimeError(
                f"API field '{field}' has non-numeric time indexes."
            ) from None
    if isinstance(value, list):
        return value
    raise RuntimeError(f"API field '{field}' must be an indexed object or list.")


def fetch_yearly_history() -> dict[str, Any]:
    if not API_KEY:
        raise RuntimeError(
            "API key is not configured. Set HTMETEO_API_KEY in the environment."
        )
    if not 2000 <= YEAR <= date.today().year:
        raise RuntimeError(f"YEAR must be between 2000 and {date.today().year}.")

    url = f"{API_URL}/{quote(CITY_NAME, safe='')}/{YEAR}/{API_KEY}"
    try:
        response = requests.get(url, timeout=(10, 180))
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Yearly history request failed ({type(exc).__name__})."
        ) from None

    try:
        payload = response.json()
    except ValueError:
        encoding = response.apparent_encoding or "utf-8"
        body = response.content.decode(encoding, errors="replace").strip()
        raise RuntimeError(
            f"History API returned a non-JSON response "
            f"(HTTP {response.status_code}): {body[:240]}"
        ) from None
    if response.status_code != 200:
        raise RuntimeError(f"History API returned HTTP {response.status_code}.")
    if not isinstance(payload, dict):
        raise RuntimeError("History API response must be a JSON object.")
    if "error" in payload:
        raise RuntimeError(f"History API returned an error: {payload['error']}")
    return payload


def parse_history(payload: dict[str, Any]) -> dict[str, Any]:
    if "date" not in payload:
        raise RuntimeError("History response is missing the 'date' field.")

    raw_dates = _ordered_values(payload["date"], "date")
    if not raw_dates:
        raise RuntimeError("History response contains no hourly records.")
    try:
        times = [
            datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(
                tzinfo=None
            )
            for value in raw_dates
        ]
    except ValueError as exc:
        raise RuntimeError(f"Invalid timestamp in history response: {exc}") from None
    if any(item.year != YEAR for item in times):
        raise RuntimeError(f"History response contains timestamps outside {YEAR}.")
    if times != sorted(times) or len(set(times)) != len(times):
        raise RuntimeError("History timestamps must be unique and in ascending order.")

    series: dict[str, np.ndarray] = {}
    missing: list[str] = []
    for field in VARIABLES:
        if field not in payload:
            series[field] = np.full(len(times), np.nan, dtype=float)
            missing.append(field)
            continue
        raw_values = _ordered_values(payload[field], field)
        if len(raw_values) != len(times):
            raise RuntimeError(
                f"History field '{field}' contains {len(raw_values)} values; "
                f"expected {len(times)}."
            )
        values = []
        for value in raw_values:
            try:
                values.append(float(value) if value is not None else np.nan)
            except (TypeError, ValueError):
                values.append(np.nan)
        series[field] = np.asarray(values, dtype=float)
    if all(not np.isfinite(values).any() for values in series.values()):
        raise RuntimeError("History response contains no usable weather variables.")
    return {"times": times, "series": series, "missing": missing}


def _groups(
    times: list[datetime], key_fn: Callable[[datetime], Any]
) -> dict[Any, np.ndarray]:
    grouped: dict[Any, list[int]] = defaultdict(list)
    for index, timestamp in enumerate(times):
        grouped[key_fn(timestamp)].append(index)
    return {
        key: np.asarray(indexes, dtype=int)
        for key, indexes in sorted(grouped.items())
    }


def _finite(values: np.ndarray) -> np.ndarray:
    return values[np.isfinite(values)]


def _circular_mean(values: np.ndarray) -> float:
    valid = _finite(values)
    if not valid.size:
        return float("nan")
    radians = np.deg2rad(valid)
    sine = np.sin(radians).mean()
    cosine = np.cos(radians).mean()
    if np.isclose(sine, 0) and np.isclose(cosine, 0):
        return float("nan")
    mean = float(np.rad2deg(np.arctan2(sine, cosine)) % 360)
    return 0.0 if np.isclose(mean, 360) else mean


def _mode(values: np.ndarray) -> float:
    valid = _finite(values)
    if not valid.size:
        return float("nan")
    counts = Counter(np.rint(valid).astype(int).tolist())
    return float(min(counts, key=lambda code: (-counts[code], code)))


def _total_value(values: np.ndarray, field: str) -> tuple[float, str]:
    valid = _finite(values)
    if not valid.size:
        return float("nan"), ""
    if field in ACCUMULATED_VARIABLES:
        return float(valid.sum()), VARIABLES[field][1]
    if field in RADIATION_VARIABLES:
        return float(valid.sum() / 1000), "kWh/m²"
    return float("nan"), ""


def _statistics(values: np.ndarray, field: str) -> dict[str, Any]:
    valid = _finite(values)
    result: dict[str, Any] = {
        "count": int(valid.size),
        "missing": int(values.size - valid.size),
        "min": float("nan"),
        "max": float("nan"),
        "mean": float("nan"),
        "median": float("nan"),
        "std": float("nan"),
        "total": float("nan"),
        "total_unit": "",
        "mode": float("nan"),
    }
    if not valid.size:
        return result
    if field == "weather_code":
        result["min"] = float(np.min(valid))
        result["max"] = float(np.max(valid))
        result["mode"] = _mode(valid)
    elif field in DIRECTION_VARIABLES:
        result["mean"] = _circular_mean(valid)
    else:
        result.update(
            min=float(np.min(valid)),
            max=float(np.max(valid)),
            mean=float(np.mean(valid)),
            median=float(np.median(valid)),
            std=float(np.std(valid)),
        )
    result["total"], result["total_unit"] = _total_value(valid, field)
    return result


def annual_statistics(series: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    rows = []
    for field, (label, unit) in VARIABLES.items():
        stats = _statistics(series[field], field)
        rows.append(
            {
                "variable_key": field,
                "variable": label,
                "unit": unit,
                **stats,
            }
        )
    return rows


def monthly_statistics(
    times: list[datetime], series: dict[str, np.ndarray]
) -> list[dict[str, Any]]:
    rows = []
    for (year, month), indexes in _groups(times, lambda item: (item.year, item.month)).items():
        for field, (label, unit) in VARIABLES.items():
            rows.append(
                {
                    "year": year,
                    "month": month,
                    "variable_key": field,
                    "variable": label,
                    "unit": unit,
                    **_statistics(series[field][indexes], field),
                }
            )
    return rows


def daily_summaries(
    times: list[datetime], series: dict[str, np.ndarray]
) -> list[dict[str, Any]]:
    rows = []
    for day, indexes in _groups(times, lambda item: item.date()).items():
        row: dict[str, Any] = {"date": day.isoformat()}
        for field in VARIABLES:
            values = series[field][indexes]
            valid = _finite(values)
            if field == "weather_code":
                value = _mode(values)
                row[field] = value
                row["weather_name"] = (
                    WEATHER_NAMES.get(int(value), "其他天气")
                    if np.isfinite(value)
                    else ""
                )
            elif field in DIRECTION_VARIABLES:
                row[field] = _circular_mean(values)
            elif field in ACCUMULATED_VARIABLES:
                row[field] = float(valid.sum()) if valid.size else float("nan")
            elif field in RADIATION_VARIABLES:
                row[field] = float(valid.mean()) if valid.size else float("nan")
                row[f"{field}_energy_kwh_m2"] = (
                    float(valid.sum() / 1000) if valid.size else float("nan")
                )
            elif field == "wind_gusts_10m":
                row[field] = float(np.max(valid)) if valid.size else float("nan")
            else:
                row[field] = float(np.mean(valid)) if valid.size else float("nan")

        temperatures = _finite(series["temperature_2m"][indexes])
        row["temperature_min"] = (
            float(np.min(temperatures)) if temperatures.size else float("nan")
        )
        row["temperature_max"] = (
            float(np.max(temperatures)) if temperatures.size else float("nan")
        )
        rows.append(row)
    return rows


CORRELATION_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "dew_point_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "cloud_cover",
    "shortwave_radiation",
    "pressure_msl",
    "vapour_pressure_deficit",
    "boundary_layer_height",
    "total_column_integrated_water_vapour",
]


def correlation_matrix(series: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    fields = [field for field in CORRELATION_FIELDS if field in series]
    matrix = np.full((len(fields), len(fields)), np.nan, dtype=float)
    for row, left in enumerate(fields):
        for column, right in enumerate(fields):
            valid = np.isfinite(series[left]) & np.isfinite(series[right])
            if valid.sum() < 3:
                continue
            x = series[left][valid]
            y = series[right][valid]
            if np.std(x) == 0 or np.std(y) == 0:
                continue
            matrix[row, column] = float(np.corrcoef(x, y)[0, 1])
    return fields, matrix


def _safe_city_name(city: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", city).strip(" ._") or "地点"


def _csv_value(value: Any) -> Any:
    if isinstance(value, (float, np.floating)):
        return round(float(value), 6) if np.isfinite(value) else ""
    if isinstance(value, (int, np.integer)):
        return int(value)
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def export_statistics(
    annual: list[dict[str, Any]],
    monthly: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    corr_fields: list[str],
    corr_values: np.ndarray,
) -> dict[str, Path]:
    prefix = f"{_safe_city_name(CITY_NAME)}_{YEAR}"
    annual_path = PROJECT_ROOT / "data" / f"{prefix}_全年统计.csv"
    monthly_path = PROJECT_ROOT / "data" / f"{prefix}_月统计.csv"
    daily_path = PROJECT_ROOT / "data" / f"{prefix}_日统计.csv"
    corr_path = PROJECT_ROOT / "data" / f"{prefix}_相关性矩阵.csv"
    stat_columns = [
        "count",
        "missing",
        "min",
        "max",
        "mean",
        "median",
        "std",
        "total",
        "total_unit",
        "mode",
    ]
    annual_columns = ["variable_key", "variable", "unit", *stat_columns]
    monthly_columns = [
        "year",
        "month",
        "variable_key",
        "variable",
        "unit",
        *stat_columns,
    ]
    daily_columns = [
        "date",
        *VARIABLES.keys(),
        *(f"{field}_energy_kwh_m2" for field in RADIATION_FIELDS),
        "weather_name",
        "temperature_min",
        "temperature_max",
    ]
    _write_csv(annual_path, annual, annual_columns)
    _write_csv(monthly_path, monthly, monthly_columns)
    _write_csv(daily_path, daily, daily_columns)

    correlation_rows = []
    for index, field in enumerate(corr_fields):
        correlation_rows.append(
            {
                "variable_key": field,
                "variable": VARIABLES[field][0],
                **{
                    other: corr_values[index, column]
                    for column, other in enumerate(corr_fields)
                },
            }
        )
    _write_csv(
        corr_path,
        correlation_rows,
        ["variable_key", "variable", *corr_fields],
    )
    return {
        "annual": annual_path,
        "monthly": monthly_path,
        "daily": daily_path,
        "correlation": corr_path,
    }


def _monthly_values(
    times: list[datetime],
    values: np.ndarray,
    reducer: str = "mean",
) -> np.ndarray:
    result = np.full(12, np.nan, dtype=float)
    groups = _groups(times, lambda item: item.month)
    for month, indexes in groups.items():
        valid = _finite(values[indexes])
        if not valid.size:
            continue
        if reducer == "sum":
            result[month - 1] = valid.sum()
        elif reducer == "max":
            result[month - 1] = valid.max()
        elif reducer == "min":
            result[month - 1] = valid.min()
        else:
            result[month - 1] = valid.mean()
    return result


def _panel(ax: Any, title: str) -> None:
    ax.set_facecolor(COLORS["panel"])
    ax.set_title(title, loc="left", fontsize=11, color=COLORS["ink"], pad=9, weight="bold")
    ax.tick_params(labelsize=8, colors=COLORS["muted"], length=2)
    ax.grid(color=COLORS["grid"], linewidth=0.55, alpha=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])
        spine.set_linewidth(0.7)


def _monthly_axis(ax: Any) -> None:
    ax.set_xticks(np.arange(1, 13))
    ax.set_xticklabels([f"{month}月" for month in range(1, 13)])


def _draw_wind_rose(ax: Any, series: dict[str, np.ndarray]) -> None:
    direction = series["wind_direction_10m"]
    speed = series["wind_speed_10m"]
    valid = np.isfinite(direction) & np.isfinite(speed)
    direction = direction[valid] % 360
    speed = speed[valid]
    if not direction.size:
        ax.text(0.5, 0.5, "无有效风向数据", ha="center", va="center", transform=ax.transAxes)
        return

    sectors = 16
    edges = np.linspace(0, 360, sectors + 1)
    centers = np.deg2rad((edges[:-1] + edges[1:]) / 2)
    width = 2 * np.pi / sectors * 0.88
    speed_bins = [(0, 2), (2, 5), (5, 8), (8, 11), (11, np.inf)]
    colors = ["#d9eef4", "#91cbd9", "#55a8bd", "#337f9f", "#214d73"]
    bottom = np.zeros(sectors, dtype=float)
    for (lower, upper), color in zip(speed_bins, colors):
        mask = (speed >= lower) & (speed < upper)
        counts, _ = np.histogram(direction[mask], bins=edges)
        percent = counts / direction.size * 100
        ax.bar(
            centers,
            percent,
            width=width,
            bottom=bottom,
            color=color,
            edgecolor="white",
            linewidth=0.35,
            label=f"{lower}–{upper if np.isfinite(upper) else '+'} m/s",
        )
        bottom += percent
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.arange(0, 360, 45), labels=["北", "东北", "东", "东南", "南", "西南", "西", "西北"])
    ax.tick_params(labelsize=7, colors=COLORS["muted"])
    ax.grid(color=COLORS["grid"], linewidth=0.55)
    ax.set_title(
        "全年风向风速频率分布",
        loc="left",
        fontsize=11,
        color=COLORS["ink"],
        pad=12,
        weight="bold",
    )
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=6.5, frameon=False)


def _draw_diurnal_heatmap(
    ax: Any,
    times: list[datetime],
    values: np.ndarray,
    title: str,
    cmap: str,
    unit: str,
    power: bool = False,
) -> None:
    matrix = np.full((12, 24), np.nan, dtype=float)
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for timestamp, value in zip(times, values):
        if np.isfinite(value):
            buckets[(timestamp.month - 1, timestamp.hour)].append(float(value))
    for (month, hour), bucket in buckets.items():
        matrix[month, hour] = float(np.mean(bucket))
    if not np.isfinite(matrix).any():
        _panel(ax, title)
        ax.text(0.5, 0.5, "无有效数据", ha="center", va="center", transform=ax.transAxes)
        return

    valid = matrix[np.isfinite(matrix)]
    vmin = float(np.min(valid))
    vmax = float(np.percentile(valid, 98)) if power else float(np.max(valid))
    if np.isclose(vmin, vmax):
        vmax = vmin + 1
    norm = PowerNorm(gamma=0.55, vmin=max(0, vmin), vmax=max(vmax, 1e-6)) if power else None
    mesh = ax.pcolormesh(
        np.arange(25),
        np.arange(13),
        matrix,
        cmap=cmap,
        norm=norm,
        vmin=None if norm else vmin,
        vmax=None if norm else vmax,
        shading="flat",
        edgecolors="#ffffff",
        linewidth=0.2,
    )
    ax.set_title(title, loc="left", fontsize=11, color=COLORS["ink"], pad=9, weight="bold")
    ax.set_xlim(0, 24)
    ax.set_ylim(12, 0)
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xticklabels(["00时", "06时", "12时", "18时", "24时"])
    ax.set_yticks(np.arange(0.5, 12.5, 1))
    ax.set_yticklabels([f"{month}月" for month in range(1, 13)])
    ax.tick_params(labelsize=7, colors=COLORS["muted"], length=0)
    ax.grid(False)
    colorbar = ax.figure.colorbar(mesh, ax=ax, pad=0.02, fraction=0.035)
    colorbar.set_label(unit, fontsize=7, color=COLORS["muted"])
    colorbar.ax.tick_params(labelsize=6, colors=COLORS["muted"])
    colorbar.outline.set_visible(False)


def _draw_calendar(
    ax: Any,
    daily: list[dict[str, Any]],
    field: str,
    title: str,
    cmap: str,
    unit: str,
) -> None:
    calendar = np.full((7, 53), np.nan, dtype=float)
    year_start = date(YEAR, 1, 1)
    for row in daily:
        day = date.fromisoformat(row["date"])
        column = ((day - year_start).days + year_start.weekday()) // 7
        value = row.get(field, float("nan"))
        if column < 53 and np.isfinite(value):
            calendar[day.weekday(), column] = value
    _panel(ax, title)
    valid = calendar[np.isfinite(calendar)]
    if not valid.size:
        ax.text(0.5, 0.5, "无有效数据", ha="center", va="center", transform=ax.transAxes)
        return

    vmax = float(np.percentile(valid, 98))
    if np.isclose(vmax, 0):
        vmax = 1.0
    mesh = ax.pcolormesh(
        np.arange(54),
        np.arange(8),
        calendar,
        cmap=cmap,
        norm=PowerNorm(gamma=0.55, vmin=0, vmax=vmax),
        shading="flat",
        edgecolors="white",
        linewidth=0.55,
    )
    ax.set_xlim(0, 53)
    ax.set_ylim(7, 0)
    ax.set_yticks(np.arange(0.5, 7.5, 1))
    ax.set_yticklabels(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
    month_ticks = []
    month_labels = []
    for month in range(1, 13):
        first = date(YEAR, month, 1)
        column = ((first - year_start).days + year_start.weekday()) // 7
        month_ticks.append(column + 0.5)
        month_labels.append(f"{month}月")
    ax.set_xticks(month_ticks)
    ax.set_xticklabels(month_labels)
    ax.xaxis.tick_top()
    ax.tick_params(labelsize=7, colors=COLORS["muted"], length=0, pad=3)
    ax.grid(False)
    colorbar = ax.figure.colorbar(mesh, ax=ax, pad=0.02, fraction=0.035)
    colorbar.set_label(unit, fontsize=7, color=COLORS["muted"])
    colorbar.ax.tick_params(labelsize=6, colors=COLORS["muted"])
    colorbar.outline.set_visible(False)


def _draw_monthly_weather(ax: Any, times: list[datetime], codes: np.ndarray) -> None:
    _panel(ax, "月天气现象频率")
    valid = np.isfinite(codes)
    if not valid.any():
        ax.text(0.5, 0.5, "无有效天气代码", ha="center", va="center", transform=ax.transAxes)
        return
    counts = Counter(np.rint(codes[valid]).astype(int).tolist())
    top_codes = [code for code, _ in counts.most_common(7)]
    monthly_counts = np.zeros((len(top_codes), 12), dtype=float)
    monthly_totals = np.zeros(12, dtype=float)
    for timestamp, code in zip(times, codes):
        if not np.isfinite(code):
            continue
        month = timestamp.month - 1
        monthly_totals[month] += 1
        rounded_code = int(round(code))
        if rounded_code in top_codes:
            monthly_counts[top_codes.index(rounded_code), month] += 1
    with np.errstate(divide="ignore", invalid="ignore"):
        monthly_counts = np.divide(
            monthly_counts,
            monthly_totals,
            out=np.zeros_like(monthly_counts),
            where=monthly_totals > 0,
        ) * 100
    colors = plt.get_cmap("Set2")(np.linspace(0.05, 0.95, len(top_codes)))
    bottom = np.zeros(12)
    for index, color in enumerate(colors):
        label = WEATHER_NAMES.get(top_codes[index], f"代码{top_codes[index]}")
        ax.bar(
            np.arange(1, 13),
            monthly_counts[index],
            bottom=bottom,
            width=0.72,
            color=color,
            edgecolor="white",
            linewidth=0.4,
            label=label,
        )
        bottom += monthly_counts[index]
    _monthly_axis(ax)
    ax.set_ylabel("全年前七类天气占比（%）", fontsize=8, color=COLORS["muted"])
    ax.set_ylim(0, 100)
    ax.legend(ncol=3, fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13))


def _draw_correlation(
    ax: Any, fields: list[str], matrix: np.ndarray
) -> None:
    _panel(ax, "全年气象要素相关性")
    labels = [VARIABLES[field][0] for field in fields]
    image = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=6.5)
    ax.set_yticklabels(labels, fontsize=6.5)
    for row in range(len(fields)):
        for column in range(len(fields)):
            value = matrix[row, column]
            if np.isfinite(value):
                ax.text(
                    column,
                    row,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=5.8,
                    color="#21384a" if abs(value) < 0.72 else "white",
                )
    colorbar = ax.figure.colorbar(image, ax=ax, pad=0.02, fraction=0.035)
    colorbar.set_label("相关系数", fontsize=7, color=COLORS["muted"])
    colorbar.ax.tick_params(labelsize=6, colors=COLORS["muted"])
    colorbar.outline.set_visible(False)
    ax.grid(False)


def make_dashboard(
    times: list[datetime],
    series: dict[str, np.ndarray],
    annual: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    corr_fields: list[str],
    corr_values: np.ndarray,
    output_path: Path,
) -> Path:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    figure = plt.figure(figsize=(22, 34), facecolor=COLORS["paper"])
    figure.text(
        0.055,
        0.976,
        f"{CITY_NAME}·{YEAR}年逐小时历史气象数据统计分析图表",
        fontsize=23,
        weight="bold",
        color=COLORS["ink"],
    )
    figure.text(
        0.055,
        0.958,
        (
            f"时间范围：{times[0]:%Y-%m-%d %H:%M} 至 {times[-1]:%Y-%m-%d %H:%M}"
            f"　|　有效小时：{len(times):,}"
            "　|　数据源：ERA5 由海天气象提供API支持：https://htqx.cn/"
        ),
        fontsize=8.5,
        color=COLORS["muted"],
    )

    annual_by_key = {row["variable_key"]: row for row in annual}

    def annual_value(field: str, stat: str, unit: str) -> str:
        value = annual_by_key[field][stat]
        return f"{value:,.1f} {unit}" if np.isfinite(value) else "暂无数据"

    def annual_range(field: str) -> tuple[str, str]:
        row = annual_by_key[field]
        unit = VARIABLES[field][1]
        low = f"最低 {row['min']:.1f} {unit}" if np.isfinite(row["min"]) else "最低 —"
        high = f"最高 {row['max']:.1f} {unit}" if np.isfinite(row["max"]) else "最高 —"
        return low, high

    direction = annual_by_key["wind_direction_10m"]["mean"]
    direction_text = "暂无数据"
    if np.isfinite(direction):
        direction_sector = COMPASS_16[int((direction % 360 + 11.25) // 22.5) % 16]
        direction_text = f"{direction:.1f}° {direction_sector}"

    valid_codes = _finite(series["weather_code"])
    weather_items = []
    if valid_codes.size:
        weather_counts = Counter(np.rint(valid_codes).astype(int).tolist())
        weather_items = [
            (
                WEATHER_NAMES.get(code, f"代码{code}"),
                count / valid_codes.size * 100,
            )
            for code, count in weather_counts.most_common(3)
        ]

    radiation_total = annual_by_key["shortwave_radiation"]["total"]
    radiation_note = (
        f"全年累计辐射 {radiation_total:,.1f} kWh/m²"
        if np.isfinite(radiation_total)
        else "全年累计辐射 暂无数据"
    )
    wind_mean = annual_by_key["wind_speed_10m"]["mean"]
    gust_max = annual_by_key["wind_gusts_10m"]["max"]
    wind_summary = f"{wind_mean:.1f} m/s" if np.isfinite(wind_mean) else "暂无数据"
    gust_note = (
        f"最大阵风 {gust_max:.1f} m/s"
        if np.isfinite(gust_max)
        else "最大阵风 暂无数据"
    )
    precipitation_total = annual_value("precipitation", "total", "mm")
    cloud_components = [
        (label, annual_by_key[field]["mean"])
        for label, field in (
            ("高", "cloud_cover_high"),
            ("中", "cloud_cover_mid"),
            ("低", "cloud_cover_low"),
        )
    ]
    cloud_note = " · ".join(
        f"{label} {value:.0f}%"
        for label, value in cloud_components
        if np.isfinite(value)
    )
    if not cloud_note:
        cloud_note = "高、中、低云暂无数据"

    valid_wind_directions = _finite(series["wind_direction_10m"])
    prevailing_wind_note = "盛行风向 暂无数据"
    if valid_wind_directions.size:
        sector_indexes = (
            (valid_wind_directions % 360 + 11.25) // 22.5
        ).astype(int) % len(COMPASS_16)
        sector_counts = Counter(sector_indexes.tolist())
        prevailing_sector, prevailing_count = sector_counts.most_common(1)[0]
        prevailing_wind_note = (
            f"盛行风向 {COMPASS_16[prevailing_sector]} "
            f"{prevailing_count / valid_wind_directions.size * 100:.1f}%"
        )

    daily_precipitation = _finite(
        np.asarray([row["precipitation"] for row in daily], dtype=float)
    )
    monthly_precipitation = _finite(
        _monthly_values(times, series["precipitation"], "sum")
    )
    daily_precipitation_max = (
        f"{daily_precipitation.max():.0f} mm"
        if daily_precipitation.size
        else "—"
    )
    monthly_precipitation_max = (
        f"{monthly_precipitation.max():.0f} mm"
        if monthly_precipitation.size
        else "—"
    )
    precipitation_note = (
        f"日最高 {daily_precipitation_max} · 月最高 {monthly_precipitation_max}"
    )

    cards = [
        {
            "label": "年平均气温",
            "value": annual_value("temperature_2m", "mean", "℃"),
            "range": annual_range("temperature_2m"),
        },
        {
            "label": "年平均气压",
            "value": annual_value("pressure_msl", "mean", "hPa"),
            "range": annual_range("pressure_msl"),
        },
        {
            "label": "年平均相对湿度",
            "value": annual_value("relative_humidity_2m", "mean", "%"),
            "range": annual_range("relative_humidity_2m"),
        },
        {
            "label": "年平均云量",
            "value": annual_value("cloud_cover", "mean", "%"),
            "note": cloud_note,
            "note_size": 6.5,
        },
        {
            "label": "年平均风向",
            "value": direction_text,
            "note": prevailing_wind_note,
            "note_size": 6.5,
        },
        {
            "label": "全年累计降水",
            "value": precipitation_total,
            "note": precipitation_note,
            "note_size": 6.2,
        },
        {
            "label": "年平均风速",
            "value": wind_summary,
            "note": gust_note,
        },
        {
            "label": "年平均短波辐射",
            "value": annual_value("shortwave_radiation", "mean", "W/m²"),
            "note": radiation_note,
        },
    ]
    x_start, x_end = 0.055, 0.835
    available_width = x_end - x_start
    card_width = available_width / len(cards)
    x = x_start
    for card in cards:
        figure.text(
            x + 0.004,
            0.932,
            card["label"],
            fontsize=8.5,
            color=COLORS["muted"],
        )
        figure.text(
            x + 0.004,
            0.907,
            card["value"],
            fontsize=12,
            weight="bold",
            color=COLORS["ink"],
        )
        if "range" in card:
            low, high = card["range"]
            figure.text(
                x + 0.004,
                0.889,
                low,
                fontsize=7.1,
                color="#287fb0",
            )
            figure.text(
                x + card_width * 0.49,
                0.889,
                high,
                fontsize=7.1,
                color="#c85f5b",
            )
        elif "note" in card:
            figure.text(
                x + 0.004,
                0.889,
                card["note"],
                fontsize=card.get("note_size", 7.2),
                color=COLORS["muted"],
            )
        x += card_width

    weather_x = 0.85
    figure.text(
        weather_x,
        0.932,
        "全年主要天气",
        fontsize=8.5,
        color=COLORS["muted"],
    )
    if weather_items:
        name, percentage = weather_items[0]
        figure.text(
            weather_x,
            0.907,
            f"{name} {percentage:.1f}%",
            fontsize=12,
            weight="bold",
            color=COLORS["ink"],
        )
        secondary_weather = " · ".join(
            f"{name} {percentage:.1f}%"
            for name, percentage in weather_items[1:]
        )
        if secondary_weather:
            figure.text(
                weather_x,
                0.889,
                secondary_weather,
                fontsize=7.2,
                color=COLORS["muted"],
            )
    else:
        figure.text(
            weather_x,
            0.907,
            "暂无有效天气数据",
            fontsize=8,
            color=COLORS["muted"],
        )

    grid = figure.add_gridspec(
        8,
        4,
        left=0.055,
        right=0.95,
        top=0.84,
        bottom=0.035,
        hspace=0.44,
        wspace=0.32,
    )
    months = np.arange(1, 13)

    # Monthly thermal profile
    ax = figure.add_subplot(grid[0, :2])
    _panel(ax, "月平均气温")
    tmean = _monthly_values(times, series["temperature_2m"])
    tmin = _monthly_values(times, series["temperature_2m"], "min")
    tmax = _monthly_values(times, series["temperature_2m"], "max")
    ax.fill_between(months, tmin, tmax, color=COLORS["cyan"], alpha=0.17, label="2米气温月内范围")
    ax.plot(months, tmean, color=COLORS["blue"], marker="o", lw=2, label="2米气温")
    for field, color, label in (
        ("apparent_temperature", COLORS["orange"], "体感温度"),
        ("dew_point_2m", COLORS["teal"], "露点温度"),
        ("wet_bulb_temperature_2m", COLORS["purple"], "湿球温度"),
    ):
        ax.plot(months, _monthly_values(times, series[field]), color=color, marker=".", lw=1.25, label=label)
    _monthly_axis(ax)
    ax.set_ylabel("温度（℃）", fontsize=8, color=COLORS["muted"])
    ax.legend(ncol=2, fontsize=7, frameon=False)

    # Monthly water balance
    ax = figure.add_subplot(grid[0, 2])
    _panel(ax, "月累积降水与蒸散")
    bar_width = 0.23
    for offset, field, color, label in (
        (-bar_width, "precipitation", COLORS["blue"], "降水"),
        (0, "rain", COLORS["cyan"], "雨量"),
        (bar_width, "snowfall", COLORS["purple"], "降雪"),
    ):
        ax.bar(
            months + offset,
            _monthly_values(times, series[field], "sum"),
            width=bar_width * 0.92,
            color=color,
            label=label,
        )
    ax2 = ax.twinx()
    ax2.plot(
        months,
        _monthly_values(times, series["et0_fao_evapotranspiration"], "sum"),
        color=COLORS["orange"],
        marker="o",
        lw=1.4,
        label="参考蒸散",
    )
    _monthly_axis(ax)
    ax.set_ylabel("降水 / 降雪（mm / cm）", fontsize=7, color=COLORS["muted"])
    ax2.set_ylabel("蒸散（mm）", fontsize=7, color=COLORS["orange"])
    ax2.tick_params(labelsize=7, colors=COLORS["orange"])
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, fontsize=6.5, frameon=False, loc="upper right")

    # Annual wind rose
    ax = figure.add_subplot(grid[0, 3], projection="polar")
    _draw_wind_rose(ax, series)

    # Humidity and cloud
    ax = figure.add_subplot(grid[1, :2])
    _panel(ax, "月平均相对湿度与云量")
    for field, color, label in (
        ("relative_humidity_2m", COLORS["blue"], "相对湿度"),
        ("cloud_cover", COLORS["purple"], "总云量"),
        ("cloud_cover_low", COLORS["cyan"], "低云量"),
        ("cloud_cover_mid", COLORS["teal"], "中云量"),
        ("cloud_cover_high", COLORS["orange"], "高云量"),
    ):
        ax.plot(months, _monthly_values(times, series[field]), marker="o", ms=3, lw=1.5, color=color, label=label)
    _monthly_axis(ax)
    ax.set_ylim(0, 100)
    ax.set_ylabel("相对湿度 / 云量（%）", fontsize=8, color=COLORS["muted"])
    ax.legend(ncol=3, fontsize=7, frameon=False)

    # Solar irradiance means and separately reported integrated energy.
    ax = figure.add_subplot(grid[1, 2:])
    _panel(ax, "月平均太阳辐射")
    radiation_fields = (
        ("shortwave_radiation", COLORS["orange"], "短波"),
        ("direct_radiation", COLORS["blue"], "直接"),
        ("diffuse_radiation", COLORS["cyan"], "散射"),
        ("global_tilted_irradiance", COLORS["purple"], "倾斜面总量"),
    )
    width = 0.18
    for index, (field, color, label) in enumerate(radiation_fields):
        offset = (index - (len(radiation_fields) - 1) / 2) * width
        ax.bar(
            months + offset,
            _monthly_values(times, series[field]),
            width=width * 0.9,
            color=color,
            label=label,
        )
    _monthly_axis(ax)
    ax.set_ylabel("辐射通量（W/m²）", fontsize=8, color=COLORS["muted"])
    ax.legend(ncol=2, fontsize=7, frameon=False)

    # Month by hour heatmaps
    ax = figure.add_subplot(grid[2, :2])
    _draw_diurnal_heatmap(
        ax, times, series["temperature_2m"], "月小时平均气温", "coolwarm", "℃"
    )
    ax = figure.add_subplot(grid[2, 2:])
    _draw_diurnal_heatmap(
        ax,
        times,
        series["precipitation"],
        "月小时平均降水",
        "Blues",
        "mm/h",
        power=True,
    )

    # Calendar heatmaps
    ax = figure.add_subplot(grid[3, :2])
    _draw_calendar(ax, daily, "precipitation", "日累积降水", "Blues", "mm/day")
    ax = figure.add_subplot(grid[3, 2:])
    _draw_calendar(
        ax,
        daily,
        "shortwave_radiation",
        "日平均短波辐射",
        "YlOrBr",
        "W/m²",
    )

    # Soil temperature and moisture
    ax = figure.add_subplot(grid[4, :2])
    _panel(ax, "月平均不同深度土壤温度")
    soil_temperature_fields = (
        ("soil_temperature_0_to_7cm", COLORS["orange"], "0–7 cm"),
        ("soil_temperature_7_to_28cm", COLORS["blue"], "7–28 cm"),
        ("soil_temperature_28_to_100cm", COLORS["teal"], "28–100 cm"),
        ("soil_temperature_100_to_255cm", COLORS["purple"], "100–255 cm"),
    )
    for field, color, label in soil_temperature_fields:
        ax.plot(months, _monthly_values(times, series[field]), color=color, marker="o", ms=3, lw=1.5, label=label)
    _monthly_axis(ax)
    ax.set_ylabel("温度（℃）", fontsize=8, color=COLORS["muted"])
    ax.legend(ncol=2, fontsize=7, frameon=False)

    ax = figure.add_subplot(grid[4, 2:])
    _panel(ax, "月平均不同深度土壤湿度")
    soil_moisture_fields = (
        ("soil_moisture_0_to_7cm", COLORS["orange"], "0–7 cm"),
        ("soil_moisture_7_to_28cm", COLORS["blue"], "7–28 cm"),
        ("soil_moisture_28_to_100cm", COLORS["teal"], "28–100 cm"),
        ("soil_moisture_100_to_255cm", COLORS["purple"], "100–255 cm"),
    )
    for field, color, label in soil_moisture_fields:
        ax.plot(months, _monthly_values(times, series[field]), color=color, marker="o", ms=3, lw=1.5, label=label)
    _monthly_axis(ax)
    ax.set_ylabel("体积含水率（m³/m³）", fontsize=8, color=COLORS["muted"])
    ax.legend(ncol=2, fontsize=7, frameon=False)

    # Daily temperature range and wind/humidity
    ax = figure.add_subplot(grid[5, :2])
    _panel(ax, "日最高最低与平均气温")
    dates = [date.fromisoformat(row["date"]) for row in daily]
    daily_tmin = np.asarray([row["temperature_min"] for row in daily], dtype=float)
    daily_tmax = np.asarray([row["temperature_max"] for row in daily], dtype=float)
    daily_tmean = np.asarray([row["temperature_2m"] for row in daily], dtype=float)
    ax.fill_between(dates, daily_tmin, daily_tmax, color=COLORS["cyan"], alpha=0.22, label="日最高–最低")
    ax.plot(dates, daily_tmean, color=COLORS["blue"], lw=1, label="日平均")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
    ax.set_ylabel("温度（℃）", fontsize=8, color=COLORS["muted"])
    ax.legend(ncol=2, fontsize=7, frameon=False)

    ax = figure.add_subplot(grid[5, 2:])
    _panel(ax, "日平均风速与相对湿度")
    wind_dates = dates
    wind_speed_daily = np.asarray([row["wind_speed_10m"] for row in daily], dtype=float)
    humidity_daily = np.asarray([row["relative_humidity_2m"] for row in daily], dtype=float)
    ax.plot(wind_dates, wind_speed_daily, color=COLORS["blue"], lw=0.9, label="10米风速")
    ax.set_ylabel("风速（m/s）", fontsize=8, color=COLORS["blue"])
    ax2 = ax.twinx()
    ax2.plot(wind_dates, humidity_daily, color=COLORS["teal"], lw=0.9, alpha=0.85, label="相对湿度")
    ax2.set_ylabel("相对湿度（%）", fontsize=8, color=COLORS["teal"])
    ax2.set_ylim(0, 100)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
    ax.tick_params(labelsize=7, colors=COLORS["muted"])
    ax2.tick_params(labelsize=7, colors=COLORS["teal"])
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, fontsize=7, frameon=False, loc="upper right")

    # Weather-code composition and pairwise correlations
    ax = figure.add_subplot(grid[6, :2])
    _draw_monthly_weather(ax, times, series["weather_code"])
    ax = figure.add_subplot(grid[6, 2:])
    _draw_correlation(ax, corr_fields, corr_values)

    # Pressure, atmospheric column and boundary layer
    ax = figure.add_subplot(grid[7, :2])
    _panel(ax, "月平均气压与水汽压亏缺")
    for field, color, label in (
        ("pressure_msl", COLORS["blue"], "海平面气压"),
        ("surface_pressure", COLORS["teal"], "地面气压"),
    ):
        ax.plot(months, _monthly_values(times, series[field]), marker="o", ms=3, lw=1.4, color=color, label=label)
    _monthly_axis(ax)
    ax.set_ylabel("气压（hPa）", fontsize=8, color=COLORS["muted"])
    ax2 = ax.twinx()
    ax2.plot(
        months,
        _monthly_values(times, series["vapour_pressure_deficit"]),
        color=COLORS["orange"],
        marker="s",
        ms=2.5,
        lw=1.25,
        label="水汽压亏缺",
    )
    ax2.set_ylabel("水汽压亏缺（kPa）", fontsize=7, color=COLORS["orange"])
    ax2.tick_params(labelsize=7, colors=COLORS["orange"])
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, fontsize=7, frameon=False)

    ax = figure.add_subplot(grid[7, 2:])
    _panel(ax, "月平均边界层高度与整层可降水量")
    ax.plot(
        months,
        _monthly_values(times, series["boundary_layer_height"]),
        color=COLORS["purple"],
        marker="o",
        ms=3,
        lw=1.5,
        label="边界层高度",
    )
    _monthly_axis(ax)
    ax.set_ylabel("边界层高度（m）", fontsize=8, color=COLORS["purple"])
    ax.tick_params(axis="y", colors=COLORS["purple"])
    ax2 = ax.twinx()
    ax2.plot(
        months,
        _monthly_values(times, series["total_column_integrated_water_vapour"]),
        color=COLORS["cyan"],
        marker="s",
        ms=3,
        lw=1.5,
        label="整层可降水量",
    )
    ax2.set_ylabel("整层可降水量（kg/m²）", fontsize=8, color=COLORS["cyan"])
    ax2.tick_params(labelsize=7, colors=COLORS["cyan"])
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, fontsize=7, frameon=False)

    figure.text(
        0.5,
        0.017,
        "原始数据下载和气象变量定义单位查询请访问海天气象官网：https://htqx.cn/",
        ha="center",
        fontsize=8,
        color=COLORS["muted"],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    return output_path


def main() -> None:
    payload = fetch_yearly_history()
    data = parse_history(payload)
    times: list[datetime] = data["times"]
    series: dict[str, np.ndarray] = data["series"]
    if data["missing"]:
        print(
            "API 未返回以下变量，相关统计和图表将留空："
            + ", ".join(data["missing"])
        )

    annual = annual_statistics(series)
    monthly = monthly_statistics(times, series)
    daily = daily_summaries(times, series)
    corr_fields, corr_values = correlation_matrix(series)

    prefix = f"{_safe_city_name(CITY_NAME)}_{YEAR}"
    figure_path = PROJECT_ROOT / "figures" / f"{prefix}_全年逐小时历史气象分析.png"
    output_paths = export_statistics(
        annual, monthly, daily, corr_fields, corr_values
    )
    make_dashboard(
        times, series, annual, daily, corr_fields, corr_values, figure_path
    )

    expected = (date(YEAR + 1, 1, 1) - date(YEAR, 1, 1)).days * 24
    print(f"地点：{CITY_NAME}　年份：{YEAR}")
    print(
        f"有效时次：{len(times):,} / {expected:,}　"
        f"覆盖：{times[0]:%Y-%m-%d %H:%M} 至 {times[-1]:%Y-%m-%d %H:%M}"
    )
    print(f"图表：{figure_path}")
    for path in output_paths.values():
        print(f"CSV：{path}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
