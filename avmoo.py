#!/usr/bin/env python3

"""
利用爬取的代理IP，爬取avmoo.com的影片信息。存入mongodb。
"""

import re
import requests
from datetime import datetime

from bs4 import BeautifulSoup
from pymongo import MongoClient

client = MongoClient()
db = client.avmoo


def mid2int(mid):
    """
    将36进制字符串mid转换为10进制，1-9a-z
    :param mid:
    :return:
    """
    value = 0
    mid = mid.lower()
    length = len(mid)

    for i in range(len(mid)):
        c = mid[i]
        factor = int(c) if c.isdigit() else ord(c) - 97 + 10
        value += 36 ** (length - i - 1) * factor
    return value


def int2mid(value):
    """
    将10进制mid转换为36进制字符串，1-9a-z
    :param value:
    :return:
    """
    if value < 36:
        return str(value) if value < 10 else chr(value - 10 + 97)
    else:
        c = value % 36
        sub = int((value - c) / 36)
        c = str(c) if c < 10 else chr(c - 10 + 97)
        return '%s%s' % (int2mid(sub), c)


def safe_search(ptn, src, pair=False, integer=False):
    """
    search ptn in src, and return group search result
    :param ptn: 正则
    :param src: 数据源
    :param pair: 是否搜索一组数据，默认搜索一个
    :param integer: 是否搜索一个数字，默认字符串
    :return: 搜索的结果
    """
    m = re.search(ptn, src)
    if m:
        if pair:
            return m.group(1).strip(), m.group(2).strip()
        elif integer:
            return int(m.group(1))
        else:
            return m.group(1).strip()
    else:
        if pair:
            return '', ''
        elif integer:
            return -1
        else:
            return ''


def get_movie(mid, domain, https=True):
    """
    获取指定影片的全部信息
    参见 "https://www.avmoo.com/cn/movie/500"

    :param mid:  影片36进制id
    :param domain: 网站域名，如'www.avmoo.com'
    :param https: 默认使用https
    :return:
    """
    protocol = 'https' if https else 'http'
    ptn_server = '{:s}://{:s}/cn'.format(protocol, domain).replace('.', '\.')

    ptn_name = '<h3>(.*?)</h3>'
    ptn_fid = '<span class="header">识别码:</span> <span.*?>(.*?)</span>'

    ptn_time = '<p><span class="header">发行时间:</span>(.*?)</p>'
    ptn_length = '<p><span class="header">长度:</span> (\d+)分钟</p>'
    ptn_cover = '<a class="bigImage" href=".*?"><img src="(.*?)".*?></a>'

    ptn_director = '<a href="{:s}/director/(.*?)">(.*?)</a>'.format(ptn_server)
    ptn_studio = '<a href="{:s}/studio/(.*?)">(.*?)</a>'.format(ptn_server)
    ptn_label = '<a href="{:s}/label/(.*?)">(.*?)</a>'.format(ptn_server)
    ptn_series = '<a href="{:s}/series/(.*?)">(.*?)</a>'.format(ptn_server)
    ptn_genre = '<a href="{:s}/genre/(.*?)">(.*?)</a>'.format(ptn_server)

    ptn_sample = '<a class="sample-box.*?" href="(.*?)">'
    ptn_star = '{:s}/star/(.*)'.format(ptn_server)

    url = 'https://www.avmoo.com/cn/movie/{:s}'.format(mid)
    source = requests.get(url).text

    name = safe_search(ptn_name, source)  # 片名
    fid = safe_search(ptn_fid, source)  # 番号
    time = safe_search(ptn_time, source)  # 发行时间
    length = safe_search(ptn_length, source, integer=True)  # 片长，单位分钟
    cover = safe_search(ptn_cover, source)  # 大图URL

    director = safe_search(ptn_director, source, pair=True)  # (导演id, 导演名)
    studio = safe_search(ptn_studio, source, pair=True)  # (制作商id, 制作商名)
    label = safe_search(ptn_label, source, pair=True)  # (发行商id, 发行商名)
    series = safe_search(ptn_series, source, pair=True)  # (系列id， 系列名)

    genres = re.findall(ptn_genre, source)  # [(类别id, 类别名)...]
    samples = re.findall(ptn_sample, source)  # [样图URL...]

    stars = []
    soup = BeautifulSoup(source, 'lxml')
    for star in soup.find_all(name='a', class_='avatar-box'):
        sid = safe_search(ptn_star, star['href'])
        name = star.span.text.strip()
        stars.append({'id': sid, 'name': name})

    document = {
        'mid': mid,
        'fid': fid,
        'name': name.replace(fid, '').strip(),
        'time': time,  # datetime.strptime(time, "%Y-%m-%d"),
        'length': length,
        'cover': cover,

        'director': {
            'id': director[0],
            'name': director[1],
        },
        'studio': {
            'id': studio[0],
            'name': studio[1],
        },
        'label': {
            'id': label[0],
            'name': label[1],
        },
        'series': {
            'id': series[0],
            'name': series[1],
        },

        'genres': [
            {'id': genre[0], 'name': genre[1]} for genre in genres
            ],

        'stars': stars,
        'samples': samples
    }

    return document


if __name__ == '__main__':
    db.movie.insert_one(get_movie('5555', 'www.avmoo.com'))