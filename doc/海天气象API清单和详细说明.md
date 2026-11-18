# 海天气象API清单和详细说明 （V2.1.3）

## 一、API清单和详细说明

海天气象数据信息服务平台（[https://cornicelli.net/](https://cornicelli.net/)）现已发布2.1.3版本API清单，用户可根据需要在线调用。
气象数据调取API共分为3大类：

- 天气预报类
- 历史天气类
- 地理信息查询类

所有专业用户均已开放使用，同时已加入Python SDK支持，用户可以快速构建url在WEB应用或本地程序中快速调取到需要的气象数据资源。

### 1.在线API清单

截止目前V2.1.3版本，共有以下7项API提供调用查询接口：

1. 某日某地天气预报查询
2. 某坐标最新天气预报查询
3. 某日某地历史天气查询
4. 某月某地历史天气查询
5. 某年某地历史天气查询
6. 统计分析历史天气数据查询
7. 坐标地名信息查询

以上7种API对应的示例url如下：

1. https://htqx.cn/meteo/api/forecast/daily/西安市/2019/4/10/eud84jnf95jr75l3ys7dnr84jd
2. https://htqx.cn/meteo/api/forecast/daily_coords/116.213/40.214/eud84jnf95jr75l3ys7dnr84jd
3. https://htqx.cn/meteo/api/history/daily/西安市/2019/4/10/eud84jnf95jr75l3ys7dnr84jd
4. https://htqx.cn/meteo/api/history/monthly/西安市/2019/4/eud84jnf95jr75l3ys7dnr84jd
5. https://htqx.cn/meteo/api/history/yearly/西安市/2019/eud84jnf95jr75l3ys7dnr84jd
6. https://htqx.cn/meteo/api/history_analysis/daily/西安市/eud84jnf95jr75l3ys7dnr84jd/
7. https://htqx.cn/meteo/api/gis/coords_location/116.213/40.214/eud84jnf95jr75l3ys7dnr84jd

### 2.API详细参数说明

API可以嵌入WEB应用或本地程序中灵活使用，是一种轻量化的数据获取方式，适用于小规模数据获取和本地存储资源受限的使用场景。所有API调取数据均需要提供26位`API_KEY`参数，可在个人中心查看用户账户对应的`API_KEY`。目前开放的7种API功能和参数对比如下：

| API名称                  | API参数                       | 主要功能                                     | 返回数据说明                                           |
| -------------------------- | ------------------------------- | ---------------------------------------------- | -------------------------------------------------------- |
| 某日某地天气预报查询     | 城市名称、年、月、日、API Key | 查询该地点选定日期未来10日逐小时气象预报数据 | 选定日期至未来10天内240个时次32种气象要素数据          |
| 某坐标最新天气预报查询   | 坐标经度、坐标纬度、API Key   | 查询该坐标地点最新未来10日逐小时气象预报数据 | 该坐标未来10天内240个时次32种气象要素数据              |
| 某日某地历史天气查询     | 城市名称、年、月、日、API Key | 查询该地点选定日期逐小时历史气象数据         | 选定日期当日的24个时次40种气象要素历史数据             |
| 某月某地历史天气查询     | 城市名称、年、月、API Key     | 查询该地点选定月份逐小时历史气象数据         | 选定月份当月的720个时次40种气象要素历史数据            |
| 某年某地历史天气查询     | 城市名称、年、API Key         | 查询该地点选定年份逐小时历史气象数据         | 选定年份当年的8760个时次40种气象要素历史数据           |
| 坐标地名信息查询         | 坐标经度、坐标纬度、API Key   | 查询该坐标的关联地名信息                     | 坐标最近的区县名称和所在省、市以及和最近区县的大圆距离 |
| 统计分析历史天气数据查询 | 地名、时间类型、API Key       | 查询该地点的年、月、日统计分析数据           | 该地点2000\~2025年全部逐年、逐月、逐日统计分析数据     |

### 3.API示例源代码

```python
import requests

# api主要提供以下5个接口，其中1个用于调取天气预报数据，3个用于调取历史天气数据，1个用于查询坐标信息
# 1.调取某日天气预报数据，时间跨度：选定日期起未来10日，共240小时（通过地名和坐标两种方式）
# 2.调取某日历史天气数据，时间跨度：选定日期的当日，共24小时
# 3.调取某月历史天气数据，时间跨度：选定年月的当月，共30日720小时
# 4.调取某年历史天气数据，时间跨度：选定年的当年，共12月365日8760小时
# 5.通过坐标查询地名信息
# 6.调取统计分析历史天气数据，全国市区县逐年、逐月、逐日的统计分析数据，包括均值、极值、累积值

# API Key可以在“个人中心”页面查看，所有用户都有API Key但是仅专业用户可以使用API功能，所有接口都需要API Key
api_key = "您的26位API Key"

# -------------------------------------1.调取某日天气预报数据----------------------------------------
# -------------------------------------1.1 通过地名和日期调取----------------------------------------
# 日期年月日参数，整型，须为近30日的日期
year, month, day = 2025, 9, 26 

# 地名参数，目前收录全国333个地级市，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
city_name = '西安市'

# 构造url，获取该城市该日期起，未来10日逐小时天气预报
forecast_daily_url = f"https://htqx.cn/meteo/api/forecast/daily/{city_name}/{year}/{month}/{day}/{api_key}"
forecast_daily_data = requests.get(forecast_daily_url)
print(forecast_daily_data.text)

# -------------------------------------1.2 通过地理坐标调取----------------------------------------
# 地理坐标经纬度参数
lon, lat = 108.940509, 34.617382

# 构造url，获取该坐标未来10日逐小时天气预报，如果需要查询确认坐标地名信息，参考第5点
forecast_coords_url = f"https://htqx.cn/meteo/api/forecast/daily_coords/{lon}/{lat}/{api_key}"
forecast_coords_data = requests.get(forecast_coords_url)
print(forecast_coords_data.text)

# -------------------------------------2.调取某日历史天气数据----------------------------------------
# 日期年月日参数，整型，须为2000年1月1日至今日之间的日期，历史天气数据更新有1个月左右的延迟，所以近1个月的数据可能无法调取
year, month, day = 2025, 3, 26 

# 地名参数，目前收录全国333个地级市，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource_cities_list.csv）
city_name = '南京市'

# 构造url，获取该城市该日期内24个时次的历史天气数据
history_daily_url = f"https://htqx.cn/meteo/api/history/daily/{city_name}/{year}/{month}/{day}/{api_key}"
history_daily_data = requests.get(history_daily_url)
print(history_daily_data.text)

# -------------------------------------3.调取某月历史天气数据----------------------------------------
# 年月参数，整型，须为2000年1月至今日之间的月份，历史天气数据更新有1个月左右的延迟，所以近1个月的数据可能无法调取
year, month = 2025, 3

# 地名参数，目前收录全国333个地级市，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
city_name = '成都市'

# 构造url，获取该城市该月份内720个时次的历史天气数据
history_monthly_url = f"https://htqx.cn/meteo/api/history/monthly/{city_name}/{year}/{month}/{api_key}"
history_monthly_data = requests.get(history_monthly_url)
print(history_monthly_data.text)


# -------------------------------------4.调取某年历史天气数据----------------------------------------
# 年份参数，整型，须为2000年至今日之间的年份，历史天气数据更新有1个月左右的延迟，所以近1个月的数据可能无法调取
year = 2025

# 地名参数，目前收录全国333个地级市，城市列表请在说明文档中下载查看（https://htqx.cn/meteo/download/resource/cities_list.csv）
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

# 构造url，获取该坐标关联的地名信息
history_analysis_url = f"https://htqx.cn/meteo/api/history_analysis/{time_type}/{city_name}/{api_key}/"
history_analysis_data = requests.get(history_analysis_url).json()
print(history_analysis_data)
```

### 4.气象要素分类、定义和详细说明

天气预报数据和历史天气数据共分为气温、气压、相对湿度、风、降水量、云、能见度、天气现象等13大类，其中天气预报数据一共有32种，历史天气数据一共有40种，覆盖了科研领域的绝大多数地面气象数据使用场景。

![气象要素种类思维导图](https://github.com/uniquezhiyuan/htqx/blob/main/figures/%E6%B0%94%E8%B1%A1%E8%A6%81%E7%B4%A0.png)
可通过查找下表迅速找到对应的气象要素名称和定义：

| 字段名                              | 物理名称     | 单位  | 定义和描述                                                                                         |
| ------------------------------------- | -------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| date                                | 时间         | 时    | 数据的时间标记。默认采用UTC+8时间(北京时间)。                                                      |
| temperature\_2m                     | 气温         | ℃    | 距地面2米高度的气温。                                                                              |
| relative\_humidity\_2m              | 相对湿度     | %     | 距地面2米高度的空气相对湿度。                                                                      |
| dew\_point\_2m                      | 露点温度     | ℃    | 距地面2米高度的空气露点温度。                                                                      |
| apparent\_temperature               | 体感温度     | ℃    | 指将人体所感受到的冷暖程度，转换成同等之温度。体感温度会受到气温、风速与相对湿度的综合影响。       |
| precipitation                       | 降水量       | mm    | 一定时间内，降落到水平面上，假如无渗漏，不流失，也不蒸发，累积起来的水的深度。                     |
| rain                                | 降水量       | mm    | 大尺度天气系统所引发的降水量。                                                                     |
| showers                             | 降水量       | mm    | 中小尺度对流天气系统所引发的降水量。                                                               |
| snowfall                            | 降雪量       | cm    | 一定持续时间（1小时）内累积降雪的深度。大约为降水量的7倍。                                         |
| snow\_depth                         | 雪深         | m     | 当前时刻地面积雪深度。                                                                             |
| weather\_code                       | 天气现象     |   无 | WMO定义的天气现象代码（详见下文）。                                                                |
| pressure\_msl                       | 海平面气压   | hPa   | 温度15摄氏度条件下，由本站气压推算到平均海平面上的气压值。                                         |
| surface\_pressure                   | 气压         | hPa   | 本站气压或场面气压，地表气压值。                                                                   |
| cloud\_cover                        | 总云量       | %     | 天空高、中、低云覆盖率。                                                                           |
| cloud\_cover\_low                   | 低云量       | %     | 天空低云覆盖率。                                                                                   |
| cloud\_cover\_mid                   | 中云量       | %     | 天空中云覆盖率。                                                                                   |
| cloud\_cover\_high                  | 高云量       | %     | 天空高云覆盖率。                                                                                   |
| visibility                          | 能见度       | m     | 地面水平可视距离。                                                                                 |
| dew\_point\_2m                      | 露点温度     | ℃    | 距地面2米高度的空气露点温度。                                                                      |
| et0\_fao\_evapotranspiration        | 蒸发量       | mm    | 持续时间内（1小时内）地表蒸发的水量。                                                              |
| vapour\_pressure\_deficit           | 水汽压差     | kPa   | 饱和水汽压与实际水汽压差值。                                                                       |
| wind\_speed\_10m                    | 平均风速     | m/s   | 地面10米高度平均风速。                                                                             |
| wind\_direction\_10m                | 风向         | °    | 地面10米高度风向。                                                                                 |
| wind\_gusts\_10m                    | 阵风风速     | m/s   | 地面10米高度阵风风速。                                                                             |
| surface\_temperature                | 地表温度     | ℃    | 地面温度，即地温。                                                                                 |
| soil\_moisture\_0\_to\_10cm         | 土壤温度     | ℃    | 地下0\~10厘米厚度层平均温度。                                                                      |
| cape                                | 对流有效位能 | J/kg  | CAPE,评估垂直大气是否稳定、对流是否容易发展的指标之一。                                            |
| lifted\_index                       | 抬升指数     |       | LI，自由对流高度以上不稳定能量大小的指数。                                                         |
| convective\_inhibition              | 对流抑制能   | J/kg  | CIN，阻止气块自地面上升至自由对流高度的能量大小。                                                  |
| shortwave\_radiation\_instant       | 短波辐射     | W/m² | 波长短于3μm的太阳辐射。                                                                           |
| direct\_radiation\_instant          | 直接短波辐射 | W/m² | 未被大气阻挡而能够直达到地面的太阳短波辐射。                                                       |
| diffuse\_radiation\_instant         | 散射辐射     | W/m² | 太阳光经大气层中的空气分子、云滴和气溶胶的散射作用(天空散射)以及地表漫反射(地面散射)等形成的辐射。 |
| direct\_normal\_irradiance\_instant | 直接辐射     | W/m² | DNI，未被大气阻挡而能够直达到地面的辐射。                                                          |
| global\_tilted\_irradiance\_instant | 倾角辐射     | W/m² | 特定倾斜面上接收到的直接辐射(DNI)和散射辐射(DHI)之和。                                             |
| terrestrial\_radiation\_instant     | 地面辐射     | W/m² | 短波辐射和长波辐射之和，由地球本身的辐射和太阳辐照后的反射组成的辐射。                             |

在统计分析历史天气数据API返回数据中中，以上气象要素名称后缀会加上`_max`、`_min`、_mean、`_sum`、`_average`，分别代表对应时间尺度的对应气象要素的最大值、最小值、平均值、累积值和均值，其中 `_average`是平均风向特有的后缀。

### 5.天气现象代码对照表

以下是WMO定义的天气现象代码`（weather_code）`及其对应的详细说明：

| 天气代码 | 天气现象   | 描述                                              |
| ------ | ------------ | --------------------------------------------------- |
| 0    | 晴         | 晴朗天气，无天气现象。                            |
| 1    | 大部晴     | 天空主要为晴朗天气。                              |
| 2    | 多云       | 局部为多云甜腻去。                                |
| 3    | 阴         | 云量95%以上。                                     |
| 45   | 雾         | 雾。                                              |
| 48   | 雾凇       | 雾凇。                                            |
| 51   | 小细雨     | 细雨。雨滴直径0.5毫米以下。                       |
| 53   | 中细雨     | 细雨。雨滴直径0.5毫米以下。                       |
| 55   | 大细雨     | 细雨。雨滴直径0.5毫米以下。                       |
| 56   | 轻度冻细雨 | 冻雨。雨滴直径0.5毫米以下。                       |
| 57   | 重度冻细雨 | 冻雨。雨滴直径0.5毫米以下。                       |
| 61   | 小雨       | 24小时累积降水量10毫米以下。雨滴直径0.5毫米以上。 |
| 63   | 中雨       | 24小时累积降水量10\~25毫米。雨滴直径0.5毫米以上。 |
| 65   | 大雨       | 24小时累积降水量25\~50毫米。雨滴直径0.5毫米以上。 |
| 66   | 轻度冻雨   | 雨滴直径0.5毫米以上。                             |
| 67   | 重度冻雨   | 雨滴直径0.5毫米以上。                             |
| 71   | 小雪       | 24小时累积降水量0.1\~2.4毫米。                    |
| 73   | 中雪       | 24小时累积降水量2.4\~4.9毫米。                    |
| 75   | 大雪       | 24小时累积降水量5.0\~9.9毫米。                    |
| 77   | 霰         | 雪粒。                                            |
| 80   | 小阵雨     | 阵雨。                                            |
| 81   | 中阵雨     | 阵雨。                                            |
| 82   | 大阵雨     | 阵雨。                                            |
| 85   | 小阵雪     | 阵雪。                                            |
| 86   | 大阵雪     | 阵雪。                                            |
| 95   | 雷暴       | 小型或大型雷暴。                                  |
| 96   | 小冰雹雷暴 | 伴随冰雹的小型雷暴。                              |
| 99   | 大冰雹雷暴 | 伴随冰雹的大型雷暴。                              |

