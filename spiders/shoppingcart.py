# -*- coding: utf-8 -*-
import re, json, csv, copy

import scrapy

class ShoppingCartSpider(scrapy.Spider):
    name = 'shoppingcart'
    allowed_domains = ["cusis.cuhk.edu.hk"]
    start_urls = (
        'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/SA_LEARNER_SERVICES_2.SSR_SSENRL_CART.GBL',
    )

    def __init__(self, category=None, *args, **kwargs):
        self.username = args[0]
        self.password = args[1]
        self.term = args[2]
        super(ShoppingCartSpider, self).__init__(self)

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
        print "Parsing shopping cart data..."

        # login error
        errormsg = response.xpath("id('login_error')/text()")
        if len(errormsg.extract()) > 0:
            with open('data/data' + self.term + '.json', 'w') as jsonFile:
                json.dump({"error": errormsg.extract()[0].strip()}, jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
            return

        # empty cart
        if not response.xpath("//a[@id='DERIVED_REGFRM1_LINK_ADD_ENRL']"):
            print "No class in cart."
            with open('data/cart' + self.term + '.json', 'w') as jsonFile:
                json.dump(list(), jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
            return

        #read cart
        items = list()
        formcode = dict()
        lastCredit = ''
        with open("data/formcode.csv", "r") as csvFile:
            csvReader = csv.reader(csvFile, delimiter=',')
            for item in csvReader:
                formcode[item[0]] = item[2]

        cart = response.xpath("//table[@class='PSLEVEL1GRIDNBO']")
        for sel in cart.xpath("./tr")[2:]:
            data = sel.xpath("./td")
            item = dict()
            if data[0].xpath("./input"):
                temp = data[1].xpath("./span/a/text()").extract()
                item['code'] = temp[0][:9]
                item['code'] = ''.join(item['code'].split(' '))
                item['sess'] = temp[0][10:]
                item['nbr'] = temp[1][3:7]
                item['credit'] = data[5].xpath("./span/text()").extract()[0]
                lastCredit = item['credit']
                item['form'] = 'Lecture'
            else:
                temp = data[1].xpath("./span/text()").extract()
                item['code'] = temp[0][1:10]
                item['code'] = ''.join(item['code'].split(' '))
                item['sess'] = temp[0][11:]
                item['nbr'] = temp[1][3:7]
                item['credit'] = lastCredit
                try:
                    item['form'] = formcode[temp[0][-3]]
                except:
                    print "Error: Class form unknown"
                    item['form'] = '-'

            temp = data[4].xpath("./span/text()").extract()
            item['instructor'] = ' '.join(''.join(temp).split('\r'))
            item['venue'] = data[3].xpath("./span/text()").extract()[0]
            tempDict = {"Open": "Cart-Open", "Wait List": "Cart-Waiting", "Closed": "Cart-Closed"}
            item['stat'] = tempDict[data[6].xpath("./div/img/@alt").extract()[0]]

            for daytime in data[2].xpath("./span/text()").extract():
                newitem = copy.deepcopy(item)
                if daytime[0] == '\r':
                    newitem['day'], newitem['time'] = daytime[1:3], daytime[4:]
                else:
                    newitem['day'], newitem['time'] = daytime[:2], daytime[3:]
                if newitem['day'] == u'\u00a0':    # time TBA
                    newitem['day'] = newitem['time'] = "-"
                items.append(newitem)
            #print item


        with open("data/cart" + self.term + ".json", "w") as jsonFile:
            print "Writing shopping cart data to file..."
            json.dump(items, jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
