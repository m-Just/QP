# -*- coding: utf-8 -*-
import sys, os

import data_manager


# Data structure maintaining timetable schedules
# Only essential reference id information stored
'''
Sketch.schedule = {
    code: {
        'section',
        'classes': {
            form: nbr
        },
    },
}
'''

class Sketch(object):
    def __init__(self, table, draft, name='draft', copy=None):
        self.schedule = dict()
        self.table = table
        self.draft = draft
        self.name = name
        if not copy == None:
            if isinstance(copy, Sketch):
                self.mergeWith(copy)
            else:
                print 'Error: ' + '"' + copy + '"' + ' is not an instance of class Sketch'

    def getName(self):
        return self.name

    def getSchedule(self):
        return self.schedule

    def setSchedule(self, schedule):
        self.schedule = schedule

    def diff(self, other):
        s0 = other.getSchedule()
        s1 = self.getSchedule()
        c0 = set(s0.keys())
        c1 = set(s1.keys())
        toDel = dict()
        toAdd = dict()
        for c in c0 - c1:
            toDel[c] = s0[c]
        for c in c1 - c0:
            toAdd[c] = s1[c]
        return toDel, toAdd

    # Submit changes to timetable
    def submitChangeToTable(self, shopping=False):
        temp = self.schedule.copy()
        draft = self.draft.getSchedule()
        temp.update(draft)
        entries = data_manager.loadTableSlotEntries(temp)
        self.table.loadTimetable(entries)

    # This method will replace the current schedule with the newly merged one
    def mergeWith(self, other):
        if isinstance(other, Sketch):
            for code in other.getSchedule().keys():
                if code in self.schedule:
                    print 'Error: Merge conflict'
                    break
                else:
                    self.schedule[code] = other.getSchedule()[code]
        else:
            'Error: Sketches cannot merge with other type of objects'
        return self.schedule

    # Argument data = { code, section, form, nbr }
    def switchSection(self, data):
        print data['code'] + ': Switch section to ' + data['section'] + ' in ' + self.name
        if data['code'] in self.schedule:
            course = self.schedule[data['code']]
        else:
            course = self.schedule[data['code']] = dict()
        course['section'] = data['section']
        course['classes'] = { data['form']: data['nbr'] }

    def switchSession(self, data):
        print data['code'] + ': Switch session to ' + data['form'] + '-' + data['nbr'] + ' in ' + self.name
        if data['code'] in self.schedule and self.schedule[data['code']]['section'] == data['section']:
            self.schedule[data['code']]['classes'][data['form']] = data['nbr']
        else:
            print 'Error: Invalid session switch: corresponding course section dismatched'

    def removeSection(self, data):
        print data['code'] + ': Remove section ' + data['section'] + ' from ' + self.name
        if data['code'] in self.schedule:
            del self.schedule[data['code']]
        else:
            print 'Error: Removing non-exsiting course from ' + self.name + ': ' +\
            data['code'] + ' ' + data['section']

    def removeSession(self, data):
        print data['code'] + ': Remove session ' + data['form'] + '-' + data['nbr'] + ' from ' + self.name
        if data['form'] in self.schedule[data['code']]['classes']:
            del self.schedule[data['code']]['classes'][data['form']]
        else:
            print 'Error: Removing non-exsiting session from ' + self.name + ': ' +\
            data['code'] + ' ' + data['section'] + ' ' + data['form']

    def clear(self):
        print 'Remove courses from ' + self.name
        self.schedule = dict()
