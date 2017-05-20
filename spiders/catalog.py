# -*- coding: utf-8 -*-
import scrapy, re, json

class CatalogSpider(scrapy.Spider):
    name = 'catalog'
    allowed_domains = ["cusis.cuhk.edu.hk"]
    start_urls = (
        'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/SA_LEARNER_SERVICES.SSS_BROWSE_CATLG_P.GBL',
    )

    def __init__(self, category=None, *args, **kwargs):
        self.username = args[0]
        self.password = args[1]
        self.action = args[2]
        super(CatalogSpider, self).__init__(self)

    def start_requests(self):
        return [scrapy.Request(
            self.start_urls[0],
            dont_filter = True,
            callback = self.login,
        )]

    def login(self, response):
        if self.action == 'DERIVED_SSS_BCC_SSR_ALPHANUM_A':
            callbackFunc = self.expand_all
        else:
            callbackFunc = self.goto_page
        return scrapy.FormRequest.from_response(
            response,
            formdata = {
                'timezoneOffset': '-480',
                'userid': args[0],
                'pwd': args[1],
            },
            dont_filter = True,
            callback = callbackFunc,
        )

    def goto_page(self, response):
        fdata = dict()
        for item in response.xpath("//form/input"):
            fdata[item.xpath("@name").extract()[0]] = item.xpath("@value").extract()[0]
        fdata["ICAction"] = self.action

        return scrapy.FormRequest.from_response(
            response,
            formdata = fdata,
            dont_filter = True,
            callback = self.expand_all,
        )

    def expand_all(self, response):
        print "page go to " + response.url
        fdata = dict()
        for item in response.xpath("//form/input"):
            fdata[item.xpath("@name").extract()[0]] = item.xpath("@value").extract()[0]
        fdata["ICAction"] = 'DERIVED_SSS_BCC_SSS_EXPAND_ALL$76$'

        return scrapy.FormRequest.from_response(
            response,
            formdata = fdata,
            dont_filter = True,
            callback = self.read_catalog,
        )

    def read_catalog(self, response):
        catalog = list()

        for subject in response.xpath("//table[@class='PSLEVEL2GRID']"):
            title = subject.xpath("../../../../../preceding-sibling::tr")[2].xpath(".//span[@class='SSSHYPERLINKBOLD']/a/text()").extract()[0].strip().split(' - ')
            subject_code, subject_name = title[0], title[-1]
            if len(subject_code) > 4: continue
            courses = dict()
            for courseRow in subject.xpath("./tr")[1:]:
                # all the courses ever registered to CUSIS, yet they may not be scheduled for this term
                if courseRow.xpath("(./td)[1]/input"):  # UG courses
                    code, name = courseRow.xpath(".//td/span/a/text()").extract()[0:2]
                    courses[code] = name
                else: # PG research courses
                    code, name = courseRow.xpath(".//td/span/a/text()").extract()[0:2]
                    courses[code] = name
                catalog.append((subject_code, subject_name, code, name))

        with open('data/atalog'+self.action[-1]+'.json', 'w') as jsonFile:
            json.dump(catalog, jsonFile, indent=2, separators=(',', ': '), sort_keys=True)
