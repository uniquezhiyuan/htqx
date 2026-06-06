# 海天气象官方标准Python库正式发布

为便于用户更加方便快捷获取历史天气数据和天气预报数据，海天气象开发团队近日完成海天气象数据信息服务平台（https://htqx.cn/）官方Python库开发测试并在Pypi平台发布，库名为HtMeteo，地址如下：https://pypi.org/project/HtMeteo/

现在用户可通过pip工具一键安装HtMeteo库：

`pip install HtMeteo`

借助HtMeteo库，用户可以脱离海天气象平台网页端获取站点气象数据，不再依赖人工查找、下载数据再进行统计分析，而是自动完成数据拉取到本地并自动处理分析，目前支持的气象数据包括以下内容：

1. 全国3191个市区县逐小时历史天气数据（2000年至今）
2. 全国3191市区县未来10日逐小时天气预报数据

如果对海天气象平台数据内容还不熟悉，可以通过数据开发文档（https://htqx.cn/meteo/doc/）了解。

以上数据包括气温、气压、相对湿度、风速风向、降水量、云量、能见度、天气现象、短波辐射、散射辐射、地面辐射、土壤温度、土壤湿度、大气边界层高度、参考蒸散量等40余种，时间分辨率均达到小时级。

通过HtMeteo库用户可依靠纯命令行实现以下功能：

1. 批量下载多个地点历史天气数据到本地
2. 批量下载多个地点天气预报数据到本地
3. 调取任意时段的历史天气数据
4. 调取任意时段的天气预报数据
5. 历史天气数据的统计分析（最大值、最小值、平均值、累积值）
6. 天气预报数据的统计分析（最大值、最小值、平均值、累积值）

该库可跨平台运行，同时支持Windows、Linux和OS X平台，通过HtMeteo库用户不再需要从网页端人工下载历史天气数据进行统计分析，HtMeteo已为用户封装了常用气象研究应用场景下的常见功能，示例如下：

* 获取西安市2024年6月的最高气温、平均相对湿度
* 获取上海市2014年至2025年的年平均气温
* 获取越秀区2018年9月12日到2019年4月9日的逐小时短波辐射
* 获取柳林县2008年5月至今的月累积降水量
* 获取北京市2010年12月的逐小时气压
* 获取武汉市未来10日逐小时降水预报
* 获取长沙市未来10日逐日最高和最低气温

以上示例简单呈现了HtMeteo库能调取哪些数据和实现哪些统计分析功能，总的来说它能够帮助用户快速**获取全国任意市区县的任意气象要素任意时间的原始数值和统计分析数值**，它的所有方法返回的数据类型均为pandas dataframe，如果内置的统计分析形式满足不了用户需求，用户可以至今调取原始数据自行完成统计分析。

如需使用HtMeteo库，仅需2行命令即可完成：

```python
from HtMeteo import HtMeteo

h = HtMeteo(username='test@htqx.cn', password='123456')  # 指定海天气象用户名和密码
```

以上2行命令可以导入HtMeteo库，通过设定用户名和密码来完成用户验证，然后即可实现上述所有数据拉取、处理、统计分析功能。

现在HtMeteo同时完善了海天气象数据信息服务平台数据批量下载功能，如需下载多个地点的历史天气数据，仅需如下2行命令即可实现：

```python
locations = ['南京市', '疏勒县', '顺德区', '大理白族自治州']
h.fetch_locations_data(locations)
```

第一行命令构建一个待下载历史天气数据的地名列表，第二行命令会将列表内所有地点的历史天气数据下载到本地，包括2000年至今的所有年份的逐小时历史天气数据和逐日、逐月、逐年的统计分析数据，运行以上命令之后，屏幕将会出现以下输出：

```python
顺德区 工作目录已创建：././data/history/顺德区
顺德区 2000 逐小时历史数据不存在。
顺德区 2001 逐小时历史数据不存在。
顺德区 2002 逐小时历史数据不存在。
顺德区 2003 逐小时历史数据不存在。
顺德区 2004 逐小时历史数据不存在。
顺德区 2005 逐小时历史数据不存在。
顺德区 2006 逐小时历史数据不存在。
顺德区 2007 逐小时历史数据不存在。
顺德区 2008 逐小时历史数据不存在。
顺德区 2009 逐小时历史数据不存在。
顺德区 2010 逐小时历史数据不存在。
顺德区 2011 逐小时历史数据不存在。
顺德区 2012 逐小时历史数据不存在。
顺德区 2013 逐小时历史数据不存在。
顺德区 2014 逐小时历史数据不存在。
顺德区 2015 逐小时历史数据不存在。
顺德区 2016 逐小时历史数据不存在。
顺德区 2017 逐小时历史数据不存在。
顺德区 2018 逐小时历史数据不存在。
顺德区 2019 逐小时历史数据不存在。
顺德区 2020 逐小时历史数据不存在。
顺德区 2021 逐小时历史数据不存在。
顺德区 2022 逐小时历史数据不存在。
顺德区 2023 逐小时历史数据不存在。
顺德区 2024 逐小时历史数据不存在。
顺德区 2025 逐小时历史数据不存在。
顺德区 2026 逐小时历史数据不存在。
顺德区 逐日历史数据不存在。
顺德区 逐月历史数据不存在。
顺德区 逐年历史数据不存在。
顺德区 天气预报数据不存在。
顺德区 数据存在缺失，现在开始从云端拉取缺失数据。
用户登录状态正常。
正在从云端拉取 顺德区 逐小时历史气象数据: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 27/27 [00:18<00:00,  1.48it/s]
顺德区 逐小时历史气象数据拉取完毕。
顺德区 逐日历史气象数据拉取完毕。
顺德区 逐月历史气象数据拉取完毕。
顺德区 逐年历史气象数据拉取完毕。
正在从云端拉取 顺德区 最新天气预报数据······
顺德区 今日天气预报数据拉取完毕。
任务进度：75.0%。已完成3个地点，共计4个。
```

所有历史天气数据`csv`文件将会被下载至`./data/temp/`目录，并被处理成为Parquet格式分类存放在`./data/history/`目录。

如果需要下载全国天气预报数据，则执行以下命令即可：

```python
h.fetch_all_latest_forecast_data()
```

全国所有3191个市区县的最新天气预报数据压缩文件会被下载至`./data/temp/`目录，并自动解压至`./data/forecast/`目录，文件格式均为`csv`，用户可以用Excel和文本查看软件直接打开查看或者编写程序处理。

`HeMeteo`库的所有属性和方法如下表所示：

| 属性/方法名称                         | 功能说明                             |
| --------------------------------------- | -------------------------------------- |
| 1.账户管理属性                        | —————————————————— |
|  account\_info                        | 详细的海天气象账户信息               |
|  username                             | 用户名                               |
|  password                             | 密码                                 |
|  account\_type                        | 账户类型                             |
|  api\_key                             | api\_key                             |
|  subscribe\_days                      | 订阅天数                             |
|  session                              | 连接会话                             |
| 2.数据调取属性                        | —————————————————— |
|  location                             | 当前设定地点                         |
|  locations                            | 地点列表                             |
|  history\_mode                        | 历史天气数据模式                     |
|  forecast\_mode                       | 天气预报数据模式                     |
|  years                                | 历史数据年份列表2000\~2025           |
| 3.工作目录属性                        | —————————————————— |
|  work\_dirs                           | 全部工作目录列表                     |
|  temp\_data\_path                     | 缓存目录                             |
|  hourly\_history\_meteo\_data\_path   | 逐小时统计分析数据目录               |
|  daily\_history\_meteo\_data\_path    | 逐日统计分析数据目录                 |
|  monthly\_history\_meteo\_data\_path  | 逐月统计分析数据目录                 |
|  yearly\_history\_meteo\_data\_path   | 逐年统计分析数据目录                 |
|  forecast\_data\_path                 | 预报数据目录                         |
| 4.账户管理方法                        | —————————————————— |
|  login\_account                       | 登录海天账户                         |
|  create\_work\_dirs                   | 创建所有工作目录                     |
|  set\_forecast\_mode                  | 设定天气预报数据模式                 |
|  set\_history\_mode                   | 设定历史天气数据模式                 |
|  set\_location                        | 设定地点                             |
| 5.数据拉取方法                        | —————————————————— |
|  data\_status\_check()                | 数据完整性校验                       |
|  fetch\_data()                        | 从云端拉取数据                             |
|  fetch\_locations\_data()             | 拉取多个地点数据                     |
|  fetch\_all\_latest\_forecast\_data() | 拉取全国城市天气预报数据             |
| 6.历史天气数据调取方法                | —————————————————— |
|  hourly\_value()                      | 调取某小时历史天气数据               |
|  daily\_value()                       | 调取某天统计分析历史天气数据         |
|  monthly\_value()                     | 调取某月统计分析历史天气数据         |
|  yearly\_value()                      | 调取某年统计分析历史天气数据         |
|  hourly\_series()                     | 调取起止小时时段统计分析历史天气数据 |
|  daily\_series()                      | 调取起止天时段统计分析历史天气数据   |
|  monthly\_series()                    | 调取起止月时段统计分析历史天气数据   |
|  yearly\_series()                     | 调取起止年时段年统计分析历史天气数据 |
| 7.天气预报数据调取方法                    | —————————————————— |
|  forecast\_hourly\_series()           | 调取未来10日逐小时天气预报数据       |
|  forecast\_daily\_series()            | 调取未来10日逐日统计分析天气预报数据 |
| 8.在线接口API使用                     | —————————————————— |
|  api\_history\_hourly\_of\_day()      | 仅查看某天的逐小时历史天气数据       |
|  api\_history\_hourly\_of\_month()    | 仅查看某月的逐小时历史天气数据       |
|  api\_history\_hourly\_of\_year()     | 仅查看某年的逐小时历史天气数据       |
|  api\_history\_analysis()             | 仅查看日、月、年统计分析历史天气数据 |
|  api\_forecast\_hourly()              | 仅查看某地点的逐小时天气预报数据     |
|  api\_forecast\_hourly\_by\_coords()  | 仅查看某坐标的逐小时天气预报数据     |
|  find\_location\_by\_coords()         | 查询某坐标的地名信息                 |
| 9.其他方法                            | —————————————————— |
|  clear\_data\_dir()                   | 清空工作目录内的所有数据             |

现在用户使用pip命令安装HeMeteo库之后可以在安装目录打开basic_usage.py文件查看所有的示例源代码，通过源代码详细的注释可以深入了解所有的用法。

```python
"""
海天气象HtMeteo超级信息体使用示例代码
海天气象HtMeteo超级信息体，是海天气象数据信息服务平台开发的，基于平台数据合集和在线API的Python程序库，它能够实现账户认证、气象数据下载、气象数据
统计分析、气象数据在线API调用等功能，将海天气象平台的所有数据资源和在线接口整合在了一个Python库中，因此形象被命名为“超级信息体”。
开发它的初衷是为了变革气象领域科研人员、应用人员、学生获取地面气象数据的方式，无论是历史天气数据还是天气预报数据，它能够最大限度减少气象数据用户在数据
查找、统计分析、整理订正、存储调取环节的时间耗费，一站式解决所有的科研任务和实践应用的数据准备问题，让用户不再受制于数据准备的羁绊，从而专注于对
气象数据的潜能开发和价值创造。
在线支持：https://htqx.cn/meteo/doc
"""
from HtMeteo import HtMeteo

# DATA_DIR = './'  # 手动指定数据存放目录，若不指定则存放在程序运行当前目录
# -------------------------基本参数-------------------------
location = '西安市'
# locations = ['北京市', '三原县', '喀什地区', '贡山独龙族怒族自治县', '海北藏族自治州']
meteo_types = ['temperature_2m_max',  # 最高2米气温
               'surface_pressure_mean',  # 平均地面气压
               'relative_humidity_2m_mean',  # 平均地面2米相对湿度
               'wind_speed_10m_mean',  # 平均10米风速
               'precipitation_sum',  # 累积降水量
               'shortwave_radiation_min']  # 最小短波辐射
# meteo_types 所有可选参数在文档末尾

target_year, target_month, target_day, target_hour = 2019, 4, 20, 18

start_year, start_month, start_day, start_hour = 2019, 12, 25, 18
end_year, end_month, end_day, end_hour = 2020, 3, 26, 18

# -------------------------用户认证 示例代码-------------------------
# 初始化HtMeteo超级信息体
h = HtMeteo(username='test@htqx.cn', password='123456')  # 指定海天气象用户名和密码，实例化超级信息体
# h = HtMeteo()  # 不指定用户名和密码，无法拉取在线数据，只能分析本地数据
h.login_account()  # 通过用户名和密码登录海天气象
print(h.account_info)  # 查看账户信息
print(h.username, h.password, h.api_key, h.account_type, h.subscribe_days)  # 分别查看用户名、密码、api_key、用户类型、订阅时间
# time.sleep(1000)
# -------------------------历史天气数据统计分析 示例代码-------------------------
h.set_location('西安市')  # 设定地点，会自动检测目录数据状态，如果数据缺失会自动从云端拉取，默认只拉区历史数据，如果需要预报数据需开启预报模式
# 1.获取单一时间历史气象数据，
# 读取西安市2019年4月20日18时历史气象数据，包含气象要素：2米气温、平均地面气压、平均2米相对湿度、10米平均风速、累积降水量和短波辐射
# 可以指定meteo_types参数改变气象要素类型，所有的历史气象要素列表在文档末尾，meteo_types是一个列表
# meteo_types = history_meteo_types_options  # 指定所有气象要素
h.hourly_value(meteo_types=meteo_types, year=target_year, month=target_month, day=target_day, hour=target_hour)

# 返回pandas series类型，可以通过气象要素名称索引
meteo_data = h.hourly_value(meteo_types=meteo_types, year=target_year, month=target_month, day=target_day,
                            hour=target_hour)
print(meteo_data['temperature_2m'])  # 输出2米气温数值
print(meteo_data.index)  # 查看所有索引

# 读取西安市2019年4月20日历史气象数据，气象要素包括最高2米气温、平均地面气压、平均地面2米相对湿度、平均10米风速、累积降水量、最小短波辐射
h.daily_value(meteo_types=meteo_types, year=2019, month=4, day=20)

# 读取西安市2019年4月历史气象数据，气象要素包括最高2米气温、平均地面气压、平均地面2米相对湿度、平均10米风速、累积降水量、最小短波辐射
h.monthly_value(meteo_types=meteo_types, year=2019, month=4)

# 读取西安市2019年历史气象数据，气象要素包括最高2米气温、平均地面气压、平均地面2米相对湿度、平均10米风速、累积降水量、最小短波辐射
h.yearly_value(meteo_types=meteo_types, year=2019)

# 2.获取时间段内连续历史气象数据，气象要素包括最高2米气温、平均地面气压、平均地面2米相对湿度、平均10米风速、累积降水量、最小短波辐射
# 读取西安市2019年12月31日0时至2020年1月1日23时历史气象数据
h.hourly_series(meteo_types=meteo_types,
                start_year=2019, start_month=12, start_day=31, start_hour=0,
                end_year=2020, end_month=1, end_day=1, end_hour=23)  # 起止时间都包含，可跨年读取
# 返回pandas dataframe，可以通过时间、气象要素名称索引
meteo_data = h.hourly_series(meteo_types=meteo_types,
                             start_year=2019, start_month=12, start_day=31, start_hour=0,
                             end_year=2020, end_month=1, end_day=1, end_hour=23)
print(meteo_data['temperature_2m'].iloc[0])  # 输出第一个2米气温数值
print(meteo_data['wind_speed_10m'].iloc[-5:].tolist())  # 输出最后5个10米平均风速数值，并转换为列表
print(meteo_data.index)  # 查看所有索引
print(meteo_data.columns)  # 查看所有列名

# 读取西安市2019年12月31日至2020年1月1日历史气象数据
h.daily_series(meteo_types=meteo_types,
               start_year=2019, start_month=12, start_day=31,
               end_year=2020, end_month=1, end_day=1)  # 起止时间都包含，可跨年读取

# 读取西安市2019年12月31日至2020年1月1日历史气象数据
h.monthly_series(meteo_types=meteo_types,
                 start_year=2019, start_month=12,
                 end_year=2020, end_month=1)  # 起止时间都包含，可跨年读取

# 读取西安市2019年至2025年历史气象数据
h.yearly_series(meteo_types=meteo_types,
                start_year=2019,
                end_year=2025)  # 起止时间都包含，可跨年读取

# -------------------------天气预报数据统计分析 示例代码-------------------------
# 3.读取预报数据
h.set_forecast_mode('on')  # 开启预报模式，预报模式默认为关闭，开启后方能使用预报数据读取功能，如果关闭不会下载天气预报数据
h.set_history_mode('off')  # 如果不使用历史数据，可以先关闭它，否则设定地点后，历史数据也会被自动下载，耗费时间
h.set_location('三原县')
# 读取三原县未来240小时逐小时天气预报原始数据
h.forecast_hourly_series()
meteo_data = h.forecast_daily_series()
print(meteo_data.columns)  # 查看所有气象要素名称

# 读取三原县未来10日逐日天气预报统计分析数据
h.forecast_daily_series()
meteo_data = h.forecast_daily_series()
print(meteo_data.columns)  # 查看所有气象要素名称

# 4.只想下载数据，或者关注的地点较多，想先下载完数据再读取处理以节省时间
locations = ['南京市', '疏勒县', '顺德区', '大理白族自治州']
h.set_forecast_mode('on')  # 开启预报数据模式，若关闭则不会下载预报数据
h.set_history_mode('on')  # 开启历史数据模式，否则不会下载历史数据
# 如果不设定历史数据模式或者预报数据模式，则只下载历史数据，因为预报数据模式默认为关闭状态

# 批量下载多个地点的天气预报数据和历史天气数据
h.fetch_locations_data(locations)

# 5.批量下载全国3191个市区县预报数据3191
h.fetch_all_latest_forecast_data()

# 6.需要查询经纬度所在地名和海拔
lon, lat = 116, 40
h.find_location_by_coords(lon, lat)
location_name = h.find_location_by_coords(lon, lat)  # 将查询到的坐标地点名称赋值给location_name
print(location_name)  # 输出"门头沟区"

# -------------------------在线API 示例代码-------------------------
# 7.直接从API调取数据，不再下载数据到本地
h.set_forecast_mode('off')  # 关闭预报数据模式，不再从云端下载数据到本地，直接API调取
h.set_history_mode('off')  # 关闭历史数据模式，不再从云端下载数据到本地，直接API调取
# 通过地名调取未来10日逐小时天气预报数据
meteo_data = h.api_forecast_hourly()  # 从API直接调取西安市未来10日逐小时天气预报数据
print(meteo_data.index)  # 输出时间索引
print(meteo_data.columns)  # 输出气象要素列表

# 通过经纬度坐标调取未来10日逐小时天气预报数据
lon, lat = 116, 40
meteo_data = h.api_forecast_hourly_by_coords(lon, lat)  # 从API直接调取西安市未来10日逐小时天气预报数据
print(meteo_data.index)  # 输出时间索引
print(meteo_data.columns)  # 输出气象要素列表

# 调取某一天的逐小时历史天气数据
year, month, day = 2019, 4, 20
meteo_data = h.api_history_hourly_of_day(year, month, day)  # 从API直接调取西安市2019年4月20日的逐小时历史天气数据
print(meteo_data.index)  # 输出时间索引
print(meteo_data.columns)  # 输出气象要素列表

# 调取某一月的逐小时历史天气数据
year, month = 2019, 4
meteo_data = h.api_history_hourly_of_month(year, month)  # 从API直接调取西安市2019年4月的逐小时历史天气数据
print(meteo_data.index)  # 输出时间索引
print(meteo_data.columns)  # 输出气象要素列表

# 调取某一年的逐小时历史天气数据
year = 2019
meteo_data = h.api_history_hourly_of_year(year)  # 从API直接调取西安市2019年的逐小时历史天气数据
print(meteo_data.index)  # 输出时间索引
print(meteo_data.columns)  # 输出气象要素列表

# 调取2000~2025年全时段统计分析历史天气数据
time_type = 'monthly'  # 'daily''monthly''yearly' 三选一，分别代表日、月、年尺度的统计分析数据
meteo_data = h.api_history_analysis(time_type)  # 从API直接调取西安市2000~2025年的月统计分析历史天气数据
print(meteo_data.index)  # 输出时间索引
print(meteo_data.columns)  # 输出气象要素列表


# 8.其他功能
# h.clear_work_dirs()  # 清空./data目录内的所有数据，重置工作目录，谨慎操作

# 9.注意事项
# 全国有大约30个区名重复，冠以所在市名称加以区分，全国市区县地名清单下载地址：https://htqx.cn/meteo/doc
```
