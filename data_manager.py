# -*- coding: utf-8 -*-
import sys, re, json, csv, time, os, copy, Queue

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from thread_manager import ThreadManager, BrowserThread, NetworkThread
import network_manager, config

CATALOG_URL = 'data/catalog.json'

FORMCODE_URL = 'data/formcode.csv'
LANGUAGE_URL = 'data/language.csv'
VENUECODE_URL = 'data/venue.csv'


# All course data loaded during runtime are saved in this cache
# cache data is accessed by course code in form of 'XXXX0000', where X are capital letters


_cache = dict()
'''
Cache data structure---------------------------------------------------------------------
Note: (~) is the variable name used
      (*) star stressed items are loaded only by specific request
    _cache = {
        code: {
            'code',
            'name',
            'credit',
            'baseform',
            'overall_status',
            'sections': {
                '<section_code>': {
                    'instructor': [],
                    'language': [],
                    'classes': {
                        'Lecture': (classes){
                            (class_dict){
                                'nbr',
                                'day': [],      list_element = '-' if TBA else in raw format, e.g, 'Mo'
                                'time': [],     list_element = '-' if TBA else in raw format, e.g, '02:30PM - 04:15PM'
                                'venue': [],    list_element = 'TBA' if TBA
                                'status',
                                *'quota',
                                *'vacancy',
                            },
                        },
                        'Tutorial': (classes){},
                        'Others': (classes){},
                    },
                },
            },
        },
    }
Cache data structure---------------------------------------------------------------------
'''

# For catalog data structure, view ./data/catalog.json
_catalog = list()


_schedule = dict()
_plans = {'A': dict(), 'B': dict(), 'C': dict()}

'''
Schedule and plan data structure---------------------------------------------------------
    _schedule = {
        code: {
            'sess': [], # sess = section_code + form_code + class_num, e.g. AC1 or -T02
                                # if class is lecture, then sess = section_code
            'nbr': [],  # nbr is a unique identifier useful in referring to data in cache
        }
    }
Schedule and plan data structure---------------------------------------------------------
'''

def dataCrawl(username, password, term):
    process = CrawlerProcess(get_project_settings())

    # timetable & shopping_cart spider
    process.crawl('timetable', None, username, password, term)
    process.crawl('shoppingcart', None, username, password, term)

    # course catalog spider
    if not os.path.isfile(CATALOG_URL):
        for i in string.uppercase:
            action = 'DERIVED_SSS_BCC_SSR_ALPHANUM_' + i
            process.crawl('catalog', None, username, password, action)

    process.start() # the script will block here until the crawling is finished
    process.stop()

    # Combine catalog files
    if not os.path.isfile(CATALOG_URL):
        with open(CATALOG_URL, "w") as total:
            temp = list()
            for i in string.uppercase:
                with open("data/catalog"+i+".json") as file:
                    temp += json.load(file)
                os.remove("data/catalog"+i+".json")
            json.dump(temp, total, indent=2, separators=(',', ': '), sort_keys=True)

def loadCatalog(reload=False):
    global _catalog
    if reload == False and len(_catalog) > 0:
        return _catalog
    else:
        with open(CATALOG_URL, "r") as catalog:
            if catalog == None:
                print "Error: Catalog dose not exist"
                exit(1)
            else:
                data = json.load(catalog)
                print "Catalog loaded from file successfully: " + str(len(data)) + " courses in total"
                print "Please wait..."
                _catalog = data
                return data

# Called when timetable is updated
def saveSketchesToFile(plans, term):
    with open('data/plans' + term + '.json', 'w') as jsonFile:
        sketches = dict()
        for sketch in plans:
            sketches[sketch.getName()] = sketch.getSchedule()
        json.dump(sketches, jsonFile, indent=2, separators=(',', ': '), sort_keys=True)

def loadStoredSketches(term):
    path = 'data/plans' + term + '.json'
    if os.path.isfile(path):
        with open(path) as jsonFile:
            data = json.load(jsonFile)
            if data == None:
                print 'Error: Sketch file invalid'
                data = dict()
    else:
        print 'Info: Sketch file not exist'
        data = dict()
    return data

def loadSchedule(additional_course, browser1, browser2, term):
    global _schedule
    if len(_schedule) == 0:
        # Scrape
        _schedule = loadEnrolledSchedule(term) + loadShoppingCart(term)
        # Detailed search
        courseSet = set()
        for courseItem in _schedule:   # Courses in official schedule
            courseSet.add(courseItem['code'])
        for courseCode in additional_course:    # Courses in local schedule
            courseSet.add(courseCode)
        for code in courseSet:
            loadOpenStatus(code, browser1)
            loadCourseData(code, browser1, browser2)    # Save course detail to _cache

    return _schedule

# Load enrollment status, instead of open status
def loadEnrollmentStatus(nbr):
    global _schedule
    for item in _schedule:
        if item['nbr'] == nbr:
            return item['stat']
    return None

def loadEnrolledSchedule(term):
    with open('data/data' + term + '.json') as dataJson:
        data = json.load(dataJson)
    if 'error' in data:
        print "Error: " + data['error']
        exit(1)
    return data

def loadShoppingCart(term):
    with open('data/cart' + term + '.json') as cartJson:
        cart = json.load(cartJson)
    if 'error' in cart:
        print "Error: " + cart['error']
        exit(1)
    # Get course name for courses in shoppin cart
    # Because course name is not shown in the shopping cart page
    # Loading name by searching in catalog is very ineffecient, change later
    for course in cart:
        for item in loadCatalog():
            if course['code'][:4] == item[0] and course['code'][5:] == item[2]:
                course['name'] = item[3]
    return cart

def loadTableSlotEntries(sketch_schedule):
    classes = list()
    for code in sketch_schedule.keys():
        class_dict = dict()
        sketch_course = sketch_schedule[code]
        class_dict['code'] = code[:4] + ' ' + code[4:]
        class_dict['name'] = _cache[code]['name']

        cached_section = _cache[code]['sections'][sketch_course['section']]
        class_dict['instructor'] = ', '.join(cached_section['instructor'])

        cached_classes = cached_section['classes']
        for form in sketch_course['classes'].keys():
            secondary_class_dict = copy.deepcopy(class_dict)
            secondary_class_dict['nbr'] = sketch_course['classes'][form]
            secondary_class_dict['form'] = form


            found = None
            for index, class_ in cached_classes[form].items():
                if class_['nbr'] == sketch_course['classes'][form]:
                    found = class_
                    break

            if not found == None:
                class_ = found
                name_to_code_dict = dict()
                loadReverseFormCode(name_to_code_dict)
                if form == 'Lecture':
                    secondary_class_dict['sess'] = sketch_course['section']
                else:
                    secondary_class_dict['sess'] = sketch_course['section'] + name_to_code_dict[form] + index
                for i in range(len(class_['time'])):
                    tritiary_class_dict = copy.deepcopy(secondary_class_dict)
                    enroll_status = loadEnrollmentStatus(secondary_class_dict['nbr'])
                    tritiary_class_dict['stat'] = class_['status'] if enroll_status == None else enroll_status
                    tritiary_class_dict['day'] = class_['day'][i]
                    tritiary_class_dict['time'] = class_['time'][i]
                    tritiary_class_dict['venue'] = class_['venue'][i]
                    classes.append(tritiary_class_dict)
            else:
                print 'Error: Course in sketch not found in cache'
    #print classes
    return classes


def loadFormCode(code_to_name_dict, abbr_to_name_dict):
    with open(FORMCODE_URL, "r") as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        for item in csvReader:
            code_to_name_dict[item[0]] = item[2]
            abbr_to_name_dict[item[1]] = item[2]

def loadReverseFormCode(name_to_code_dict):
    with open(FORMCODE_URL, "r") as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        for item in csvReader:
            name_to_code_dict[item[2]] = item[0]

def loadLangCode(code_to_lang_dict):
    with open(LANGUAGE_URL, "r") as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        for item in csvReader:
            code_to_lang_dict[item[0]] = item[1]

def loadVenueCode(code_to_name_dict):
    with open(VENUECODE_URL, "r") as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        for item in csvReader:
            code_to_name_dict[item[0]] = ','.join(item[1].split('`'))

def setCachedCourseUnavailable(code):
    if code in _cache:
        if not _cache[code] == None:
            print "Error: Cache conflict"
            exit(1)
    else:
        _cache[code] = None

def cachedCourseIsAvailable(code):
    if code in _cache:
        if _cache[code] == None:
            return False
        else:
            return True
    else:
        return None

# Check if a course is available via class search
def loadOpenStatus(code, search_browser):
    if network_manager.check_connection() == False:
        return config.NETWORK_ERROR

    status_queue = Queue.Queue()
    check_thread = BrowserThread(status_queue, search_browser.check, code)

    manager = ThreadManager(1, (check_thread,), (status_queue,))
    manager.start()

    return manager.get()[0]

def loadCourseData(code, search_browser, ttable_browser, reload=False):
    # Check if data is already in cache
    if code not in _cache or reload == True:
        # Load from CUSIS concurrently
        search_queue = Queue.Queue()
        ttable_queue = Queue.Queue()

        search_thread = BrowserThread(search_queue, search_browser.loadSearchResult, code)
        ttable_thread = BrowserThread(ttable_queue, ttable_browser.loadTeachingTable, code)

        manager = ThreadManager(2, (search_thread, ttable_thread), (search_queue, ttable_queue))
        manager.start()

        search_result, ttable_result = manager.get()

        if search_result == None or ttable_result == None:
            print "Error: Data load from CUSIS failed, no results returned: " + code
            exit(1)
        elif ttable_result == config.NETWORK_ERROR:
            return config.NETWORK_ERROR

        # Combine data from teaching table and search result
        ttable_result['overall_status'] = search_result['overall_status']

        for section_code in ttable_result['sections'].keys():
            search_classes = search_result['sections'][section_code]['classes']
            ttable_classes = ttable_result['sections'][section_code]['classes']
            for class_form in ttable_classes.keys():
                search_form = search_classes[class_form]
                ttable_form = ttable_classes[class_form]
                for class_dict in ttable_form.keys():
                    ttable_class = ttable_form[class_dict]
                    search_class = search_form[class_dict]

                    ttable_class['status'] = search_class['status']
                    ttable_class['nbr'] = search_class['nbr']

        # Save to cache
        _cache[code] = ttable_result

    #print _cache[code]
    return _cache[code]

def getBaseform(code):
    return _cache[code]['baseform']
