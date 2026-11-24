# =============================================================================
# 西安市未来 10 日逐小时天气预报与可视化
#
# 功能
#   * 调用海天气象逐日天气预报 API，取得 240 个小时的预报数据。
#   * 在图表顶部展示最接近当前北京时间的预报时次及温度、天气、风、
#     气压、降水、短波辐射、总云量、能见度和相对湿度。
#   * 汇总每日高低温、天气、平均风速与风向、云量、能见度、相对湿度、
#     累积降水和降水时段。
#   * 绘制逐小时气温趋势及“日期 × 小时”降水日历热力格。
#   * 天气图标使用 Matplotlib 基本图元绘制，不依赖外部图标版权或网络。
#   * 数据源及在线文档：https://htqx.cn/
#
# 可修改参数（均为大写常量）
#   API_KEY: 在海天气象个人中心查看26位 API Key。
#   CITY_NAME: 查询地点，支持全国市区县。
#   YEAR / MONTH / DAY: 预报起始日期，默认当前北京时间日期。
#   OUTPUT_PATH: 输出 PNG 路径，默认保存到项目 figures 目录。
#
# PowerShell 运行示例（在项目根目录执行）
#   .\.venv\Scripts\python.exe src\city_forecast.py
#
# 修改上方日期常量可指定 API 支持范围内的起始日期。日期接口返回的时间
# 使用北京时间；图片文件名由地点、返回数据首个时次和预报周期组成。
# =============================================================================

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.path import Path as MplPath
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch


BEIJING_TZ = timezone(timedelta(hours=8))
TODAY = datetime.now(BEIJING_TZ).date()

# =============================================================================
# 用户可修改参数
# =============================================================================
# API_KEY = os.getenv("HTMETEO_API_KEY", "").strip()

API_KEY = "2js7rY7j89JgbNH76Ggh7TF5r6"  # 请在海天气象个人中心查看26位 API Key：https://htqx.cn/
CITY_NAME = "伊犁哈萨克自治州"
YEAR = TODAY.year
MONTH = TODAY.month
DAY = TODAY.day

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://htqx.cn/meteo/api/forecast/daily"

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
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
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

RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
THUNDER_CODES = {95, 96, 99}
RAIN_LEVELS = [0, 0.1, 0.5, 1, 2.5, 5, 10, 20, 50]
RAIN_COLORS = [
    "#f2f8fc",
    "#d8effa",
    "#b5e3f5",
    "#82d0ed",
    "#4db5dd",
    "#238fc1",
    "#176ba0",
    "#123f70",
]


def _ordered_values(value: Any, field: str) -> list[Any]:
    if isinstance(value, dict):
        try:
            return [value[key] for key in sorted(value, key=lambda item: int(item))]
        except (TypeError, ValueError):
            raise RuntimeError(f"API field '{field}' has non-numeric time indexes.") from None
    if isinstance(value, list):
        return value
    raise RuntimeError(f"API field '{field}' must be an indexed object or list.")


def _numeric_series(payload: dict[str, Any], field: str) -> np.ndarray:
    if field not in payload:
        raise RuntimeError(f"Forecast response is missing '{field}'.")
    values = _ordered_values(payload[field], field)
    result = []
    for value in values:
        try:
            result.append(float(value) if value is not None else np.nan)
        except (TypeError, ValueError):
            result.append(np.nan)
    return np.asarray(result, dtype=float)


def fetch_forecast() -> dict[str, Any]:
    if not API_KEY:
        raise RuntimeError(
            "API key is not configured. Set HTMETEO_API_KEY in the environment first."
        )

    city = quote(CITY_NAME, safe="")
    url = f"{API_URL}/{city}/{YEAR}/{MONTH}/{DAY}/{API_KEY}"
    try:
        response = requests.get(url, timeout=(10, 90))
    except requests.RequestException as exc:
        raise RuntimeError(f"Forecast request failed ({type(exc).__name__}).") from None

    if response.status_code != 200:
        raise RuntimeError(f"Forecast API returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("Forecast API response was not valid JSON.") from None
    if not isinstance(payload, dict):
        raise RuntimeError("Forecast API response must be a JSON object.")
    if "error" in payload:
        raise RuntimeError(f"Forecast API returned an error: {payload['error']}")
    return payload


def parse_forecast(payload: dict[str, Any]) -> dict[str, Any]:
    if "date" not in payload:
        raise RuntimeError("Forecast response is missing 'date'.")
    raw_times = _ordered_values(payload["date"], "date")
    times = []
    for value in raw_times:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise RuntimeError(f"Invalid forecast time value: {value!r}.") from None
        # API timestamps are Beijing wall time; retain their clock fields as-is.
        times.append(parsed.replace(tzinfo=None))

    series = {
        field: _numeric_series(payload, field)
        for field in (
            "temperature_2m",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "pressure_msl",
            "precipitation",
            "shortwave_radiation",
            "cloud_cover",
            "visibility",
            "relative_humidity_2m",
        )
    }
    if not times:
        raise RuntimeError("Forecast response contains no hourly records.")
    for field, values in series.items():
        if values.size != len(times):
            raise RuntimeError(
                f"Forecast field '{field}' contains {values.size} values; "
                f"expected {len(times)}."
            )
    return {"times": times, **series}


def weather_name(code: float) -> str:
    if not np.isfinite(code):
        return "天气信息缺失"
    return WEATHER_NAMES.get(int(round(code)), "天气现象")


def compass_direction(degrees: float) -> str:
    if not np.isfinite(degrees):
        return "—"
    directions = ("北", "东北", "东", "东南", "南", "西南", "西", "西北")
    return directions[int((degrees % 360 + 22.5) // 45) % 8]


def _valid_mean(values: np.ndarray) -> float:
    valid = values[np.isfinite(values)]
    return float(valid.mean()) if valid.size else float("nan")


def _wind_direction_mean(values: np.ndarray) -> float:
    valid = values[np.isfinite(values)]
    if not valid.size:
        return float("nan")
    radians = np.deg2rad(valid)
    sine = np.sin(radians).mean()
    cosine = np.cos(radians).mean()
    if np.isclose(sine, 0) and np.isclose(cosine, 0):
        return float("nan")
    return float(np.rad2deg(np.arctan2(sine, cosine)) % 360)


def _precipitation_periods(
    times: list[datetime], precipitation: np.ndarray, indexes: np.ndarray
) -> str:
    wet_hours = [
        int(index)
        for index in indexes
        if np.isfinite(precipitation[index]) and precipitation[index] >= 0.1
    ]
    if not wet_hours:
        return "无明显降水"

    groups: list[list[int]] = [[wet_hours[0]]]
    for index in wet_hours[1:]:
        if index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    periods = []
    for group in groups:
        start = times[group[0]].strftime("%H")
        end_hour = (times[group[-1]] + timedelta(hours=1)).strftime("%H")
        periods.append(f"{start}–{end_hour}时")
    return "、".join(periods)


def daily_summaries(data: dict[str, Any]) -> list[dict[str, Any]]:
    dates = [item.date() for item in data["times"]]
    unique_dates = list(dict.fromkeys(dates))
    summaries = []
    for forecast_date in unique_dates:
        indexes = np.asarray(
            [index for index, item_date in enumerate(dates) if item_date == forecast_date],
            dtype=int,
        )
        temperatures = data["temperature_2m"][indexes]
        valid_temperatures = temperatures[np.isfinite(temperatures)]
        if not valid_temperatures.size:
            high = low = float("nan")
        else:
            high = float(valid_temperatures.max())
            low = float(valid_temperatures.min())

        midday_index = min(
            indexes,
            key=lambda index: abs(data["times"][index].hour - 12),
        )
        weather = weather_name(data["weather_code"][midday_index])
        direction = _wind_direction_mean(data["wind_direction_10m"][indexes])
        precipitation = data["precipitation"][indexes]
        precipitation_total = float(np.nansum(precipitation))
        summaries.append(
            {
                "date": forecast_date,
                "high": high,
                "low": low,
                "weather": weather,
                "weather_code": float(data["weather_code"][midday_index]),
                "wind_speed": _valid_mean(data["wind_speed_10m"][indexes]),
                "wind_direction": direction,
                "cloud_cover": _valid_mean(data["cloud_cover"][indexes]),
                "visibility": _valid_mean(data["visibility"][indexes]),
                "relative_humidity": _valid_mean(
                    data["relative_humidity_2m"][indexes]
                ),
                "precipitation": precipitation_total,
                "precipitation_periods": _precipitation_periods(
                    data["times"], data["precipitation"], indexes
                ),
            }
        )
    return summaries


def _format_number(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}" if np.isfinite(value) else "—"


def _format_temperature(value: float) -> str:
    return f"{int(np.rint(value))}" if np.isfinite(value) else "—"


def draw_weather_icon(
    axes: Any,
    code: float,
    center: tuple[float, float] = (0.5, 0.42),
    scale: float = 1.0,
) -> None:
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.set_aspect("equal")
    axes.axis("off")
    x, y = center
    condition = int(round(code)) if np.isfinite(code) else -1
    line_color = "#7898ad"
    sun_color = "#f3b653"

    def point(dx: float, dy: float) -> tuple[float, float]:
        return x + dx * scale, y + dy * scale

    def draw_sun(
        sun_x: float,
        sun_y: float,
        radius: float,
        behind_cloud: bool,
        ray_extension: float = 0.145,
    ) -> None:
        zorder = 2 if behind_cloud else 3
        axes.add_patch(
            Circle(
                (sun_x, sun_y),
                radius * scale,
                facecolor="#fff3d8",
                edgecolor=sun_color,
                linewidth=1.35 * scale,
                zorder=zorder,
            )
        )
        for angle in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            inner = radius + ray_extension * 0.45
            outer = radius + ray_extension
            start = (sun_x + np.cos(angle) * inner * scale, sun_y + np.sin(angle) * inner * scale)
            end = (sun_x + np.cos(angle) * outer * scale, sun_y + np.sin(angle) * outer * scale)
            axes.plot(
                [start[0], end[0]],
                [start[1], end[1]],
                color=sun_color,
                linewidth=1.35 * scale,
                solid_capstyle="round",
                zorder=zorder,
            )

    def draw_cloud() -> None:
        vertices = [
            point(-0.38, 0.02),
            point(-0.50, 0.02),
            point(-0.55, 0.08),
            point(-0.55, 0.17),
            point(-0.55, 0.26),
            point(-0.46, 0.34),
            point(-0.34, 0.34),
            point(-0.30, 0.40),
            point(-0.17, 0.45),
            point(-0.02, 0.40),
            point(0.09, 0.47),
            point(0.26, 0.47),
            point(0.34, 0.38),
            point(0.47, 0.38),
            point(0.56, 0.30),
            point(0.56, 0.21),
            point(0.56, 0.12),
            point(0.46, 0.02),
            point(0.34, 0.02),
            point(0.16, 0.02),
            point(-0.20, 0.02),
            point(-0.38, 0.02),
            point(-0.38, 0.02),
        ]
        codes = [MplPath.MOVETO] + [MplPath.CURVE4] * 21 + [MplPath.CLOSEPOLY]
        cloud_path = MplPath(vertices, codes)
        axes.add_patch(
            PathPatch(
                cloud_path,
                facecolor="#f5f9fc",
                edgecolor=line_color,
                linewidth=1.45 * scale,
                joinstyle="round",
                capstyle="round",
                zorder=4,
            )
        )

    if condition in (0, 1):
        draw_sun(x, y, 0.18, behind_cloud=False)
        return
    if condition == 2:
        draw_sun(
            *point(0.25, 0.30),
            radius=0.15,
            behind_cloud=True,
            ray_extension=0.10,
        )

    draw_cloud()

    if condition in RAIN_CODES:
        for dx in (-0.22, 0, 0.22):
            axes.plot(
                [point(dx + 0.025, -0.16)[0], point(dx - 0.015, -0.25)[0]],
                [point(dx, -0.16)[1], point(dx, -0.25)[1]],
                color="#4d9fc8",
                linewidth=1.65 * scale,
                solid_capstyle="round",
                zorder=3,
            )
    elif condition in SNOW_CODES:
        for dx in (-0.20, 0, 0.20):
            snow_x, snow_y = point(dx, -0.20)
            arm = 0.045 * scale
            for angle in (0, np.pi / 3, 2 * np.pi / 3):
                axes.plot(
                    [snow_x - np.cos(angle) * arm, snow_x + np.cos(angle) * arm],
                    [snow_y - np.sin(angle) * arm, snow_y + np.sin(angle) * arm],
                    color="#58a7cf",
                    linewidth=1.0 * scale,
                    solid_capstyle="round",
                    zorder=3,
                )
    elif condition in THUNDER_CODES:
        bolt_vertices = [
            point(0.08, -0.075),
            point(-0.10, -0.31),
            point(0.015, -0.27),
            point(-0.045, -0.41),
            point(0.16, -0.215),
            point(0.055, -0.23),
            point(0.08, -0.075),
        ]
        bolt_codes = [
            MplPath.MOVETO,
            MplPath.LINETO,
            MplPath.LINETO,
            MplPath.LINETO,
            MplPath.LINETO,
            MplPath.LINETO,
            MplPath.CLOSEPOLY,
        ]
        axes.add_patch(
            PathPatch(
                MplPath(bolt_vertices, bolt_codes),
                facecolor="#f3b653",
                edgecolor="#e2a13f",
                linewidth=0.7 * scale,
                zorder=6,
            )
        )
    elif condition in (45, 48):
        for offset in (-0.12, -0.24):
            start = point(-0.25, offset)
            end = point(0.25, offset)
            axes.plot(
                [start[0], end[0]],
                [start[1], end[1]],
                color="#9bb3c2",
                linewidth=1.2 * scale,
                solid_capstyle="round",
                alpha=0.9,
                zorder=3,
            )


def _current_index(data: dict[str, Any]) -> int:
    now = datetime.now(BEIJING_TZ).replace(tzinfo=None)
    return min(
        range(len(data["times"])),
        key=lambda index: abs((data["times"][index] - now).total_seconds()),
    )


def _make_daily_table(axes: Any, summaries: list[dict[str, Any]]) -> None:
    axes.axis("off")
    headers = [
        "日期",
        "天气图标",
        "天气",
        "最高 / 最低",
        "平均风速 / 风向",
        "日降水",
        "降水时段",
        "总云量",
        "能见度",
        "相对湿度",
    ]
    rows = []
    for summary in summaries:
        weekday = "一二三四五六日"[summary["date"].weekday()]
        rows.append(
            [
                f'{summary["date"]:%m-%d} 周{weekday}',
                "",
                summary["weather"],
                (
                    f'{_format_temperature(summary["high"])}℃ / '
                    f'{_format_temperature(summary["low"])}℃'
                ),
                (
                    f'{_format_number(summary["wind_speed"])} m/s '
                    f'{compass_direction(summary["wind_direction"])}'
                ),
                f'{_format_number(summary["precipitation"])} mm',
                summary["precipitation_periods"],
                f'{_format_number(summary["cloud_cover"], 0)}%',
                f'{_format_number(summary["visibility"] / 1000)} km',
                f'{_format_number(summary["relative_humidity"], 0)}%',
            ]
        )

    table = axes.table(
        cellText=rows,
        colLabels=headers,
        colWidths=[0.095, 0.05, 0.08, 0.12, 0.15, 0.08, 0.16, 0.075, 0.09, 0.10],
        cellLoc="center",
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor("#e6eef4")
        cell.set_linewidth(0.55)
        if row == 0:
            cell.set_facecolor("#eaf4fb")
            cell.set_text_props(color="#35546d", weight="bold")
        else:
            cell.set_facecolor("#ffffff" if row % 2 else "#f7fafc")
            cell.set_text_props(color="#34495e")
            cell.set_height(0.085)

    table_figure = axes.figure
    table_figure.canvas.draw()
    table_bounds = axes.get_position()
    for row_index, summary in enumerate(summaries, start=1):
        icon_cell = table[(row_index, 1)]
        icon_axes = table_figure.add_axes(
            [
                table_bounds.x0
                + (icon_cell.get_x() + icon_cell.get_width() * 0.12) * table_bounds.width,
                table_bounds.y0
                + (icon_cell.get_y() + icon_cell.get_height() * 0.12) * table_bounds.height,
                icon_cell.get_width() * table_bounds.width * 0.76,
                icon_cell.get_height() * table_bounds.height * 0.76,
            ]
        )
        draw_weather_icon(icon_axes, summary["weather_code"], scale=0.72)


def plot_forecast(data: dict[str, Any], output_path: Path) -> Path:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure = plt.figure(figsize=(16, 13), facecolor="#eef4f8")

    figure.text(
        0.06,
        0.965,
        f"{CITY_NAME}·未来10日天气预报",
        fontsize=23,
        fontweight="bold",
        color="#17324d",
        ha="left",
    )
    figure.text(
        0.06,
        0.94,
        (
            "逐小时预报  /  "
            f"起报时间 {(data['times'][0].date() - timedelta(days=1)):%Y-%m-%d} 20:00"
            "（北京时间）"
        ),
        fontsize=10,
        color="#688096",
        ha="left",
    )

    figure.text(0.06, 0.907, "当前天气", fontsize=13, color="#17324d", fontweight="bold")
    card = figure.add_axes([0.05, 0.715, 0.90, 0.175])
    card.axis("off")
    card.add_patch(
        FancyBboxPatch(
            (0, 0),
            1,
            1,
            boxstyle="round,pad=0.012,rounding_size=0.035",
            facecolor="#ffffff",
            edgecolor="#e2edf4",
            linewidth=0.8,
            transform=card.transAxes,
            clip_on=False,
        )
    )

    current = _current_index(data)
    code = data["weather_code"][current]
    icon_axes = figure.add_axes([0.075, 0.758, 0.09, 0.10])
    draw_weather_icon(icon_axes, code, scale=0.82)
    figure.text(0.18, 0.84, f"{CITY_NAME}  ·  当前天气", fontsize=9, color="#688096")
    figure.text(
        0.18,
        0.775,
        f'{_format_number(data["temperature_2m"][current], 0)}℃',
        fontsize=31,
        color="#17324d",
        fontweight="bold",
    )
    current_time = data["times"][current].strftime("%m月%d日 %H:%M")
    figure.text(
        0.32,
        0.82,
        weather_name(code),
        fontsize=10,
        color="#35546d",
    )
    figure.text(0.32, 0.78, current_time, fontsize=9, color="#688096")

    metric_fields_top = [
        ("风力 / 风向", f'{_format_number(data["wind_speed_10m"][current])} m/s · {compass_direction(data["wind_direction_10m"][current])}'),
        ("气压", f'{_format_number(data["pressure_msl"][current])} hPa'),
        ("小时降水", f'{_format_number(data["precipitation"][current])} mm'),
        ("短波辐射", f'{_format_number(data["shortwave_radiation"][current], 0)} W/m²'),
        ("总云量", f'{_format_number(data["cloud_cover"][current], 0)}%'),
        ("能见度", f'{_format_number(data["visibility"][current] / 1000)} km'),
        ("相对湿度", f'{_format_number(data["relative_humidity_2m"][current], 0)}%'),
    ]
    for x, (label, value) in zip(np.linspace(0.47, 0.89, len(metric_fields_top)), metric_fields_top):
        figure.text(x, 0.835, label, fontsize=7.2, color="#8095a5", ha="left")
        figure.text(x, 0.79, value, fontsize=8, color="#29465f", ha="left")

    figure.text(0.06, 0.69, "未来 10 日逐日预报", fontsize=13, color="#17324d", fontweight="bold")
    table_axes = figure.add_axes([0.055, 0.395, 0.89, 0.27])

    _make_daily_table(table_axes, daily_summaries(data))

    figure.text(0.06, 0.37, "气温变化趋势", fontsize=13, color="#17324d", fontweight="bold")
    temperature_axes = figure.add_axes([0.09, 0.22, 0.84, 0.125], facecolor="#f8fbfd")
    times = data["times"]
    temperatures = data["temperature_2m"]
    temperature_min = np.nanmin(temperatures)
    temperature_max = np.nanmax(temperatures)
    temperature_axes.fill_between(
        times,
        temperatures,
        temperature_min - 2,
        color="#72b7d8",
        alpha=0.17,
        linewidth=0,
    )
    temperature_axes.plot(
        times,
        temperatures,
        color="#2887b5",
        linewidth=1.8,
        marker="o",
        markersize=2.2,
        markevery=6,
        label="逐小时气温",
    )
    summaries = daily_summaries(data)
    for summary in summaries:
        indexes = [
            index
            for index, timestamp in enumerate(times)
            if timestamp.date() == summary["date"]
        ]
        if indexes and np.isfinite(summary["high"]) and np.isfinite(summary["low"]):
            middle = times[indexes[len(indexes) // 2]]
            temperature_axes.vlines(
                middle,
                summary["low"],
                summary["high"],
                color="#f0a15b",
                linewidth=2,
                alpha=0.9,
                label="日最高 / 最低" if summary is summaries[0] else None,
            )
            temperature_axes.scatter(
                [middle, middle],
                [summary["low"], summary["high"]],
                s=10,
                color=["#74a9cf", "#e98761"],
                zorder=4,
            )
            temperature_axes.annotate(
                f'{_format_temperature(summary["high"])}℃',
                (middle, summary["high"]),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=6.5,
                color="#c66d43",
            )
            temperature_axes.annotate(
                f'{_format_temperature(summary["low"])}℃',
                (middle, summary["low"]),
                xytext=(0, -8),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=6.5,
                color="#4d83a7",
            )
    day_ticks = [
        datetime.combine(item["date"], datetime.min.time()) + timedelta(hours=12)
        for item in summaries
    ]
    temperature_axes.set_xticks(day_ticks)
    # Matplotlib treats naive datetimes as UTC; use UTC formatting to preserve wall time.
    temperature_axes.xaxis.set_major_formatter(
        mdates.DateFormatter("%m/%d %H:%M", tz=timezone.utc)
    )
    temperature_axes.set_xlim(times[0], times[-1])
    temperature_axes.set_ylim(
        temperature_min - 2,
        temperature_max + max(3, (temperature_max - temperature_min) * 0.22),
    )
    temperature_axes.set_ylabel("气温 (℃)", fontsize=8, color="#688096")
    temperature_axes.tick_params(labelsize=7, colors="#688096", length=2)
    temperature_axes.grid(axis="y", color="#dce8ef", linewidth=0.6)
    temperature_axes.spines[["top", "right"]].set_visible(False)
    temperature_axes.spines[["left", "bottom"]].set_color("#cddbe5")
    temperature_axes.legend(
        loc="upper right",
        frameon=False,
        ncol=2,
        fontsize=7,
    )

    figure.text(0.06, 0.188, "逐小时降水日历", fontsize=13, color="#17324d", fontweight="bold")
    figure.text(
        0.06,
        0.168,
        "按日期与小时排列，颜色越深表示小时降水量越大",
        fontsize=8,
        color="#8095a5",
    )
    calendar_axes = figure.add_axes([0.10, 0.04, 0.79, 0.11], facecolor="#f8fbfd")
    summaries = daily_summaries(data)
    dates = [item["date"] for item in summaries]
    rain_matrix = np.zeros((24, len(dates)), dtype=float)
    for index, timestamp in enumerate(times):
        if timestamp.date() not in dates:
            continue
        day_index = dates.index(timestamp.date())
        amount = data["precipitation"][index]
        rain_matrix[timestamp.hour, day_index] = amount if np.isfinite(amount) else 0

    rain_cmap = ListedColormap(RAIN_COLORS)
    rain_norm = BoundaryNorm(RAIN_LEVELS, rain_cmap.N, clip=True)
    mesh = calendar_axes.pcolormesh(
        np.arange(len(dates) + 1),
        np.arange(25),
        rain_matrix,
        cmap=rain_cmap,
        norm=rain_norm,
        shading="flat",
        edgecolors="#ffffff",
        linewidth=0.45,
    )
    calendar_axes.set_xlim(0, len(dates))
    calendar_axes.set_ylim(24, 0)
    calendar_axes.set_xticks(np.arange(len(dates)) + 0.5)
    calendar_axes.set_xticklabels([item.strftime("%m/%d") for item in dates], fontsize=7)
    calendar_axes.xaxis.tick_top()
    calendar_axes.set_yticks([0.5, 6.5, 12.5, 18.5])
    calendar_axes.set_yticklabels(["00时", "06时", "12时", "18时"], fontsize=7)
    calendar_axes.tick_params(length=0, colors="#688096", pad=3)
    for spine in calendar_axes.spines.values():
        spine.set_visible(False)
    colorbar_axes = figure.add_axes([0.915, 0.045, 0.012, 0.10])
    colorbar = figure.colorbar(mesh, cax=colorbar_axes, extend="max")
    colorbar.set_label("mm/h", fontsize=7, color="#688096")
    colorbar.ax.tick_params(labelsize=6, colors="#688096", length=2)
    colorbar.outline.set_visible(False)

    figure.text(
        0.5,
        0.015,
        "数据源：ECMWF  由海天气象提供API支持：https://htqx.cn/",
        ha="center",
        fontsize=8,
        color="#688096",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    return output_path


def main() -> None:
    try:
        date(YEAR, MONTH, DAY)
    except ValueError as exc:
        raise SystemExit(f"Invalid forecast date: {exc}") from None
    try:
        data = parse_forecast(fetch_forecast())
        forecast_time = data["times"][0].strftime("%Y%m%d%H")
        output_path = (
            PROJECT_ROOT
            / "figures"
            / f"{CITY_NAME}_{forecast_time}_\u672a\u676510\u65e5\u5929\u6c14\u9884\u62a5.png"
        )
        output_path = plot_forecast(data, output_path)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    print(f"Forecast chart saved to: {output_path}")
    print(f"Received {len(data['times'])} hourly records for {CITY_NAME}.")


if __name__ == "__main__":
    main()
