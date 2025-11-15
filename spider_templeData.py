import requests
from lxml import etree
import time
import csv
import os
from pymysql import *

# 数据库配置
# DB_CONFIG = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': '你的密码',
#     'database': 'douban',
#     'charset': 'utf8mb4'
# }

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}


def get_first_text(lst):
    """安全获取列表中的第一个元素"""
    try:
        return lst[0].strip()
    except:
        return ""


# def init_database():
#     """初始化数据库"""
#     try:
#         conn = connect(**DB_CONFIG)
#         cursor = conn.cursor()
#         sql = '''
#             CREATE TABLE IF NOT EXISTS movie(
#                 id INT PRIMARY KEY AUTO_INCREMENT,
#                 directors VARCHAR(255),
#                 title VARCHAR(255),
#                 casts VARCHAR(255),
#                 cover VARCHAR(255),
#                 detailLink VARCHAR(255),
#                 year VARCHAR(255),
#                 types VARCHAR(255),
#                 country VARCHAR(255),
#                 lang VARCHAR(255),
#                 time VARCHAR(255),
#                 moveiTime VARCHAR(255),
#                 commment_len VARCHAR(255),
#                 starts VARCHAR(255),
#                 summary VARCHAR(255),
#                 comments VARCHAR(255),
#                 imgList VARCHAR(255),
#                 movieUrl VARCHAR(255)
#             )
#         '''
#         cursor.execute(sql)
#         conn.commit()
#         cursor.close()
#         conn.close()
#         print("数据库表创建成功！")
#     except Exception as e:
#         print(f"数据库错误: {e}")
#
#
# def save_to_database(movie_data):
#     """保存数据到数据库"""
#     try:
#         conn = connect(**DB_CONFIG)
#         cursor = conn.cursor()
#         sql = '''
#             INSERT INTO movie (directors, title, casts, cover, detailLink, year, types, country, commment_len, starts, summary, imgList, movieUrl)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         '''
#         cursor.execute(sql, (
#             movie_data['director'],
#             movie_data['title'],
#             movie_data['casts'],
#             movie_data['cover'],
#             movie_data['detailLink'],
#             movie_data['year'],
#             movie_data['types'],
#             movie_data['country'],
#             movie_data['commment_len'],
#             movie_data['starts'],
#             movie_data['summary'],
#             movie_data['imgList'],
#             movie_data['movieUrl']
#         ))
#         conn.commit()
#         cursor.close()
#         conn.close()
#         print(f"成功保存到数据库: {movie_data['title']}")
#     except Exception as e:
#         print(f"保存到数据库错误: {e}")


# 生成所有页面的URL
urls = ['https://movie.douban.com/top250?start={}&filter='.format(str(i * 25)) for i in range(10)]
total_count = 1  # 全局计数器，从1开始

# 初始化数据库
# init_database()

# 创建CSV文件
if not os.path.exists('./tempData.csv'):
    with open("./tempData.csv", 'w', newline='', encoding='utf-8') as writer_f:
        writer = csv.writer(writer_f)
        writer.writerow(
            ['director', 'title', 'casts', 'cover', 'detailLink', 'year', 'types', 'country', 'commment_len', 'starts',
             'summary', 'imgList', 'movieUrl'])

for url in urls:
    print(f"正在爬取: {url}")

    # 发送请求
    response = requests.get(url, headers=headers)
    html = response.text

    # 解析HTML
    parser = etree.HTMLParser(encoding='utf-8')
    tree = etree.HTML(html, parser=parser)

    # 获取所有电影列表项
    lis = tree.xpath('//ol[@class="grid_view"]/li')

    print(f"本页找到 {len(lis)} 个电影")

    # 解析本页数据
    for li in lis:
        # 提取电影标题
        title = get_first_text(li.xpath('.//span[@class="title"][1]/text()'))

        # 提取电影链接
        src = get_first_text(li.xpath('.//div[@class="hd"]/a/@href'))

        # 提取导演和演员信息
        director_info = get_first_text(li.xpath('.//div[@class="bd"]/p[1]/text()'))

        # 提取年份、国家、类型
        year_info = get_first_text(li.xpath('.//div[@class="bd"]/p[1]/text()[2]'))

        # 提取评分
        score = get_first_text(li.xpath('.//span[@class="rating_num"]/text()'))

        # 提取评价人数
        comment = get_first_text(li.xpath('.//div[@class="star"]/span[4]/text()'))

        # 提取简介
        summary = get_first_text(li.xpath('.//span[@class="inq"]/text()'))

        # 提取图片
        img_src = get_first_text(li.xpath('.//img/@src'))

        # 处理导演和演员信息
        director = ""
        casts = ""
        if "导演:" in director_info and "主演:" in director_info:
            parts = director_info.split("主演:")
            director = parts[0].replace("导演:", "").strip()
            casts = parts[1].strip()
        elif "导演:" in director_info:
            director = director_info.replace("导演:", "").strip()
            casts = "未知"
        else:
            director = director_info
            casts = "未知"

        # 处理年份、国家、类型
        year = country = types = ""
        if year_info:
            parts = year_info.split('/')
            if len(parts) >= 3:
                year = parts[0].strip()
                country = parts[1].strip()
                types = parts[2].strip()

        # 处理评价人数
        commment_len = "0"
        if comment and "人评价" in comment:
            commment_len = comment.replace("人评价", "").strip()

        # 构建电影数据字典
        movie_data = {
            'director': director,
            'title': title,
            'casts': casts,
            'cover': img_src,
            'detailLink': src,
            'year': year,
            'types': types,
            'country': country,
            'commment_len': commment_len,
            'starts': score,
            'summary': summary,
            'imgList': img_src,
            'movieUrl': src
        }

        print(f"{total_count}. {title} | 评分:{score} | 导演:{director}")

        # 保存到CSV
        with open("./tempData.csv", 'a', newline='', encoding='utf-8') as writer_f:
            writer = csv.writer(writer_f)
            writer.writerow([
                movie_data['director'],
                movie_data['title'],
                movie_data['casts'],
                movie_data['cover'],
                movie_data['detailLink'],
                movie_data['year'],
                movie_data['types'],
                movie_data['country'],
                movie_data['commment_len'],
                movie_data['starts'],
                movie_data['summary'],
                movie_data['imgList'],
                movie_data['movieUrl']
            ])

        # 保存到数据库
        # save_to_database(movie_data)

        total_count += 1

    # 添加延时，避免请求过快被封IP
    time.sleep(2)

print(f"\n爬取完成！总共爬取了 {total_count - 1} 部电影")