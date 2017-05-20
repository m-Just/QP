# -*- coding: utf-8 -*-
import sys, json, re, copy

from PyQt4 import QtGui, QtCore

from sketch import Sketch

THIN_GRID_SPACING = 10

TABLE_SIZE = (600, 400)
TABLE_COL_COUNT = 3
TABLE_COL_SPAN = {'section': TABLE_COL_COUNT, 'form': 1, 'status': 1, 'class': 1}
TABLE_COL_START = {'section': 0, 'form': 0, 'status': 1, 'class': 2}

HYPHEN_SPLIT = '-'

class SectionWidget(QtGui.QWidget):
    def __init__(self, code, sketch, action, parent=None, flags=QtCore.Qt.Widget):
        QtGui.QWidget.__init__(self, parent, flags)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)       # Remove qt object from memory when closing

        self.sketch = sketch
        self.action = action
        self.local_sketch = Sketch(None, None, name='local sketch')
        self.parent_widget = parent
        self.parent_widget.section_window_count += 1
        self.parent_widget.activateContextSwitcher(False)

        temp = ['Shopping Cart', 'Plan A', 'Plan B', 'Plan C']
        self.name = temp[self.parent_widget.modeBox.currentIndex()]

        self.setWindowTitle('Section Window - ' + code)

        self.course = None
        self.backup_sketch = None
        self.initUI()

    def initUI(self):
        # UI settings
        self.setMinimumSize(*TABLE_SIZE)

        # Children widget
        if self.action == 0:
            self.confirm_button = QtGui.QPushButton("Confirm")
        elif self.action == 1:
            self.confirm_button = QtGui.QPushButton("Add to " + self.name)
        else:
            self.confirm_button = QtGui.QPushButton("Confirm")
        self.confirm_button.setEnabled(False)
        self.confirm_button.connect(self.confirm_button, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("createEntry()"))
        self.help = HelpMessage("This is a help message", self, self.confirm_button)
        self.table = SectionTable(self.help, self.sketch, self.local_sketch, self.parent_widget, self)

            # Filter
                # Show open-only, non-morning class, etc.

        # Layout
        grid = QtGui.QGridLayout()
        grid.setSpacing(THIN_GRID_SPACING)

        grid.addWidget(self.help, 0, 0, 1, 4)
        grid.addWidget(self.confirm_button, 0, 4, 1, 1)
        grid.addWidget(self.table, 1, 0, 1, 5)

        self.setLayout(grid)

    def setData(self, data):
        self.help.setData(data)
        self.table.setData(data)

    def showLoadingGUI(self):
        self.help.showLoadingGUI()
        self.table.showLoadingGUI()

    def showUnavailableDialog(self, title, message):
        msgBox = QtGui.QMessageBox(self)
        msgBox.setIcon(QtGui.QMessageBox.Information)
        msgBox.setWindowTitle(title)
        msgBox.setText(message)
        msgBox.exec_()
        self.close()

    def checkCourse(self, schedule, code, baseform):
        course = schedule[code]
        section_item = self.table.all_items[course['section']][baseform][course['classes'][baseform]]

        section_item.setCheckState(QtCore.Qt.Checked)
        self.table.selected_section = section_item

        info = { baseform: course['section'] }

        # Set all session item checkable
        for form in self.table.section_items[section_item].keys():
            for session_item in self.table.section_items[section_item][form]:
                session_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)

        # Check the selected session
        for form in course['classes'].keys():
            if not form == baseform:
                session_item = self.table.all_items[course['section']][form][course['classes'][form]]
                temp = str(session_item.text()).split(HYPHEN_SPLIT)

                info[temp[0]] = temp[1]

                session_item.setCheckState(QtCore.Qt.Checked)
                self.table.selected_session[temp[0]] = temp[1]

        self.help.updateInfo(info)

        # Move course entry being editted from main_sketch to draft
        self.sketch.getSchedule()[code] = copy.deepcopy(course)
        self.local_sketch.getSchedule()[code] = copy.deepcopy(course)
        self.backup_sketch = copy.deepcopy(self.sketch) # Memorize the section and session once selected before edit
        del schedule[code]

    # TODO
    # Pass selected course for further process (like add to shopping cart)
    def setSelectedCourse(self, course):
        self.course = course










    # Note:
    # If section window is closed by clicking the confirm button,
    # then createEntry would be called before removeFromDraft is called

    @QtCore.pyqtSlot()
    def createEntry(self):
        print "Confirm clicked"
        self.backup_sketch = None
        self.parent_widget.mergeSchedule(self.local_sketch)
        self.close()

    def closeEvent(self, event):    # This is a override method
        if not self.backup_sketch == None:
            self.parent_widget.main_sketch.mergeWith(self.backup_sketch)
        for key, value in self.local_sketch.getSchedule().items():
            self.sketch.removeSection({'code': key, 'section': value['section']})
        self.parent_widget.updateTable()
        self.parent_widget.section_window_count -= 1
        self.parent_widget.activateContextSwitcher(True)
        event.accept()

class HelpMessage(QtGui.QLabel):
    def __init__(self, text, widget, confirm):
        QtGui.QLabel.__init__(self, text)
        self.widget = widget
        self.confirm = confirm
        self.initUI()

    def initUI(self):
        pass

    def showLoadingGUI(self):
        self.setText('Loading course data from CUSIS, please wait')

    def setData(self, data):
        temp = data['sections'].keys()[0]
        self.forms = data['sections'][temp]['classes'].keys()
        self.baseform = data['baseform']
        self.setText('Please select a section first')

    def updateInfo(self, info):
        self.baseInfo = info
        forms_list = ["Section" + (' ' + info[self.baseform] if self.baseform in info else " <font color='red'>not selected</font>")]
        for form in self.forms:
            if not form == self.baseform:
                forms_list.append(form + (' ' + info[form] if form in info else " <font color='red'>not selected</font>"))
        self.setText(' > '.join(forms_list))

        # If all the conditions are met
        if len(self.forms) == len(info.keys()):
            self.widget.setSelectedCourse(info)
            self.confirm.setEnabled(True)
        else:
            self.confirm.setEnabled(False)

    def addInfo(self, info):
        for key, value in info.items():
            self.baseInfo[key] = value
        self.updateInfo(self.baseInfo)

    def removeInfo(self, info):
        for key, value in info.items():
            self.baseInfo.pop(key, None)
        self.updateInfo(self.baseInfo)

class SectionTable(QtGui.QTableWidget):

    # TODO1: Show requirements and attributes in tooltip
    # TODO2: Implement filter
    # TODO3: Check if section selected is closed or not






    def __init__(self, help, sketch, local_sketch, planner, parent=None):
        QtGui.QTableWidget.__init__(self, parent)
        self.help = help
        self.sketch = sketch
        self.local_sketch = local_sketch
        self.planner = planner

        # These two variable holds last selection, in order to verify,
        # if the user clicked exactly on the checkbox or not,
        # for there is only itemClicked() SIGNAL but no checkStateChange() SIGNAL in Qt4,
        # thus, when the user clicked on the area apart from the checkbox of an unchecked item,
        # there would be undesired issues if the difference is not handled.
        self.selected_section = None
        self.selected_session = dict()

        self.initUI()

    def initUI(self):
        # UI settings
        self.resize(*TABLE_SIZE)
        self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        #self.setStyleSheet("QTableWidget::item:hover { color: black; background-color: lavender; }")

        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

    def showLoadingGUI(self):
        # Display loading GUI
        self.setRowCount(1)
        self.setColumnCount(1)

        loadingLabel = QtGui.QLabel(self)
        loadingLabel.setAlignment(QtCore.Qt.AlignCenter)
        loadingIcon = QtGui.QMovie("img/loading4.gif")
        loadingIcon.setScaledSize(QtCore.QSize(300, 300))
        loadingLabel.setMovie(loadingIcon)
        loadingIcon.start()

        self.setCellWidget(0, 0, loadingLabel)

        self.setCurrentCell(-1, -1)

    def switchContext(self, table):
        self.timetable = table

    def setData(self, data):
        self.data = data

        self.setRowCount(0)
        self.setColumnCount(0)
        self.setColumnCount(TABLE_COL_COUNT)

        # Selection signal connect
        self.connect(self, QtCore.SIGNAL('itemClicked(QTableWidgetItem*)'), self, QtCore.SLOT('checkSection(QTableWidgetItem*)'))

        StatusColor = {
            "Open": "LightGreen",
            "Enrolled": "LightGreen",
            "Waiting": "GreenYellow",
            "Closed": "Orange"
        }

        # Reference structures
        self.all_items = dict()         # all_items : {section_code: {form: {nbr: session_item or section_item}}}
        self.section_items = dict()     # section_items : {session_forms : [session_item]}
        self.session_items = dict()     # session_items : map to the parent of session_item in section_items
        self.classData = dict()         # store the class data (course code, section code, form and nbr) of each checkable item

        self.info_items = list()        # table widget item used to display read-only uncheckable information

        section_num = len(self.data['sections'])

        # Cell items
        for section_code, section in sorted(self.data['sections'].items()):
            section_len = 0
            classes = section['classes']
            base_class = classes[self.data['baseform']].values()[0]
            base_class_count = len(base_class['time'])

            section_item = QtGui.QTableWidgetItem(section_code + ' section')
            section_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            section_item.setCheckState(QtCore.Qt.Unchecked)
            self.section_items[section_item] = dict()
            self.all_items[section_code] = {self.data['baseform']: {base_class['nbr']: section_item}}
            self.classData[section_item] = {
                'code': self.data['code'],
                'section': section_code,
                'form': self.data['baseform'],
                'nbr': base_class['nbr'],
            }

            info_label_item = QtGui.QTableWidgetItem('Information')
            lang_label_item = QtGui.QTableWidgetItem('Language')
            inst_label_item = QtGui.QTableWidgetItem('Instructor')
            self.info_items.append(info_label_item)
            self.info_items.append(lang_label_item)
            self.info_items.append(inst_label_item)

            lang = self.data['sections'][section_code]['language']
            if lang[0] == '&':
                language = ' & '.join(lang[1:])
            elif lang[0] == '#':
                language = lang[1] + ', change to ' + lang[2] + ' if needed'
            else:
                language = ''.join(lang[1:])
            language_item = QtGui.QTableWidgetItem(language)
            self.info_items.append(language_item)

            instructor_item = QtGui.QTableWidgetItem(', '.join(section['instructor']))
            self.info_items.append(instructor_item)

            info_icon = QtGui.QIcon("img/info-icon.png")
            #icon_item =  QtGui.QTableWidgetItem()
            #section_item.setIcon(info_icon)

            self.setRowCount(self.rowCount() + 3)
            self.setItem(self.rowCount() - 3, TABLE_COL_START['section'], section_item)
            self.setSpan(self.rowCount() - 3, TABLE_COL_START['section'], 1, TABLE_COL_SPAN['section'])

            self.setItem(self.rowCount() - 2, TABLE_COL_START['form'], info_label_item)
            self.setSpan(self.rowCount() - 2, TABLE_COL_START['form'], 2, TABLE_COL_SPAN['form'])

            self.setItem(self.rowCount() - 2, TABLE_COL_START['status'], lang_label_item)
            self.setItem(self.rowCount() - 1, TABLE_COL_START['status'], inst_label_item)

            self.setItem(self.rowCount() - 2, TABLE_COL_START['class'], language_item)
            self.setItem(self.rowCount() - 1, TABLE_COL_START['class'], instructor_item)

            self.setRowCount(self.rowCount() + base_class_count)
            rowRange = range(self.rowCount() - base_class_count, self.rowCount())

            for row, day, time, venue in zip(rowRange, base_class['day'], base_class['time'], base_class['venue']):
                time_venue_item = QtGui.QTableWidgetItem(self.timeVenueTBATest(day, time, venue))
                self.info_items.append(time_venue_item)
                self.setItem(row, TABLE_COL_START['class'], time_venue_item)
            baseform_label_item = QtGui.QTableWidgetItem(self.data['baseform'])
            self.info_items.append(baseform_label_item)
            self.setItem(rowRange[0], TABLE_COL_START['form'], baseform_label_item)
            self.setCellWidget(rowRange[0], TABLE_COL_START['status'], QtGui.QLabel("&nbsp;&nbsp;<font color='" + StatusColor[base_class['status']] + "'>" + base_class['status'] + "</font>&nbsp;&nbsp;"))

            if len(rowRange) > 1:
                self.setSpan(rowRange[0], TABLE_COL_START['form'], len(rowRange), self.columnSpan(rowRange[0], TABLE_COL_START['form']))
                self.setSpan(rowRange[0], TABLE_COL_START['status'], len(rowRange), self.columnSpan(rowRange[0], TABLE_COL_START['status']))
            section_len += len(rowRange)

            for form, class_  in classes.items():
                if form == self.data['baseform']:
                    continue
                else:
                    session_count = len(class_)
                    for num, session in sorted(class_.items()):
                        sub_count = len(session['time'])
                        self.setRowCount(self.rowCount() + sub_count)
                        rowRange = range(self.rowCount() - sub_count, self.rowCount())

                        for row, day, time, venue in zip(rowRange, session['day'], session['time'], session['venue']):
                            time_venue_item = QtGui.QTableWidgetItem(self.timeVenueTBATest(day, time, venue))
                            self.info_items.append(time_venue_item)
                            self.setItem(row, TABLE_COL_START['class'], time_venue_item)
                            #self.setSpan(row, TABLE_COL_START['class'], 1, TABLE_COL_SPAN['class'])
                        session_item = QtGui.QTableWidgetItem(form + HYPHEN_SPLIT + num)
                        self.setItem(rowRange[0], TABLE_COL_START['form'], session_item)
                        session_item.setFlags(QtCore.Qt.ItemIsUserCheckable)
                        session_item.setCheckState(QtCore.Qt.Unchecked)
                        if form in self.all_items[section_code]:
                            self.all_items[section_code][form][session['nbr']] = session_item
                        else:
                            self.all_items[section_code][form] = {session['nbr']: session_item}
                        self.classData[session_item] = {
                            'code': self.data['code'],
                            'section': section_code,
                            'form': form,
                            'nbr': session['nbr'],
                        }

                        if form not in self.section_items[section_item]:
                            self.section_items[section_item][form] = list()
                        self.section_items[section_item][form].append(session_item)
                        self.session_items[session_item] = self.section_items[section_item][form]

                        self.setCellWidget(rowRange[0], TABLE_COL_START['status'], QtGui.QLabel("&nbsp;&nbsp;<font color='" + StatusColor[session['status']] + "'>" + session['status'] + "</font>&nbsp;&nbsp;"))
                        #self.setSpan(rowRange[0], TABLE_COL_START['form'], 1, TABLE_COL_SPAN['form'])
                        if len(rowRange) > 1:
                            self.setSpan(rowRange[0], TABLE_COL_START['form'], len(rowRange), self.columnSpan(rowRange[0], TABLE_COL_START['form']))
                        section_len += len(rowRange)

    def timeVenueTBATest(self, day, time, venue):
        if day == '-' and time == '-':
            if venue == 'TBA': temp = 'Class time and venue to be announced (TBA)'
            else: temp = '(Class time to be announced) @ ' + venue
        elif venue == 'TBA': temp = day + ' ' + time + ' @ ' + 'Class venue to be announced'
        else: temp = day + ' ' + time + ' @ ' + venue
        return temp

    @QtCore.pyqtSlot(QtGui.QTableWidgetItem)
    def checkSection(self, item):
        if item in self.info_items: return      # check if the item is checkable or read-only
        # Section(Lecture) checked/unchecked
        if self.columnSpan(item.row(), item.column()) == TABLE_COL_SPAN['section']:
            if item.checkState() == QtCore.Qt.Checked:  # Signal is emitted after check state has already changed
                self.selected_section = item
                self.sketch.switchSection(self.classData[item])
                self.local_sketch.switchSection(self.classData[item])

                helpMessage = dict()
                helpMessage[self.data['baseform']] = str(item.text()).split(' ')[0]

                for section in self.section_items.keys():
                    if section == item:
                        for session_forms in self.section_items[section].values():
                            # Enable sessions
                            for session in session_forms:
                                if session.checkState() == QtCore.Qt.Checked:
                                    self.sketch.switchSession(self.classData[session])
                                    self.local_sketch.switchSession(self.classData[session])

                                    temp = str(session.text()).split(HYPHEN_SPLIT)
                                    helpMessage[temp[0]] = temp[1]
                                session.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                    else:
                        if section.checkState() == QtCore.Qt.Checked:
                            section.setCheckState(QtCore.Qt.Unchecked)
                            # Disable sessions
                            for session_forms in self.section_items[section].values():
                                for session in session_forms:
                                    session.setFlags(QtCore.Qt.ItemIsUserCheckable)
                self.help.updateInfo(helpMessage)
            else:
                if item == self.selected_section:
                    self.sketch.removeSection(self.classData[item])
                    self.local_sketch.removeSection(self.classData[item])

                    self.help.updateInfo({})
                for session_forms in self.section_items[item].values():
                    for session in session_forms:
                        session.setFlags(QtCore.Qt.ItemIsUserCheckable)
        # Session(Tutorial, Lab, etc.) checked/unchecked
        else:
            temp = str(item.text()).split(HYPHEN_SPLIT)
            if item.checkState() == QtCore.Qt.Checked:
                self.sketch.switchSession(self.classData[item])
                self.local_sketch.switchSession(self.classData[item])

                self.selected_session[temp[0]] = temp[1]
                self.help.addInfo({temp[0]:temp[1]})
                for session in self.session_items[item]:
                    if not session == item:
                        session.setCheckState(QtCore.Qt.Unchecked)
            else:
                if temp[0] in self.selected_session and self.selected_session[temp[0]] == temp[1]:
                    self.sketch.removeSession(self.classData[item])
                    self.local_sketch.removeSession(self.classData[item])

                    self.help.removeInfo({temp[0]:temp[1]})
                    del self.selected_session[temp[0]]

        self.planner.updateTable()
        #print self.sketch.getSchedule()

if __name__ == '__main__':
    data = {'code': u'CSCI2100', 'name': u'Data Structures \u6578\u64da\u7d50\u69cb', 'credit': u'3.00', 'overall_status': 'Open', 'sections': {u'A': {'instructor': [u'Professor KING Kuo Chin Irwin'], 'classes': {'Lecture': {'01': {'status': u'Open', 'nbr': u'4021', 'venue': [u'Lee Shau Kee Building LT3', u'Lee Shau Kee Building LT3'], 'day': [u'Mo', u'Tu'], 'time': [u'12:30PM - 01:15PM', u'12:30PM - 02:15PM']}}, 'Tutorial': {u'02': {'status': u'Open', 'nbr': u'4798', 'venue': [u'William M.W. Mong Engineering Building 407'], 'day': [u'We'], 'time': [u'05:30PM - 06:15PM']}, u'01': {'status': 'Waiting', 'nbr': u'4024', 'venue': [u'William M.W. Mong Engineering Building 803'], 'day': [u'Mo'], 'time': [u'05:30PM - 06:15PM']}}}, 'language': [' ', 'English']}, u'C': {'instructor': [u'Professor YU Jeffrey Xu'], 'classes': {'Lecture': {'01': {'status': u'Open', 'nbr': u'4023', 'venue': [u'Mong Man Wai Building LT1', u'Lady Shaw Building LT6'], 'day': [u'Mo', u'Th'], 'time': [u'10:30AM - 12:15PM', u'04:30PM - 05:15PM']}}, 'Tutorial': {u'01': {'status': u'Open', 'nbr': u'4799', 'venue': [u'TBA'], 'day': ['-'], 'time': ['-']}}}, 'language': [' ', 'English']}, u'B': {'instructor': [u'Professor SUN Hanqiu'], 'classes': {'Lecture': {'01': {'status': u'Open', 'nbr': u'4022', 'venue': [u'Y.C. Liang Hall 103', u'William M.W. Mong Engineering Building 407'], 'day': [u'Mo', u'Tu'], 'time': [u'12:30PM - 01:15PM', u'12:30PM - 02:15PM']}}, 'Tutorial': {u'02': {'status': u'Open', 'nbr': u'5640', 'venue': [u'Lady Shaw Building C2'], 'day': [u'We'], 'time': [u'05:30PM - 06:15PM']}, u'01': {'status': u'Open', 'nbr': u'4025', 'venue': [u'Lady Shaw Building C1'], 'day': [u'Mo'], 'time': [u'05:30PM - 06:15PM']}}}, 'language': [' ', 'English']}, u'D': {'instructor': [u'Professor SUN Hanqiu'], 'classes': {'Lecture': {'01': {'status': u'Open', 'nbr': u'5628', 'venue': [u'Lee Shau Kee Building LT3', u'T.Y. Wong Hall LT'], 'day': [u'We', u'Fr'], 'time': [u'11:30AM - 12:15PM', u'09:30AM - 11:15AM']}}, 'Tutorial': {u'02': {'status': u'Open', 'nbr': u'6084', 'venue': [u'Lee Shau Kee Building LT3'], 'day': [u'Tu'], 'time': [u'09:30AM - 10:15AM']}, u'01': {'status': u'Open', 'nbr': u'4800', 'venue': [u'Lee Shau Kee Building LT3'], 'day': [u'We'], 'time': [u'12:30PM - 01:15PM']}}}, 'language': [' ', 'English']}}, 'baseform': 'Lecture'}

    app = QtGui.QApplication(sys.argv)
    widget = SectionWidget('CSCI2100', Sketch())
    widget.setData(data)
    widget.show()
    sys.exit(app.exec_())
