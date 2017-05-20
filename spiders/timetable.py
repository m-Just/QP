# -*- coding: utf-8 -*-
import re, json

import scrapy

class TimetableSpider(scrapy.Spider):
    name = 'timetable'
    allowed_domains = ["cusis.cuhk.edu.hk"]
    start_urls = (
        'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/SA_LEARNER_SERVICES.SSR_SSENRL_LIST.GBL',
    )

    def __init__(self, category=None, *args, **kwargs):
        self.username = args[0]
        self.password = args[1]
        self.term = args[2]
        super(TimetableSpider, self).__init__(self)

    def start_requests(self):
        return [scrapy.Request(
            self.start_urls[0],
            dont_filter = True,
            callback = self.login,
        )]

    def login(self, response):
        return scrapy.FormRequest.from_response(
            response,
            formdata = {
                'timezoneOffset': '-480',
                'userid': self.username,
                'pwd': self.password,
            },
            dont_filter = True,
            callback = self.select_term,
        )

    def get_term_index(self, response):
        table = response.xpath("//table[@id='SSR_DUMMY_RECV1$scroll$0']")
        for tr in table.xpath(".//tr")[2:]:
            m = re.search(self.term, tr.xpath("./td")[1].xpath("./span")[0].extract())
            if not m == None:
                return tr.xpath("./td")[0].xpath("./input/@value").extract()
        return '-1'

    def select_term(self, response):
        term_selected = self.get_term_index(response)
        if term_selected == '-1':
            print "Error: Could not get term index"
        else:
            print "Term selected: " + self.term
        return scrapy.FormRequest.from_response(
            response,
            formdata = {
                'ICAction': 'DERIVED_SSS_SCT_SSR_PB_GO',
                'SSR_DUMMY_RECV1$sels$0': term_selected,
            },
            dont_filter = True,
            callback = self.parse_timetable,
        )

    def parse_timetable(self, response):
        print "Parsing class schedule..."

        # login error
        errormsg = response.xpath("id('login_error')/text()")
        if len(errormsg.extract()) > 0:
            with open('data/data' + self.term + '.json', 'w') as jsonFile:
                json.dump({"error": errormsg.extract()[0].strip()}, jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
            return

        # empty schedule
        if not response.xpath("//table[@class='PSGROUPBOXWBO']"):
            print "No class in schedule."
            with open('data/data' + self.term + '.json', 'w') as jsonFile:
                json.dump(list(), jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
            return

        # read schedule
        items = list()
        lastForm = '-'
        lastNbr = '0000'
        for sel in response.xpath("//table[@class='PSGROUPBOXWBO']")[1:]:
            for data in sel.xpath(".//td[@class='PSLEVEL3GRIDROW'][7]/../..//tr")[1:]:
                item = dict()
                item['code'], item['name'] = sel.xpath(".//td[@class='PAGROUPDIVIDER']/text()").extract()[0].split(' - ')
                item['code'] = ''.join(item['code'].split(' '))

                temp = sel.xpath(".//td[@class='PSLEVEL3GRIDROW'][position()<5]/span/text()")
                item['stat'] = temp[0].extract()
                if (item['stat'] == 'Waiting'):
                    item['credit'] = temp[2].extract()
                else:
                    item['credit'] = temp[1].extract()

                span = data.xpath(".//td")
                if span[0].xpath('./span'):
                    content = span[0].xpath('./span/text()').extract()[0]
                    if content == u"\u00a0":
                        item['nbr'] = lastNbr
                    else:
                        item['nbr'] = content
                        lastNbr = item['nbr']
                if span[1].xpath("./span/a"):
                    item['sess'] = span.xpath("./span/a/text()").extract()[0]
                    lastSess = item['sess']
                else:
                    item['sess'] = lastSess
                if span[2].xpath("./span"):
                    content = span[2].xpath("./span/text()").extract()[0]
                    if content == u"\u00a0":
                        item['form'] = lastForm
                    else:
                        item['form'] = content
                        lastForm = content
                daytime = span[3].xpath("./span/text()").extract()[0]
                item['day'], item['time'] = daytime[:2], daytime[3:]
                if item['day'] == u'\u00a0':    # time TBA
                    item['day'] = item['time'] = "-"
                item['venue'] = span[4].xpath("./span/text()").extract()[0]
                temp = span[5].xpath("./span/text()").extract()
                item['instructor'] = ''.join(''.join(temp).split('\r'))
                items.append(item)

        with open('data/data' + self.term + '.json', 'w') as jsonFile:
            print "Writing schedule to file..."
            json.dump(items, jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
