# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CourseItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    code = scrapy.Field()
    name = scrapy.Field()
    sess = scrapy.Field()
    form = scrapy.Field()    
    time = scrapy.Field()
    venue = scrapy.Field()
    stat = scrapy.Field()
    day = scrapy.Field()
    credit = scrapy.Field()
