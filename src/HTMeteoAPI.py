import requests

# api主要提供以下9个接口，其中3个用于调取天气预报数据，4个用于调取历史天气数据，1个用于查询坐标信息，1个用于调取空气质量指数
# 1.调取某日天气预报数据，时间跨度：选定日期起未来10日，共240小时（通过地名和坐标两种方式）
# 2.调取某日历史天气数据，时间跨度：选定日期的当日，共24小时
# 3.调取某月历史天气数据，时间跨度：选定年月的当月，共30日720小时
# 4.调取某年历史天气数据，时间跨度：选定年的当年，共12月365日8760小时
# 5.通过坐标查询地名信息
# 6.调取统计分析历史天气数据，全国市区县逐年、逐月、逐日统计分析数据，包括均值、极值、累积值
# 7.调取某年逐小时空气质量数据，包括空气质量指数和各项污染物浓度小时平均值
# 8.调取某种气象要素某时次全国0.1°网格预报数据，时间范围：未来10日某小时，共240小时
# 9.调取某地逐日天气预报摘要数据，时间跨度：未来10日

# API Key可以在“个人中心”页面查看，所有用户都有API Key但是仅专业用户可以使用API功能，所有接口都需要API Key

api_key = "您的26位API Key"

# -------------------------------------1.调取某日天气预报数据----------------------------------------
# -------------------------------------1.1 通过地名和日期调取----------------------------------------
# 日期年月日参数，整型，须为近30日的日期，最新数据为当前日期，返回数据为设定日期起未来10日逐小时数据
year, month, day = 2025, 9, 26 

# 地名参数，目前收录全国3191个市区县，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
city_name = '西安市'

# 构造url，获取该城市该日期起，未来10日逐小时天气预报
forecast_city_url = f"https://htqx.cn/meteo/api/forecast/daily/{city_name}/{year}/{month}/{day}/{api_key}"
forecast_city_data = requests.get(forecast_city_url)
print(forecast_city_data.text)

# -------------------------------------1.2 通过地理坐标调取----------------------------------------
# 地理坐标经纬度参数
lon, lat = 108.940509, 34.617382

# 构造url，获取该坐标未来10日逐小时天气预报，如果需要查询确认坐标地名信息，参考第5点
forecast_coords_url = f"https://htqx.cn/meteo/api/forecast/daily_coords/{lon}/{lat}/{api_key}"
forecast_coords_data = requests.get(forecast_coords_url)
print(forecast_coords_data.text)

# -------------------------------------1.3 通过地名调取ECMWF滚动更新预报（推荐）----------------------------------------
# 无需日期参数，返回数据始终为最新
# 地名参数，目前收录全国3191个市区县，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
city_name = '西安市'

# 构造url，获取该城市未来10日逐小时天气预报
forecast_city_url = f"https://htqx.cn/meteo/api/forecast/ecmwf/location/{city_name}/{api_key}"
forecast_city_data = requests.get(forecast_city_url)
print(forecast_city_data.text)

# -------------------------------------1.4 通过地理坐标调取ECMWF滚动更新预报（推荐）----------------------------------------
# 地理坐标经纬度参数
lon, lat = 108.940509, 34.617382

# 构造url，获取该坐标最新未来10日逐小时天气预报，如果需要查询确认坐标地名信息，参考第5节
forecast_coords_url = f"https://htqx.cn/meteo/api/forecast/ecmwf/coords/{lon}/{lat}/{api_key}"
forecast_coords_data = requests.get(forecast_coords_url)
print(forecast_coords_data.text)

# -------------------------------------2.调取某日历史天气数据----------------------------------------
# 日期年月日参数，整型，须为2000年1月1日至今日之间的日期，历史天气数据更新有1个月左右的延迟，所以近1个月的数据可能无法调取
year, month, day = 2025, 3, 26 

# 地名参数，目前收录全国3191个市区县，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource_cities_list.csv）
city_name = '南京市'

# 构造url，获取该城市该日期内24个时次的历史天气数据
history_daily_url = f"https://htqx.cn/meteo/api/history/daily/{city_name}/{year}/{month}/{day}/{api_key}"
history_daily_data = requests.get(history_daily_url)
print(history_daily_data.text)

# -------------------------------------3.调取某月历史天气数据----------------------------------------
# 年月参数，整型，须为2000年1月至今日之间的月份，历史天气数据更新有1个月左右的延迟，所以近1个月的数据可能无法调取
year, month = 2025, 3

# 地名参数，目前收录全国3191个市区县，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
city_name = '成都市'

# 构造url，获取该城市该月份内720个时次的历史天气数据
history_monthly_url = f"https://htqx.cn/meteo/api/history/monthly/{city_name}/{year}/{month}/{api_key}"
history_monthly_data = requests.get(history_monthly_url)
print(history_monthly_data.text)


# -------------------------------------4.调取某年历史天气数据----------------------------------------
# 年份参数，整型，须为2000年至今日之间的年份，历史天气数据更新有10天左右的延迟，所以近10天的数据可能无法调取
year = 2025

# 地名参数，目前收录全国3191个市区县，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
city_name = '上海市'

# 构造url，获取该城市该年份内8760个时次的历史天气数据
history_yearly_url = f"https://htqx.cn/meteo/api/history/yearly/{city_name}/{year}/{api_key}"
history_yearly_data = requests.get(history_yearly_url)
print(history_yearly_data.text)

# -------------------------------------5.通过经纬度坐标查询地名信息----------------------------------------
# 地理坐标经纬度参数
lon, lat = 108.940509, 34.617382

# 构造url，获取该坐标关联的地名信息
coords_info_url = f"https://htqx.cn/meteo/api/gis/coords_location/{lon}/{lat}/{api_key}"
coords_info_data = requests.get(coords_info_url).json()
print(coords_info_data)

# -------------------------------------6.调取统计分析历史天气数据----------------------------------------

# 地名、时间类型参数，时间类型daily、monthly、yearly代表分别按日、月、年统计分析
city_name = '三原县'
time_type = 'daily'  # 'daily' 'monthly' 'yearly' 三选一

# 构造url，获取该地点日、月、年统计分析历史数据
history_analysis_url = f"https://htqx.cn/meteo/api/history_analysis/{time_type}/{city_name}/{api_key}/"
history_analysis_data = requests.get(history_analysis_url).json()
print(history_analysis_data)

# -------------------------------------7.调取历史空气质量数据----------------------------------------

# 地名、时间类型参数
city_name = '成都市'
year = '2025'  # 年份

# 构造url，获取该城市该年逐小时空气质量数据，包括AQI和污染物浓度
aqi_url = f"https://htqx.cn/meteo/api/aqi/yearly/{city_name}/{year}/{api_key}/"
aqi_data = requests.get(aqi_url).json()
print(history_analysis_data)

# -------------------------------------8.调取全国范围0.1°网格天气预报数据----------------------------------------
time = '2026062915'  # 时间标记，固定10位长度，代表2026年4月29日15时
meteo_type = 'temperature_2m'  # 气象要素类型，地面2米气温，可选气象要素见在线文档
grid_data_url = f"https://htqx.cn/meteo/api/forecast/grid/{time}/{meteo_type}/{api_key}"
grid_data = requests.get(grid_data_url).json()
# 返回网格经纬度坐标、全国范围0.1°分辨率网格数据（401×631二维数组，覆盖范围：15~55°N，72~136°E）
print(grid_data)

# -------------------------------------9.调取某地逐日天气预报摘要数据，时间跨度：未来10日----------------------------------------
city_name = '江宁区'
forecast_summary_url = f"https://htqx.cn/meteo/api/forecast/summary/{city_name}/{api_key}"
forecast_summary_data = requests.get(forecast_summary_url).json()
# 返回逐日天气预报摘要数据，日期（未来10日）、星期、气温、天气、降水量、气压、湿度、风力、风向、降水时间等
print(forecast_summary_data)
