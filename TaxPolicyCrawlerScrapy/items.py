# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class TaxpolicycrawlerscrapyItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class PolicyItem(scrapy.Item):
    title = scrapy.Field()  # 标题: 国家税务总局关于卷烟消费税计税价格核定管理有关问题的公告
    subtitle = scrapy.Field()  # 副标题：国家税务总局公告2017年第32号
    date = scrapy.Field()  # 发文日期
    content = scrapy.Field()  # 正文内容
    publisher = scrapy.Field()  # 发文部门
    url = scrapy.Field()  # 链接地址
    md5 = scrapy.Field()  # md5判断是否重复


class PolicySource(scrapy.Item):
    source = scrapy.Field()         # 政策来源: 国税总局、各省市区税务局
    policyType = scrapy.Field()     # 政策类型：税收法规库、政策解读、与外国的税收条约
    taxLevel = scrapy.Field()       # 税种：国税、地税