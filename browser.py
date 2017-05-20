# -*- coding: utf-8 -*-
import sys, re, json, csv, time, string, threading, Queue
from operator import itemgetter
from HTMLParser import HTMLParser

from PyQt4 import QtGui, QtCore

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import data_manager, config

URL = {
    'CLASS_SEARCH': 'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/SA_LEARNER_SERVICES.CLASS_SEARCH.GBL',   # Class Search
    'TEACHING_TABLE': 'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/CU_SCR_MENU.CU_TMSR801.GBL',           # Teaching timetable
    'SHOPPING_CART': 'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/SA_LEARNER_SERVICES_2.SSR_SSENRL_CART.GBL',
    'DROP': 'https://cusis.cuhk.edu.hk/psc/csprd/CUHK/PSFT_HR/c/SA_LEARNER_SERVICES.SSR_SSENRL_DROP.GBL?Page=SSR_SSENRL_DROP',
}

REFRESH_INTERVAL = 1200.0     # in sec

LOGIN_SUCCESS = 1
LOGIN_FAILURE = 0


class Browser():
    def __init__(self, browser, dest):
        self.browser = browser
        self.browser.get(URL[dest])
        self.url = URL[dest]

        self.login_status = 0
        self.cacheCatalog = dict()   # store all courses information that has been loaded from CUSIS

        self.code_to_name = dict()
        self.abbr_to_name = dict()
        data_manager.loadFormCode(self.code_to_name, self.abbr_to_name)

        self.code2lang = dict()
        data_manager.loadLangCode(self.code2lang)

        self.venue_abbr_to_name = dict()
        data_manager.loadVenueCode(self.venue_abbr_to_name)

        self.timer = None

    def login(self, cred):
        self.cancelTimer()

        if self.login_status == LOGIN_SUCCESS: return LOGIN_SUCCESS     # Already logged in

        self.term_code = cred['term_code']
        self.term_name = cred['term_name']

        username = self.browser.find_element_by_id("userid")
        password = self.browser.find_element_by_id("pwd")

        username.send_keys(str(cred['username']))
        password.send_keys(str(cred['password']))

        self.browser.find_element_by_name("Submit").click()

        if not len(self.browser.find_elements_by_id("userid")) == 0:
            return LOGIN_FAILURE

        self.login_status = LOGIN_SUCCESS
        self.setTimer()

        return LOGIN_SUCCESS

    def check(self, code, resetFlag=0):
        self.cancelTimer()

        # Explict wait to avoid race condition where the find element is executing before it is present on the page
        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            termSelect = Select(wait.until(EC.element_to_be_clickable((By.ID,'CLASS_SRCH_WRK2_STRM$50$'))))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.browser.get(self.url)
            return config.NETWORK_ERROR

        #termSelect = Select(self.browser.find_element_by_id("CLASS_SRCH_WRK2_STRM$50$"))
        termSelect.select_by_value(self.term_code)

        # Fill in course code
        course_subject = self.browser.find_element_by_id("CLASS_SRCH_WRK2_SUBJECT$67$")
        course_number = self.browser.find_element_by_id("CLASS_SRCH_WRK2_CATALOG_NBR$71$")

        course_number.clear()
        course_number.send_keys(code[4:])
        course_subject.clear()
        course_subject.send_keys(code[:4])

        # Also search for wait-listed & closed classes
        if self.browser.find_element_by_name("CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk").get_attribute("value") == 'Y':
            self.browser.find_element_by_id("CLASS_SRCH_WRK2_SSR_OPEN_ONLY").click()

        # PG Research course
        if int(code[4]) > 4:
            career = Select(self.browser.find_element_by_id("CLASS_SRCH_WRK2_ACAD_CAREER"))
            career.select_by_visible_text("Postgraduate - Research")

        # Submit search
        self.browser.find_element_by_id("CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH").click()

        # Handling prompt with more than 50 courses
        try:
            self.browser.find_element_by_id("#ICSave").click()
        except:
            pass

        # Return True if the course is available
        try:
            self.browser.find_element_by_id("DERIVED_CLSRCH_SSR_CLASSNAME_LONG$0")

            if resetFlag == 1: self.reset()
            self.setTimer()

            return True
        # No matched course
        except:
            print "Course " + code + " not opened"

            if resetFlag == 1: self.reset()
            self.setTimer()

            return False


    # This method normally should be executed right after check()
    def loadSearchResult(self, code):
        self.cancelTimer()

        # Expand all sections
        try:
            expand_all = self.browser.find_element_by_id("$ICField106$hviewall$0")
            if expand_all.text == "View All Sections":
                expand_all.click()
        except:
            pass

        # Parse course data

        # Update data with overall_status and status
        '''
        data = {
            'overall_status',
            'sections': {
                '<section_code>': {
                    'classes': {
                        'Lecture': {
                            (class_dict){
                                'nbr',
                                'status',
                            },
                        },
                        'Tutorial': {},
                        'Others': {},
                    },
                },
            },
        }
        '''


        data = dict()
        data['sections'] = dict()

        table_raw = self.browser.find_element_by_id("$ICField106$scroll$0").get_attribute('innerHTML')

        classcodelist = re.findall('(?<=[>]).+?[(][0-9]{4}[)]', table_raw)
        statuslist = re.findall('(?<=alt[=]["]).{1,10}(?=["])', table_raw)

        data['overall_status'] = 'Closed'
        for classcode, status in zip(classcodelist, statuslist):
            classcode_splited = re.split("(?<=.)[-]", classcode)

            if re.search('[0-9]', classcode_splited[0]):    # non-lecture
                m = re.search('(?<=[-a-zA-Z])[a-zA-Z](?=[0-9])', classcode_splited[0])
                classform = self.code_to_name[m.group(0)]
                m = re.split('(?<=[-a-zA-Z])[a-zA-Z](?=[0-9])', classcode_splited[0])
                section = m[0]
                classnum = m[1]
            else:   # class is of lecture form
                classform = 'Lecture'
                section = classcode_splited[0]
                classnum = '01'

            if section not in data['sections']:
                data['sections'][section] = dict()
                data['sections'][section]['classes'] = dict()
            if classform not in data['sections'][section]['classes']:
                data['sections'][section]['classes'][classform] = dict()
            if classnum not in data['sections'][section]['classes'][classform]:
                data['sections'][section]['classes'][classform][classnum] = dict()

            classes = data['sections'][section]['classes'][classform][classnum]

            classes['nbr'] = classcode_splited[1][-5:-1]

            if status == 'Wait List':
                classes['status'] = 'Waiting'
            else:
                classes['status'] = status
            if data['overall_status'] != 'Open':
                if classes['status'] == 'Open':
                    data['overall_status'] = 'Open'
                elif classes['status'] == 'Waiting':
                    data['overall_status'] = 'Waiting'

        # reset
        self.reset()
        self.setTimer()

        print "Class search finished."
        #print data
        return data

    def loadTeachingTable(self, code):
        self.cancelTimer()

        start = time.time()
        # Explict wait to avoid race condition where the find element is executing before it is present on the page
        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            termSelect = Select(wait.until(EC.element_to_be_clickable((By.ID,'CLASS_SRCH_WRK2_STRM$50$'))))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.browser.get(self.url)
            return config.NETWORK_ERROR
        termSelect.select_by_value(self.term_code)

        # Fill in course code
        course_subject = self.browser.find_element_by_id("CU_RC_TMSR801_SUBJECT")

        course_subject.clear()
        course_subject.send_keys(code[:4])

        # Submit search
        self.browser.find_element_by_id("CU_RC_TMSR801_SSR_PB_CLASS_SRCH").click()
        end = time.time()
        print "Submit search time spent: " + str(end-start)


        # Table parsing
        '''
        Note: (.) is the variable name used
              (*) star stressed items are loaded only by specific request
        table_data = {
            'code',
            'name',
            'credit',
            'baseform',
            'sections': {
                '<section_code>': {
                    'instructor': [],
                    'language': [],
                    'classes': {
                        'Lecture': (classes){
                            (class_dict){
                                'day': [],          list_element = '-' if TBA else in raw format, e.g, 'Mo'
                                'time': [],         list_element = '-' if TBA else in raw format, e.g, '02:30PM - 04:15PM'
                                'venue': [],        list_element = 'TBA' if TBA
                                *'quota',
                                *'vacancy',
                            },
                        },
                        'Tutorial': (classes){},
                        'Others': (classes){},
                    },
                },
            },
        }
        '''

        table_data = dict()
        table_data['code'] = code

        table = self.browser.find_element_by_id("CLASS_LIST$scroll$0")
        trs = table.get_attribute('innerHTML').split('</tr>')[2:]

        # Parsing data preparation: course region HTML extraction
        sections_tr = list()
        flag = 0
        for tr in trs:
            if flag == 0 and code in tr:    # Reach course region
                section_tr = [tr]
                flag = 1
            elif flag == 1:
                if code in tr:      # Reach new section region
                    sections_tr.append(section_tr)
                    section_tr = [tr]
                elif 'span' not in tr.split('</td>')[0]:    # Inside section region
                    section_tr.append(tr)
                else:       # Out of course region
                    flag = 2
                    sections_tr.append(section_tr)
                    break

        # Exit with whole table run through
        if flag < 2:
            sections_tr.append(section_tr[:-1])

        if len(sections_tr) == 0 or len(sections_tr[0]) == 0:
            print "Error: Course does not exist in teaching timetable: " + code
            return None

        # Main parsing
        table_data['sections'] = dict()
        h = HTMLParser(); flag = 0

        ESCAPE = lambda x: h.unescape(x.group(0))
        RE_SEARCH_A = '(?<=[>]).+?(?=[<][/]a[>])'
        RE_SEARCH_SPAN = '(?<=[>]).+?(?=[<][/]span[>])'
        for trs in sections_tr:
            tds = trs[0].split('</td>')
            #print tds
            # Basic information parsing
            if flag == 0:
                flag = 1
                table_data['name'] = ESCAPE(re.search(RE_SEARCH_A, tds[2]))
                table_data['credit'] = ESCAPE(re.search(RE_SEARCH_SPAN, tds[3]))
                table_data['baseform'] = self.abbr_to_name[ESCAPE(re.search(RE_SEARCH_SPAN, tds[7]))]

            # Section information parsing
            temp = ESCAPE(re.search(RE_SEARCH_SPAN, tds[8]))
            if table_data['baseform'] == 'Lecture':
                section_code = temp
            else:
                m = re.search('^[-a-zA-Z]*(?=[a-zA-Z][0-9])', temp)
                section_code = m.group(0)

            section = table_data['sections'][section_code] = dict()
            section_classes = section['classes'] = dict()

            raw = ''.join(tds[4].split('\n')[2:])
            section['instructor'] = map(string.strip, ESCAPE(re.search(RE_SEARCH_SPAN, ''.join(raw.split('<br>')))).split('-'))[1:]

            # Parse language information
            lang = ESCAPE(re.search(RE_SEARCH_SPAN, tds[9]))
            section['language'] = list()

            # Language operater detection
            split_s = ' '
            if '#' in lang:         # lang1, change to lang2 if needed
                split_s = '#'
            elif '&' in lang:       # lang1 & lang2
                split_s = '&'
            elif len(lang) > 1:
                print "Error: unknown language operator detected: " + lang

            section['language'].append(split_s)
            for lang_code in lang.split(split_s):
                if lang_code in self.code2lang:
                    section['language'].append(self.code2lang[lang_code])
                else:
                    section['language'].append(lang_code)
                    print "Error: unknown language detected: " + lang_codes

            # Parse class sessions
            last_formcode = None
            last_sub_section_code = 'Unknown'
            for tr in trs:
                tds = tr.split('</td>')

                formcode = re.search(RE_SEARCH_SPAN, tds[7])
                daytime = ESCAPE(re.search(RE_SEARCH_SPAN, tds[10]))
                venue = ESCAPE(re.search(RE_SEARCH_SPAN, tds[11]))
                if formcode == None:
                    formcode = last_formcode
                else:
                    formcode = self.abbr_to_name[ESCAPE(formcode)]
                    class_dict = {'day': [], 'time': [], 'venue': []}

                    if formcode not in section_classes:
                        section_classes[formcode] = dict()

                    last_formcode = formcode

                if formcode == 'Lecture':
                    section_classes[formcode]['01'] = class_dict
                else:
                    temp = re.search(RE_SEARCH_SPAN, tds[8])
                    if temp == None:
                        sub_section_code = last_sub_section_code
                    else:
                        m = re.search('(?<=[-a-zA-Z])[0-9]+$', ESCAPE(temp))
                        sub_section_code = m.group(0)
                        last_sub_section_code = sub_section_code
                    section_classes[formcode][sub_section_code] = class_dict

                class_dict['day'].append('-' if daytime == "TBA" else daytime[:2])
                class_dict['time'].append('-' if daytime == "TBA" else daytime[3:])
                if venue in self.venue_abbr_to_name:
                    class_dict['venue'].append(self.venue_abbr_to_name[venue])
                else:
                    temp = venue.split('_')
                    if temp[0] in self.venue_abbr_to_name:
                        class_dict['venue'].append(' '.join([self.venue_abbr_to_name[temp[0]], temp[1]]))
                    else:
                        if not temp[0] == 'TBA':
                            print "Error: Venue abbreviation not recognized: " + venue
                        class_dict['venue'].append(venue)

        self.reset()
        self.setTimer()

        print "Teaching timetable search finished."
        #print table_data
        return table_data

    def selectTerm(self):
        # Term selection
        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            submit = wait.until(EC.element_to_be_clickable((By.ID,'DERIVED_SSS_SCT_SSR_PB_GO')))
        except:
            print "Error: Browser exception encountered in term selection."
            return config.NETWORK_ERROR

        term_table = self.browser.find_element_by_id('SSR_DUMMY_RECV1$scroll$0')
        for tr in term_table.find_elements_by_xpath('.//tr')[2:]:
            tds =  tr.find_elements_by_xpath("./td")
            m = re.search(self.term_name, tds[1].find_elements_by_xpath("./span")[0].text)
            if not m == None:
                tds[0].find_element_by_xpath("./input").click()
                submit.click()
                break

    def getNbrToBoxDict(self, table, nbr_to_box):
        course_title_items = table.find_elements_by_xpath(".//a[@class='PSHYPERLINK']")
        course_select_boxes = table.find_elements_by_xpath(".//input[@type='checkbox']")

        course_nbrs = map(lambda item: re.search('(?<=[(])[0-9]{4}(?=[)])', item.text).group(0), course_title_items)
        for i in range(len(course_nbrs)):
            nbr_to_box[course_nbrs[i]] = course_select_boxes[i]

    def syncCart(self, toDel, toAdd):
        # delete course from shopping cart
        delList = list()
        for c in toDel:
            baseform = data_manager.getBaseform(c)
            delDict = toDel[c]
            delDict['baseform'] = baseform
            delList.append(delDict)
        if len(delList) > 0:
            self.deleteCourseFromCart(delList, reset=False)

        # add course to shopping cart
        for c in toAdd:
            baseform = data_manager.getBaseform(c)
            addDict = toAdd[c]
            addDict['baseform'] = baseform
            self.addCourseToCart(addDict, reset=False)

        self.browser.get(self.url)

    def addCourseToCart(self, course, reset=True):
        self.cancelTimer()
        self.browser.get(URL['SHOPPING_CART'])

        self.selectTerm()

        # Add course by nbr
        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            submit_search = wait.until(EC.element_to_be_clickable((By.ID,'DERIVED_REGFRM1_SSR_PB_ADDTOLIST2$67$')))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.addCourseToCart(course, reset)
            return config.NETWORK_ERROR

        # Enter base form class nbr
        searchField = self.browser.find_element_by_id('DERIVED_REGFRM1_CLASS_NBR')
        searchField.clear()
        searchField.send_keys(str(course['classes'][course['baseform']]))

        submit_search.click()

        # TODO:
        # Exception handling
            # Course already enrolled
            # Course not exist
            # etc

        warnings = self.browser.find_elements_by_xpath(".//table[@class='SSSMSGWARNINGFRAME']")
        if len(warnings) > 0:
            print 'Error: ', warnings[0].find_element_by_xpath(".//span").text
            print 'Unable to add course to shopping cart'
            return


        # Choose session based on nbr
        otherFormFound = False
        for c in course['classes']:
            if c != course['baseform']:
                otherFormFound = True
                break
        if otherFormFound:
            try:
                wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
                next = wait.until(EC.element_to_be_clickable((By.ID,'DERIVED_CLS_DTL_NEXT_PB')))
            except:
                print "Error: Browser exception encountered. Handling by resetting..."
                self.addCourseToCart(course, reset)
                return config.NETWORK_ERROR

            table_num = 0
            found = 0
            while True:
                table_num += 1
                try:
                    section_table = self.browser.find_element_by_id('SSR_CLS_TBL_R' + str(table_num) + '$scroll$0')
                    section_rows = section_table.find_elements_by_xpath('./tbody/tr/td/table/tbody/tr')[1:]
                except:
                    break

                for tr in section_rows:
                    tds = tr.find_elements_by_xpath('./td')
                    nbr = tds[1].find_element_by_xpath('./span').text

                    for form in course['classes'].keys():
                        if nbr == course['classes'][form]:
                            box = tds[0].find_element_by_xpath('./input')
                            box.click()
                            found += 1
                            break

                    if found == table_num: break

            next.click()

        # Wait list and confirm
        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            next = wait.until(EC.element_to_be_clickable((By.ID,'DERIVED_CLS_DTL_NEXT_PB$75$')))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.addCourseToCart(course, reset)
            return config.NETWORK_ERROR

        waitListCheck = self.browser.find_element_by_id('DERIVED_CLS_DTL_WAIT_LIST_OKAY$48$')
        waitListCheck.click()
        next.click()

        # TODO:
        # Processing adding result


        print 'Course added to shopping cart successfully'

        # Reset
        if reset == True:
            self.browser.get(self.url)

        self.setTimer()


    # TODO: fix bugs causing deletion failure
    def deleteCourseFromCart(self, course_list, reset=True):
        self.cancelTimer()
        self.browser.get(URL['SHOPPING_CART'])

        self.selectTerm()

        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            cart_table = wait.until(EC.presence_of_element_located((By.ID,'SSR_REGFORM_VW$scroll$0')))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.deleteCourseFromCart(course_list, reset)
            return config.NETWORK_ERROR

        deletes = self.browser.find_elements_by_id('DERIVED_REGFRM1_SSR_PB_DELETE')
        if len(deletes) == 0:
            print "Invalid deletion: No course in cart"
        else:
            delete = deletes[0]

            nbr_to_box = dict()
            self.getNbrToBoxDict(cart_table, nbr_to_box)

            for course in course_list:
                nbr = course['classes'][course['baseform']]
                if nbr in nbr_to_box:
                    nbr_to_box[nbr].click()
                else:
                    print 'Invalid deletion: Class ' + nbr + ' not in cart'

            delete.click()

            print 'Course deleted from shopping cart successfully'

        # Reset
        if reset == True:
            self.browser.get(self.url)

        self.setTimer()

    # TODO:
    def validateCourseInCart(self, course_list, reset=True):
        pass

    # This method can only be called after passing the validation
    def enrollCourseInCart(self, course_list, reset=True):
        self.cancelTimer()
        self.browser.get(URL['SHOPPING_CART'])

        self.selectTerm()

        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            cart_table = wait.until(EC.presence_of_element_located((By.ID,'SSR_REGFORM_VW$scroll$0')))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.enrollCourseInCart(course_list, reset)
            return config.NETWORK_ERROR

        enrolls = self.browser.find_elements_by_id('DERIVED_REGFRM1_LINK_ADD_ENRL')
        if len(enrolls) == 0:
            print "Invalid enrollment: No course in cart"
        else:
            enroll = enrolls[0]

            nbr_to_box = dict()
            self.getNbrToBoxDict(cart_table, nbr_to_box)

            for course in course_list:
                nbr = course['classes'][course['baseform']]
                if nbr in nbr_to_box:
                    nbr_to_box[nbr].click()
                else:
                    print 'Invalid enrollment: Class ' + nbr + ' not in cart'

            enroll.click()

            try:
                wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
                submit = wait.until(EC.presence_of_element_located((By.ID,'DERIVED_REGFRM1_SSR_PB_SUBMIT')))
            except:
                print "Error: Browser exception encountered. Handling by resetting..."
                self.enrollCourseInCart(course_list, reset)
                return config.NETWORK_ERROR

            submit.click()

            # TODO:
            # Show enrollment result
            print self.parseResult()

            print 'Course enrolling action completed'

        # Reset
        if reset == True:
            self.browser.get(self.url)

        self.setTimer()

    def dropCourse(self, course_list, reset=True):
        self.cancelTimer()
        self.browser.get(URL['DROP'])

        self.selectTerm()

        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            submit = wait.until(EC.element_to_be_clickable((By.ID,'DERIVED_REGFRM1_LINK_DROP_ENRL')))
        except:
            print "Error: Browser exception encountered. Handling by resetting..."
            self.dropCourse(course_list, reset)
            return config.NETWORK_ERROR

        course_table = self.browser.find_element_by_id('STDNT_ENRL_SSV1$scroll$0')
        nbr_to_box = dict()
        self.getNbrToBoxDict(course_table, nbr_to_box)

        if len(nbr_to_box.keys()) == 0:
            print "Invalid drop: No enrolled course in schedule"
        else:
            for course in course_list:
                nbr = course['classes'][course['baseform']]
                if nbr in nbr_to_box:
                    nbr_to_box[nbr].click()
                else:
                    print 'Invalid drop: Class ' + nbr + ' not in schedule'

            submit.click()

            try:
                wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
                submit = wait.until(EC.element_to_be_clickable((By.ID,'DERIVED_REGFRM1_SSR_PB_SUBMIT')))
            except:
                print "Error: Browser exception encountered. Handling by resetting..."
                self.dropCourse(course_list, reset)
                return config.NETWORK_ERROR

            submit.click()

            # TODO:
            # Show drop result
            print self.parseResult()

            print 'Course dropping action complete'

        # Reset
        if reset == True:
            self.browser.get(self.url)

        self.setTimer()

    def parseResult(self):
        try:
            wait = WebDriverWait(self.browser, config.DRIVER_EXPLICIT_WAIT)
            result_table = wait.until(EC.element_to_be_clickable((By.ID, 'SSR_SS_ERD_ER$scroll$0')))
        except:
            print "Error: Browser exception encountered in result parsing."
            return config.NETWORK_ERROR

        result = dict()
        trs = result_table.find_elements_by_xpath('.//tr')[1:]
        for tr in trs:
            code_td, message_td, status_td = tr.find_elements_by_xpath('./td')

            code_span = code_td.find_element_by_xpath('./span')
            code = ''.join(code_span.text.split(' '))
            result[code] = dict()

            message_div = message_td.find_element_by_xpath('./div')
            status_img = status_td.find_element_by_xpath('./div/img')
            result[code]['message'] = message_div.text
            result[code]['status'] = status_img.get_attribute('alt')

        return result

    def submitSchedule(self, schedule):
        pass

    def reset(self):
        self.browser.execute_script("window.history.go(-window.history.length+3)")
        if not self.browser.current_url == self.url:
            self.browser.get(self.url)

    def setTimer(self):
        self.timer = threading.Timer(REFRESH_INTERVAL, self.refresh)
        self.timer.start()

    def cancelTimer(self):
        if not self.timer == None:
            self.timer.cancel()

    def refresh(self):
        self.cancelTimer()
        self.browser.get(self.url)
        self.setTimer()
        print str(REFRESH_INTERVAL / 60) + ' minutes of inactivity, browser refreshed'

    def exit(self):
        self.cancelTimer()
        self.browser.quit()
