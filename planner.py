# -*- coding: utf-8 -*-
import sys, re, json, csv, time
from operator import itemgetter

from PyQt4 import QtGui, QtCore

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from section_widget import SectionWidget
from smart_table import SmartTable
from browser import Browser
from sketch import Sketch
import data_manager, config

# Geometry constants
WINDOW_WIDTH = 1700
WINDOW_HEIGHT = 910

VERTICAL_SPACING = 30
HORIZONTAL_SPACING = 50

MAIN_MARGIN_TOP = VERTICAL_SPACING
MAIN_MARGIN_LEFT = HORIZONTAL_SPACING

LEFT_COLUMN_WIDTH = 350

# With respect to smart table size (1200, 800)
TABS_WIDTH = 1205
TABS_HEIGHT = 835
TABS_X = LEFT_COLUMN_WIDTH + MAIN_MARGIN_LEFT + HORIZONTAL_SPACING

SYNCBUTTON_HEIGHT = 40
SYNCBUTTON_WIDTH = 50
SYNCBUTTON_X = LEFT_COLUMN_WIDTH + HORIZONTAL_SPACING - SYNCBUTTON_WIDTH
SYNCBUTTON_Y = MAIN_MARGIN_TOP

MODE_SYNC_SPACING = 15

MODEBOX_HEIGHT = 40
MODEBOX_WIDTH = LEFT_COLUMN_WIDTH - SYNCBUTTON_WIDTH - MODE_SYNC_SPACING
MODEBOX_X = MAIN_MARGIN_LEFT
MODEBOX_Y = MAIN_MARGIN_TOP

SEARCH_HEIGHT = 40
SEARCH_WIDTH = LEFT_COLUMN_WIDTH
SEARCH_X = MAIN_MARGIN_LEFT
SEARCH_Y = MODEBOX_Y + MODEBOX_HEIGHT + VERTICAL_SPACING

LIST_WIDTH = LEFT_COLUMN_WIDTH
LIST_HEIGHT = TABS_HEIGHT - (SEARCH_HEIGHT + MODEBOX_HEIGHT + VERTICAL_SPACING * 2)
LIST_X = MAIN_MARGIN_LEFT
LIST_Y = SEARCH_Y + SEARCH_HEIGHT + VERTICAL_SPACING

PLANNER_WIDTH = TABS_WIDTH
THICK_GRID_SPACING = 30
THIN_GRID_SPACING = 15

TIMESLOTNUM = 13
PLANNER_LISTITEM_HEIGHT = 30
DEFAULT_VENUENUM = 0

SEARCH_RESULT_BLOCK_LENGTH = 50
SEARCH_LISTITEM_HEIGHT = 80

ICON_SIZE = 24
ICON_MARGIN = 6

STATUSBAR_X = 0
STATUSBAR_Y = 870
STATUSBAR_WIDTH = 1000
STATUSBAR_HEIGHT = 40

class CourseInfo(QtGui.QWidget):
    searchResultNum = 0
    code = list()
    name = list()
    data = None
    info = None
    lastCourse = ''

    def __init__(self, browser1, browser2, term, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.browser1 = browser1
        self.browser2 = browser2

        self.term = term

        self.setWindowTitle('Course Information')

        self.section_window_count = 0

        # initialize window
        self.initUI()
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.catalog = data_manager.loadCatalog()

        print "Ready"

    def initUI(self):
        # Status bar
        self.status_bar = QtGui.QStatusBar(self)
        self.status_bar.showMessage('Ready')
        self.status_bar.setGeometry(STATUSBAR_X, STATUSBAR_Y, STATUSBAR_WIDTH, STATUSBAR_HEIGHT)

        # table_tabs of tableview
        self.table_tabs = QtGui.QTabWidget(self)
        self.table_tabs.setGeometry(TABS_X, MAIN_MARGIN_TOP, TABS_WIDTH, TABS_HEIGHT)

        #self.helpInfoTab = QtGui.QWidget(self.table_tabs)                     # TODO: Add help information>>>>>>>>>>>>>>>>>>>>
        self.timetableTab = SmartTable(self.table_tabs)
        self.plannerTab = QtGui.QWidget(self.table_tabs)
        #self.plannerTab = PlannerWidget(self.table_tabs)

        #self.table_tabs.addTab(self.helpInfoTab, "Info")
        self.table_tabs.addTab(self.timetableTab, "Timetable")
        self.table_tabs.addTab(self.plannerTab, "Planner")

        # Context combo box
        self.modeBox = modeBox = QtGui.QComboBox(self)
        self.modeBox.addItem('My class schedule')
        self.modeBox.addItem('Plan A')
        self.modeBox.addItem('Plan B')
        self.modeBox.addItem('Plan C')
        modeBox.setGeometry(MODEBOX_X, MODEBOX_Y, MODEBOX_WIDTH, MODEBOX_HEIGHT)
        modeBox.currentIndexChanged.connect(self.switchContext)

        self.initSketches()

        syncButton = QtGui.QPushButton('Sync', parent=self)
        syncButton.setGeometry(SYNCBUTTON_X, SYNCBUTTON_Y, SYNCBUTTON_WIDTH, SYNCBUTTON_HEIGHT)
        # TODO:
        # Connect to different sync operation according to context
        # use method addCourseToCart, dropCourse, enrollCourseInCart in browser.py
        syncButton.clicked.connect(self.sync)


        # Load main sketch to table
        self.timetableTab.loadTimetable(data_manager.loadTableSlotEntries(self.offical_sketch.getSchedule()))
        self.table_tabs.setGeometry(TABS_X, MAIN_MARGIN_TOP, TABS_WIDTH, TABS_HEIGHT)

        # List tabs in the left column of planner
        list_tabs = QtGui.QTabWidget(self)
        list_tabs.setGeometry(LIST_X, LIST_Y, LIST_WIDTH, LIST_HEIGHT)

        # Search column on the left
        searchField = self.searchField = SearchField(list_tabs, parent=self)

        scheduleList = self.scheduleList = ScheduleList(self.draft_sketch, self, parent=list_tabs)
        scheduleList.switchContext(self.main_sketch)
        searchList = self.searchList = SearchList(self.browser1, self.browser2, self.draft_sketch, searchField, self.status_bar, self, parent=list_tabs)
        searchField.textChanged.connect(searchList.updateSearchResult)

        list_tabs.addTab(scheduleList, "Schedule")
        list_tabs.addTab(searchList, "Search Results")

        self.setFocus()

    @QtCore.pyqtSlot()
    def sync(self):
        if self.main_sketch == self.offical_sketch:
            syncList = self.offical_sketch.diff(self.online_sketch)
            self.browser1.syncCart(*syncList)
            self.online_sketch = Sketch(self.timetableTab, None, name='online sketch', copy=self.offical_sketch)
            # TODO: update timetable after syncing

            

        else:
            print 'Error: Plan sync not supported yet'

    def initSketches(self):
        # Context sketches
        self.draft_sketch = Sketch(self.timetableTab, None)
        self.offical_sketch = Sketch(self.timetableTab, self.draft_sketch, name='offical sketch')
        self.plan_sketches = list()
        temp = data_manager.loadStoredSketches(self.term)
        planned_course = list()
        for i in range(3):  # Sketches for plan A, B, and C
            plan_name = 'plan'+str(i)
            plan = Sketch(self.timetableTab, self.draft_sketch, name=plan_name)
            # Set cached scheduled according to the file
            if plan_name in temp.keys():
                plan.setSchedule(temp[plan_name])
                # Add courses to be loaded
                for code in temp[plan_name].keys():
                    planned_course.append(code)
            self.plan_sketches.append(plan)
        self.main_sketch = self.offical_sketch


        # Init main sketch
        # TODO:
        # Show a progress bar during detail loading
        start = time.time()
        schedule = data_manager.loadSchedule(planned_course, self.browser1, self.browser2, self.term)
        end = time.time()
        print "Loading schedule time spent: " + str(end-start)

        section_switch = list()
        session_switch = list()
        for item in schedule:
            temp = {
                'code': item['code'],
                'section': 'unknown',
                'form': item['form'],
                'nbr': item['nbr'],
            }
            if temp['form'] == 'Lecture':
                temp['section'] = item['sess']
            else:
                temp['section'] = re.split('(?<=[-a-zA-Z])[a-zA-Z](?=[0-9])', item['sess'])[0]

            if data_manager.loadCourseData(temp['code'], None, None)['baseform'] == temp['form']:
                section_switch.append(temp)
            else:
                session_switch.append(temp)
        for section in section_switch:
            self.offical_sketch.switchSection(section)
        for session in session_switch:
            self.offical_sketch.switchSession(session)

        self.online_sketch = Sketch(self.timetableTab, None, name='online sketch', copy=self.offical_sketch)

    @QtCore.pyqtSlot(int)
    def switchContext(self, index):
        print 'Context changed to index ' + str(index)
        if index == 0:
            self.main_sketch = self.offical_sketch
        else:
            self.main_sketch = self.plan_sketches[index-1]
        self.scheduleList.switchContext(self.main_sketch)
        self.searchList.switchContext(self.main_sketch)
        self.updateTable()

    def updateTable(self):
        if self.main_sketch == self.offical_sketch:
            self.main_sketch.submitChangeToTable(shopping=True) # distinguish shopping cart course
            # TODO:
            # Add course to shopping cart


        else:
            data_manager.saveSketchesToFile(self.plan_sketches, self.term)
            self.main_sketch.submitChangeToTable()

    def mergeSchedule(self, other):
        self.main_sketch.mergeWith(other)
        self.scheduleList.switchContext(self.main_sketch)
        self.searchList.switchContext(self.main_sketch)

    def refreshData(self):
        pass
        # refresh cache

        # refresh timetable

    def activateContextSwitcher(self, bool):
        if bool == False:
            self.modeBox.setEnabled(False)
            self.modeBox.setToolTip('Close all section window before switch schedule')
        else:
            if self.section_window_count == 0:
                self.modeBox.setEnabled(True)


'''
class PlannerWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initUI()

        self.setFixedSize(PLANNER_WIDTH, TABS_HEIGHT-MAIN_MARGIN_TOP)

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(THIN_GRID_SPACING)
        self.setLayout(grid)

        scheduleArea = QtGui.QScrollArea()
        #scheduleArea.setWidgetResizable(True)
        schedule = ScheduleWidget()
        schedule.setMinimumHeight(PLANNER_LISTITEM_HEIGHT * DEFAULT_VENUENUM + THICK_GRID_SPACING)
        scheduleArea.setWidget(schedule)
        filterArea = QtGui.QScrollArea()
        #filterArea.setWidgetResizable(True)
        filter = FilterWidget()
        filterArea.setWidget(filter)

        grid.addWidget(scheduleArea, 0, 0)
        grid.addWidget(filterArea, 1, 0)

class ScheduleWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # adopt same size like FilterWidget

class FilterWidget(QtGui.QWidget):
    # temperary variables
    valueChanged = 0

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initUI()

    def initUI(self):
        self.resize(PLANNER_WIDTH - 2*THICK_GRID_SPACING, TABS_HEIGHT)

        # not set height?

        grid = QtGui.QGridLayout()
        grid.setSpacing(THICK_GRID_SPACING)
        self.setLayout(grid)

        self.timeList = QtGui.QListWidget(parent=self)
        self.timeList.setMinimumHeight(PLANNER_LISTITEM_HEIGHT * TIMESLOTNUM + THICK_GRID_SPACING)
        self.timeList.connect(self.timeList, QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self, QtCore.SLOT('timeslotChanged(QListWidgetItem*)'))
        self.timeList.connect(self.timeList, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'), self, QtCore.SLOT('timeslotClicked(QListWidgetItem*)'))
        self.timeslot = dict()
        for i in range(TIMESLOTNUM):
            self.timeslot[i] = QtGui.QListWidgetItem(str(i+8) + ":30 ~ " + str(i+9) + ":15")
            self.timeslot[i].setSizeHint(QtCore.QSize(self.timeslot[i].sizeHint().width(), PLANNER_LISTITEM_HEIGHT))
            self.timeslot[i].setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            self.timeslot[i].setCheckState(QtCore.Qt.Checked)
            #self.timeslot[i].connect(self.timeslot[i], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('timeslotChanged(int)'))
            self.timeList.addItem(self.timeslot[i])
        grid.addWidget(self.timeList, 0, 1)
        self.timeslot['selectAll'] = QtGui.QCheckBox("Select all", parent=self)
        self.timeslot['selectAll'].connect(self.timeslot['selectAll'], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('selectAllTimeSlot(int)'))
        self.timeslot['selectAll'].setCheckState(QtCore.Qt.Checked)
        self.timeslot['notMorning'] = QtGui.QCheckBox("No morning classes", parent=self)
        self.timeslot['notMorning'].connect(self.timeslot['notMorning'], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('diselectMorning(int)'))
        self.timeslot['lunchBreak'] = QtGui.QCheckBox("Lunch break", parent=self)
        grid.addWidget(self.timeslot['selectAll'], 0, 0)
        grid.addWidget(self.timeslot['notMorning'], 1, 0)
        grid.addWidget(self.timeslot['lunchBreak'], 2, 0)

        self.venueList = QtGui.QListWidget(parent=self)
        self.venueList.setSortingEnabled(True)
        self.venueList.connect(self.venueList, QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self, QtCore.SLOT('venueslotChanged(QListWidgetItem*)'))
        self.venueList.connect(self.venueList, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'), self, QtCore.SLOT('venueslotClicked(QListWidgetItem*)'))
        self.venueslot = dict()
        with open("data/venue.csv", "r") as csvFile:
            csvReader = csv.reader(csvFile, delimiter=',')
            self.acronym = dict()
            self.keyword = dict()
            self.region = {'MC': [], 'CC': [], 'UC': [], 'NA': [], 'SC': []}
            csvFile.seek(0)
            for item, count in zip(csvReader, range(DEFAULT_VENUENUM)):
                item[1] = item[1].replace("`", ",")
                item[2] = item[2].replace("`", ",")
                self.acronym[item[0]] = item[1]
                self.keyword[item[2]] = item[0]
                if item[3] in self.region.keys():
                    self.region[item[3]] = item[0]
                self.venueslot[item[0]] = QtGui.QListWidgetItem(item[1])
                self.venueslot[item[0]].setSizeHint(QtCore.QSize(self.venueslot[item[0]].sizeHint().width(), PLANNER_LISTITEM_HEIGHT))
                self.venueslot[item[0]].setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                self.venueslot[item[0]].setCheckState(QtCore.Qt.Checked)
                self.venueList.addItem(self.venueslot[item[0]])
        grid.addWidget(self.venueList, 0, 2, TIMESLOTNUM, 1)

    @QtCore.pyqtSlot(int)
    def selectAllTimeSlot(self, state):
        for i in range(TIMESLOTNUM):
            self.timeList.disconnect(self.timeList, QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self, QtCore.SLOT('timeslotChanged(QListWidgetItem*)'))
            self.timeList.disconnect(self.timeList, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'), self, QtCore.SLOT('timeslotClicked(QListWidgetItem*)'))
            self.timeslot['selectAll'].setTristate(False)
            self.timeslot[i].setCheckState(self.timeslot['selectAll'].checkState())
            self.timeList.connect(self.timeList, QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self, QtCore.SLOT('timeslotChanged(QListWidgetItem*)'))
            self.timeList.connect(self.timeList, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'), self, QtCore.SLOT('timeslotClicked(QListWidgetItem*)'))

    @QtCore.pyqtSlot(int)
    def diselectMorning(self, state):
        self.lastState = [QtCore.Qt.Checked for i in range(4)]
        if state == QtCore.Qt.Checked:
            for i in range(4):
                self.lastState[i] = self.timeslot[i].checkState()
                self.timeslot[i].setCheckState(QtCore.Qt.Unchecked)
        else:
            for i in range(4):
                self.timeslot[i].setCheckState(self.lastState[i])

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def timeslotChanged(self, item):
        self.valueChanged = 1
        self.timeslot['selectAll'].disconnect(self.timeslot['selectAll'], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('selectAllTimeSlot(int)'))
        self.timeslot['notMorning'].disconnect(self.timeslot['notMorning'], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('diselectMorning(int)'))
        checked, unchecked = 0, 0
        for i in range(TIMESLOTNUM):
            if self.timeslot[i].checkState() == QtCore.Qt.Unchecked:
                unchecked += 1
            else:
                checked += 1
        if unchecked == TIMESLOTNUM:
            self.timeslot['selectAll'].setCheckState(QtCore.Qt.Unchecked)
        elif checked == TIMESLOTNUM:
            self.timeslot['selectAll'].setCheckState(QtCore.Qt.Checked)
        else:
            self.timeslot['selectAll'].setCheckState(QtCore.Qt.PartiallyChecked)
        for i in range(4):
            if item.checkState() == QtCore.Qt.Checked:
                self.timeslot['notMorning'].setCheckState(QtCore.Qt.Unchecked)
        self.timeslot['notMorning'].connect(self.timeslot['notMorning'], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('diselectMorning(int)'))
        self.timeslot['selectAll'].connect(self.timeslot['selectAll'], QtCore.SIGNAL('stateChanged(int)'), self, QtCore.SLOT('selectAllTimeSlot(int)'))

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def timeslotClicked(self, item):
        if not self.valueChanged:
            item.setCheckState(QtCore.Qt.Checked if item.checkState() == QtCore.Qt.Unchecked else QtCore.Qt.Unchecked)
        self.valueChanged = 0

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def venueslotChanged(self, item):
        self.valueChanged = 1

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def venueslotClicked(self, item):
        if not self.valueChanged:
            item.setCheckState(QtCore.Qt.Checked if item.checkState() == QtCore.Qt.Unchecked else QtCore.Qt.Unchecked)
        self.valueChanged = 0
'''

class SearchField(QtGui.QLineEdit):
    def __init__(self, list_tabs, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        self.list_tabs = list_tabs
        self.initUI()

    def initUI(self):
        self.setGeometry(SEARCH_X, SEARCH_Y, SEARCH_WIDTH, SEARCH_HEIGHT)
        self.setPlaceholderText("Search (e.g. UGFH or German)")
        self.setMaxLength(20)

        layout = QtGui.QHBoxLayout()
        layout.addStretch()
        self.setLayout(layout)

        self.clearButton = ClearButton(self)
        self.clearButton.hide()
        layout.addWidget(self.clearButton)

        self.textChanged.connect(self.textChangedEventHandler)

    def textChangedEventHandler(self):
        self.list_tabs.setCurrentIndex(1)    # Switch to search result tab

        if len(str(self.text())) == 0:
            self.clearButton.hide()
        else:
            self.clearButton.show()

class ClearButton(QtGui.QLabel):
    def __init__(self, searchField):
        QtGui.QLabel.__init__(self, parent=None)

        self.searchField = searchField

        self.resize(10, 10)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        image = QtGui.QImage('img/cross.png')
        image = image.scaled(10, 10)
        self.setPixmap(QtGui.QPixmap.fromImage(image))

    def mousePressEvent(self, event):
        self.searchField.clear()
        event.accept()

class ScheduleList(QtGui.QTableWidget):
    def __init__(self, draft, planner, parent=None):
        QtGui.QTableWidget.__init__(self, parent)
        self.draft_sketch = draft
        self.planner = planner

        self.codes = list()
        self.sketch = None  # to be init in self.switchContext
        self.openedSectionWidget = dict()

        self.initUI()

    def initUI(self):
        self.setGeometry(LIST_X, LIST_Y, LIST_WIDTH, LIST_HEIGHT)
        self.setRowCount(0)
        self.setColumnCount(3)
        self.verticalHeader().setResizeMode(QtGui.QHeaderView.Fixed)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.cellClicked.connect(self.showSectionInfo)
        #self.setStyleSheet("QTableView::item {padding: 5px;}")
        #self.connect(self, QtCore.SIGNAL('cellClicked(int, int)'), self, QtCore.SLOT('showSectionInfo()'))

    def switchContext(self, main_sketch):
        self.main_sketch = main_sketch
        self.codes = sorted(main_sketch.getSchedule().keys())
        self.setRowCount(0)
        self.showCourseList()

    def showCourseList(self):
        catalog = data_manager.loadCatalog()
        for code in self.codes:
            name = None
            for course in catalog:
                if code[:4] == course[0] and code[4:] == course[2]:
                    name = course[3]
                    break
            if name == None:
                print 'Error: Unrecognizable course code (not in catalog): ' + code
                return

            self.setRowCount(self.rowCount()+1)

            # Text column
            display_text = '<div>' + code + '<br/>' + name + '</div>'
            courseItem = QtGui.QLabel(display_text)
            courseItem.setWordWrap(True)
            courseItem.setMargin(6)
            self.setCellWidget(self.rowCount()-1, 0, courseItem)
            self.setRowHeight(self.rowCount()-1, int(courseItem.sizeHint().height() * 1.3))

            # Action column 1
            viewDetail = QtGui.QLabel()
            viewDetail.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            image = QtGui.QImage('./img/setting.ico')
            image = image.scaled(ICON_SIZE, ICON_SIZE)
            viewDetail.setMargin(ICON_MARGIN)
            viewDetail.setPixmap(QtGui.QPixmap.fromImage(image))
            viewDetail.setToolTip('Edit')
            self.setCellWidget(self.rowCount()-1, 1, viewDetail)

            # Action column 2
            deleteCourse = QtGui.QLabel()
            deleteCourse.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            image = QtGui.QImage('./img/cross_2.png')
            image = image.scaled(ICON_SIZE, ICON_SIZE)
            deleteCourse.setMargin(ICON_MARGIN)
            deleteCourse.setPixmap(QtGui.QPixmap.fromImage(image))
            deleteCourse.setToolTip('Remove')
            self.setCellWidget(self.rowCount()-1, 2, deleteCourse)

        self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)

        # Post-search cell size adjustment
        self.setColumnWidth(1, ICON_SIZE + ICON_MARGIN * 2)
        self.setColumnWidth(2, ICON_SIZE + ICON_MARGIN * 2)

        self.scrollToTop()

    @QtCore.pyqtSlot(int, int)
    def showSectionInfo(self, row, col):
        if col == 1:
            self.openSectionWindow(self.codes[row])

        elif col == 2:
            code = self.codes[row]

            msgBox = QtGui.QMessageBox(self.planner)
            msgBox.setIcon(QtGui.QMessageBox.Information)
            msgBox.setWindowTitle('Are you sure?')
            msgBox.setText('Course ' + code + ' will be removed from your current schedule.')
            msgBox.setInformativeText('This action is irrevocable.')
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
            ret = msgBox.exec_()

            # Remove course from list and table
            if ret == QtGui.QMessageBox.Ok:
                self.removeRow(row)
                del self.main_sketch.getSchedule()[code]
                del self.codes[row]
                self.planner.updateTable()
                self.planner.searchList.switchContext(self.planner.main_sketch)

    def openSectionWindow(self, code):
        if code in self.openedSectionWidget:
            self.openedSectionWidget[code].raise_()
            self.openedSectionWidget[code].activateWindow()
        else:
            data = data_manager.loadCourseData(code, None, None)

            # Create section widget
            section_window = SectionWidget(code, self.draft_sketch, action=0, parent=self.planner, flags=QtCore.Qt.Window)
            section_window.showLoadingGUI()
            section_window.show()
            section_window.setData(data)

            self.openedSectionWidget[code] = section_window
            section_window.connect(section_window, QtCore.SIGNAL('destroyed()'), lambda: self.openedSectionWidget.pop(code))

            # Check selected component in section widget
            schedule = self.main_sketch.getSchedule()
            section_window.checkCourse(schedule, code, data['baseform'])


class SearchList(QtGui.QTableWidget):
    def __init__(self, browser1, browser2, draft, searchField, status_bar, planner, parent=None):
        QtGui.QTableWidget.__init__(self, parent)

        self.browser1 = browser1
        self.browser2 = browser2
        self.draft_sketch = draft
        self.searchField = searchField
        self.status_bar = status_bar
        self.planner = planner

        self.validRowNumber = -1
        self.openedSectionWidget = dict()

        self.initUI()

    def initUI(self):
        self.setGeometry(LIST_X, LIST_Y, LIST_WIDTH, LIST_HEIGHT)
        self.setRowCount(0)
        self.setColumnCount(2)
        self.verticalHeader().setResizeMode(QtGui.QHeaderView.Fixed)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.connect(self, QtCore.SIGNAL('cellClicked(int, int)'),
            lambda: self.showSectionInfo(self.currentRow()))

    @QtCore.pyqtSlot(str)
    def updateSearchResult(self, search_entry):
        for _ in range(self.rowCount()):
            self.removeRow(0)

        searchResultNum = 0
        self.code = list()
        self.name = list()
        self.entries = list()
        self.searchTextLen = list()
        tempList = list()

        # Searching algorithm and display implementation
        searchText = str(search_entry).strip()
        if re.match('[\-+\w]{1,}', searchText):
            # TODO 1
            # Improve search speed

            # TODO 2
            # Search filter

            # TODO 3
            # Responsive loading - show more results when the list is scrolled to the bottom


            # Searching courses in catalog by brute force
            courseSet = set()
            for course in data_manager.loadCatalog():
                entry = (course[0] + course[2], course[3])
                if entry[0] not in courseSet:
                    courseSet.add(entry[0])
                    for i in range(2):
                        match = entry[i].lower().find(str(searchText).lower())
                        if match != -1:
                            tempList.append((searchResultNum, i, match, entry[0], entry[1]))
                            self.entries.append(entry)
                            self.searchTextLen.append(len(searchText))
                            searchResultNum += 1
                            break

            # Sort search result by course code (matching from the start first) and then by course name
            self.sortedIndex = sorted(tempList, key=itemgetter(1,2))
            if len(self.sortedIndex) > 0:
                self.code, self.name = zip(*self.sortedIndex)[3:]

            self.validRowNumber = -1
            self.extendList()
            self.scrollToTop()

    def extendList(self):
        # Sorted result display
        self.setRowCount(self.validRowNumber + 1)
        rowNum = 0
        for i, part, pos, code, name in self.sortedIndex[self.validRowNumber+1:]:
            # Course title column
            self.setRowCount(self.validRowNumber + 2)
            courseItem = QtGui.QLabel()
            display_text =\
                "<div>"+self.entries[i][0][:pos]+\
                "<font color='Blue'>"+self.entries[i][0][pos:pos+self.searchTextLen[i]]+"</font>"+\
                self.entries[i][0][pos+self.searchTextLen[i]:]+'<br/>'+self.entries[i][1]+"</div>"\
                if part == 0 else\
                "<div>"+self.entries[i][0]+'<br/>'+self.entries[i][1][:pos]+\
                "<font color='Blue'>"+self.entries[i][1][pos:pos+self.searchTextLen[i]]+"</font>"+\
                self.entries[i][1][pos+self.searchTextLen[i]:]+"</div>"
            courseItem.setText(display_text)
            courseItem.setWordWrap(True)
            courseItem.setMargin(6)
            self.setRowHeight(self.validRowNumber+1, int(courseItem.sizeHint().height() * 1.3))
            self.setCellWidget(self.validRowNumber + 1, 0, courseItem)

            # Action column
            viewDetail = QtGui.QLabel()
            viewDetail.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            if code in self.planner.main_sketch.getSchedule():
                image = QtGui.QImage('./img/setting.ico')
                viewDetail.setToolTip('Edit')
            else:
                image = QtGui.QImage('./img/add_sign.ico')
                viewDetail.setToolTip('Add')
                # TODO
                # Set icons for other actions




            image = image.scaled(ICON_SIZE, ICON_SIZE)
            viewDetail.setMargin(ICON_MARGIN)
            viewDetail.setPixmap(QtGui.QPixmap.fromImage(image))
            self.setCellWidget(self.validRowNumber + 1, 1, viewDetail)

            self.validRowNumber += 1
            rowNum += 1
            # This limit number of courses to be listed
            if rowNum >= SEARCH_RESULT_BLOCK_LENGTH:
                break

        self.setRowCount(self.validRowNumber + 2)
        if self.validRowNumber + 1 == len(self.sortedIndex):
            self.allListed = True
            temp = QtGui.QTableWidgetItem('No more results')
            self.setItem(self.validRowNumber + 1, 0, temp)
            self.setRowHeight(self.validRowNumber + 1, 50)
        else:
            self.allListed = False
            temp = QtGui.QTableWidgetItem('Show more results')
            self.setItem(self.validRowNumber + 1, 0, temp)
            self.setRowHeight(self.validRowNumber + 1, 50)
        self.setSpan(self.validRowNumber + 1, 0, 1, 2)

        self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)

        # Post-search cell size adjustment
        self.setColumnWidth(1, ICON_SIZE + ICON_MARGIN * 2)



    def showSectionInfo(self, index):
        if index > self.validRowNumber:
            if self.allListed == True:  # no matched searching results
                return
            else:    # show more results
                self.extendList()
                return

        code = self.code[index]
        if code in self.planner.main_sketch.getSchedule():
            self.planner.scheduleList.openSectionWindow(code)
        else:
            # Cope with the attempts to open multiple section windows of the same courses
            if code in self.openedSectionWidget:
                self.openedSectionWidget[code].raise_()
                self.openedSectionWidget[code].activateWindow()
            else:
                # Disable list to prevent over-threading
                self.searchField.setEnabled(False)
                self.setEnabled(False)

                section_window = SectionWidget(code, self.draft_sketch, action=1, parent=self.planner, flags=QtCore.Qt.Window)
                section_window.showLoadingGUI()
                section_window.show()

                self.openedSectionWidget[code] = section_window
                section_window.connect(section_window, QtCore.SIGNAL('destroyed()'), lambda: self.openedSectionWidget.pop(code))

                # Check if a course is available
                cache_status = data_manager.cachedCourseIsAvailable(code)
                if cache_status == True:        # Cached course data is available
                    open_status = True
                elif cache_status == False:     # There is cached information showing that the course is unavailable
                    open_status = False
                elif cache_status == None:      # No information in cache
                    open_status = data_manager.loadOpenStatus(code, self.browser1)
                else:
                    print "Error: Unknown cache status: " + cache_status
                    exit(1)

                # Load course data from data_manager
                if open_status == True:
                    start = time.time()
                    self.data = data_manager.loadCourseData(code, self.browser1, self.browser2)
                    end = time.time()
                    print "Loading data time spent: " + str(end-start)
                    if self.data == config.NETWORK_ERROR:
                        section_window.showUnavailableDialog('Error', 'Failed to connect to CUSIS, please check your Internet connection.')
                    else:
                        # TODO
                        # Use another thread to set data display in the table
                        # and replace loading GUI with the complete table after the setting is done





                        section_window.setData(self.data)
                        self.status_bar.showMessage('Loading complete', 3000)
                elif open_status == False:
                    data_manager.setCachedCourseUnavailable(code)
                    self.status_bar.showMessage('Course ' + code + ' not available', 3000)
                    section_window.showUnavailableDialog('Info', code + " is unavailable this term")
                elif open_status == config.NETWORK_ERROR:
                    section_window.showUnavailableDialog('Error', 'Failed to connect to CUSIS, please check your Internet connection.')
                else:
                    print "Error: Unknown open status: " + open_status
                    exit(1)

        # Enable list
        self.searchField.setEnabled(True)
        self.setEnabled(True)

    def switchContext(self, main_sketch):
        self.main_sketch = main_sketch
        self.updateSearchResult(self.planner.searchField.text())

if __name__ == "__main__":
    print "No test available"
