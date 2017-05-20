# -*- coding: utf-8 -*-
import sys, json, re, time

from PyQt4 import QtGui, QtCore

import data_manager

class SmartTable(QtGui.QTableWidget):
    INT_WEEKDAYS = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
    WEEKDAYS_INT = {"Mo": 1, "Tu": 2, "We": 3, "Th": 4, "Fr": 5, "Sa": 6, "Su": 7}

    # TODO:
    # Figure out a color scheme distinguish online table from local plans






    SLOT_STATUSCOLOR = {
        "Enrolled": QtGui.QColor(144, 238, 144),        # LightGreen
        "Waiting": QtGui.QColor(173, 255, 47),          # GreenYellow
        "Open": QtGui.QColor(144, 238, 144),            # LightGreen
        "Closed": QtGui.QColor(255,165,0),              # Orange
        "Cart-Open": QtGui.QColor(230, 230, 250),       # Lavender
        "Cart-Waiting": QtGui.QColor(230, 230, 250),    # Lavender
        "Cart-Closed": QtGui.QColor(255,165,0),         # Orange
        "Conflict": QtGui.QColor(255, 99, 71)           # Tomato
    }

    TIP_STATUSCOLOR = {
        "Open": "LightGreen",
        "Enrolled": "LightGreen",
        "Waiting": "GreenYellow",
        "Closed": "Orange"
    }

    TABLE_SIZE = (1200.0, 800.0)

    ROW_NUM = 15
    COL_NUM = 8

    ROW_HEIGHT = TABLE_SIZE[1] / ROW_NUM
    COL_WIDTH = TABLE_SIZE[0] / COL_NUM

    def __init__(self, parent=None):
        QtGui.QTableWidget.__init__(self, parent)

        self.initUI()

    def initUI(self):
        # Table settings
        self.setFixedSize(self.TABLE_SIZE[0], self.TABLE_SIZE[1])
        self.setRowCount(self.ROW_NUM)
        self.setColumnCount(self.COL_NUM)

        self.setShowGrid(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        # Grid spacing
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        # Add padding to cells (Waring: adding new styles may destroy the table display)
        self.setStyleSheet("QTableWidget::item { padding: 10px; }")

        # testing
        self.connect(self, QtCore.SIGNAL('itemClicked(QTableWidgetItem*)'), self, QtCore.SLOT('showItemInfo(QTableWidgetItem*)'))

    # Table item clicked reaction
    @QtCore.pyqtSlot(QtGui.QTableWidgetItem)
    def showItemInfo(self, item):
        row, col = item.row(), item.column()
        pos_x = self.columnViewportPosition(col) + self.mapToGlobal(self.pos()).x() + self.columnWidth(item.column())
        pos_y = self.rowViewportPosition(row) + self.mapToGlobal(self.pos()).y()
        course = self.courseGrid[row][col]
        if len(course) == 0: return
        else: course = course[0]

        cart_label = " <font color='blue'>(Shopping Cart)</font>"
        if len(self.conflictGrid[row][col]) > 1:
            info = "<font color='red'><u>Time conflict:</u></font>"
            for course in self.courseGrid[row][col]:
                status = course['stat'].split('-')
                info += "<br/><b>" + course['code'] + " - " + course['sess'] +\
                        "</b>" + (cart_label if len(status) == 2 else '') +\
                        "<br/>" + course['name']
                info += "<br/>Time: <i>" + course['time'] + "</i>"
                info += "<br/>" + course['form'] + "@" + course['venue']
        else:
            status = course['stat'].split('-')
            info = "<b>" + course['code'] + " - " + course['sess'] +\
                   "</b>" + (cart_label if len(status) == 2 else '') +\
                   "<br/>" + course['name']
            info += "<br/>" + course['form'] + "@" + course['venue']
            info += "<br/>by <i>" + course['instructor'] + "</i>"
            status = status[1 if len(status) == 2 else 0]

            # TODO: Detail information should be loaded from Browser in Planner.py
            if status == 'Open':
                # Class availibility
                # Class capacity
                pass
            elif status == 'Waiting':
                # Waitlist position
                # Waitlist capacity
                # Class capacity
                pass
            elif status == 'Closed':
                info += "<br/><br/><u>" + "Double click the class to find other available sections" + "</u>"
                pass
            else:
                pass

            info += "<br/><br/><b>Status: <font color='" + self.TIP_STATUSCOLOR[status] + "'>" + status + "</font></b>"
        QtGui.QToolTip.showText(QtCore.QPoint(pos_x, pos_y), info)

    def switchContext(self):
        pass

    # Load class schedule from file and then display
    def loadTimetable(self, schedule):
        #print schedule
        start = time.time()
        self.setRowCount(0)
        self.setRowCount(self.ROW_NUM)

        # TODO:
        # Check if there are same courses in self.data and draft


        self.setTableUI(schedule)
        #self.setTableUI(self.course_list)
        end = time.time()
        #print "Table set-up time spent: " + str(end-start)


    def setTableUI(self, course_data):
        # TODO:
        # Display draft in blue color font









        # Table headers
        for column in range(1, self.COL_NUM):
            dayItem = SmartTableItem(self.INT_WEEKDAYS[column])
            dayItem.setTextAlignment(QtCore.Qt.AlignCenter)
            dayItem.setBackground(QtCore.Qt.cyan)
            self.setItem(0, column, dayItem)
        for row in range(1, self.ROW_NUM):
            timeItem = SmartTableItem(str(row+7)+":30")
            timeItem.setTextAlignment(QtCore.Qt.AlignHCenter)
            timeItem.setBackground(QtCore.Qt.cyan)
            self.setItem(row, 0, timeItem)

        OFFSET = lambda time: -7 if re.search('AM', time) or re.search('12', time) else 5
        TIMESLOT = lambda time: int(re.search('[1-9][0-9]?(?=:)', time).group(0)) + OFFSET(time)

        # Data structure for confilct detection
        self.conflictGrid = [[set() for c in range(self.COL_NUM)] for r in range(self.ROW_NUM)]
        self.courseGrid = [[[] for c in range(self.COL_NUM)] for r in range(self.ROW_NUM)]

        for course in course_data:
            if (course['day'] == '-' or course['time'] == '-'):
                continue

            startRow, endRow = map(TIMESLOT, course['time'].split(' - '))
            col = self.WEEKDAYS_INT[course['day']]

            for row in range(startRow, endRow):
                self.conflictGrid[row][col].add(course['code'] + ' ' + course['sess'] + ':' + course['nbr'])
                self.courseGrid[row][col].append(course)

        # Add class item to table with conflict display handled
        courseSlot = None
        courseRow = None
        for col in range(self.COL_NUM):
            for row in range(self.ROW_NUM):
                if courseSlot:  # there is a class right before this timeslot
                    if courseSlot == self.conflictGrid[row][col]:   # the two consecutive timeslots are occupied by the same class
                        courseRow[1] += 1
                    else:
                        classItem = SmartTableItem('')
                        classItem.setTextAlignment(QtCore.Qt.AlignCenter)
                        if len(courseSlot) == 1:    # non-conflict slot
                            course = self.courseGrid[courseRow[0]][col][0]
                            classItem.setText(course['code'] + ' ' + course['sess'] + '\n' + course['form'])
                            classItem.setBackground(self.SLOT_STATUSCOLOR[self.courseGrid[courseRow[0]][col][0]['stat']])
                        else:   # conflict slots
                            classItem.setText('\n'.join(map(lambda s: s.split(':')[0], courseSlot)))
                            classItem.setBackground(self.SLOT_STATUSCOLOR["Conflict"])
                        self.setItem(courseRow[0], col, classItem)
                        if courseRow[1] - courseRow[0] > 1:
                            self.setSpan(courseRow[0], col, courseRow[1] - courseRow[0], 1)
                        if len(self.conflictGrid[row][col]) > 0:    # entering new conflict slot
                            courseSlot = self.conflictGrid[row][col]
                            courseRow = [row, row+1]
                        else:
                            courseSlot = None
                            courseRow = None
                else:
                    if len(self.conflictGrid[row][col]) > 0:
                        courseSlot = self.conflictGrid[row][col]
                        courseRow = [row, row+1]

        self.clearTable()

    # Remove empty rows and columns at the table rim
    def clearTable(self):
        # remove Sat and Sun column if empty
        for i in range(2):
            day = 6
            is_empty = 1
            for row in range(1, self.ROW_NUM):
                if self.item(row, day):
                    is_empty = 0
                    break
            if is_empty:
                self.removeColumn(day)
                self.COL_NUM -= 1

        # remove evening time row if empty
        for row in range(self.ROW_NUM - 1, 11, -1):
            is_empty = 1
            for col in range(1, self.COL_NUM):
                if self.item(row, col):
                    is_empty = 0
                    break
            if is_empty:
                self.removeRow(row)
                self.ROW_NUM -= 1
            else:
                break

        self.ROW_HEIGHT = self.TABLE_SIZE[1] / self.ROW_NUM
        self.COL_WIDTH = self.TABLE_SIZE[0] / self.COL_NUM

    # Refresh table with data from CUSIS
    def refreshTable(self):
        pass


class SmartTableItem(QtGui.QTableWidgetItem):
    def __init__(self, text, type=0):
        QtGui.QTableWidgetItem.__init__(self, text, type)
        self.initUI()

    def initUI(self):
        pass


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    tempWidget = QtGui.QWidget()
    tempWidget.setFixedSize(1200.0, 800.0)
    with open('data/data.json') as jsonFile:
        schedule = json.load(jsonFile)
    smartTable = SmartTable(tempWidget)
    smartTable.loadTimetable(schedule)
    tempWidget.show()
    sys.exit(app.exec_())
