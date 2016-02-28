__author__ = 'drobisch'

import datetime
import config
import helpers
from models import User, Action, Door, RfidTagInfo, Statistic, StatisticEntry
from server import db
import random

class StatisticsManager(object):

    # Monthly stats.
    STATISTICS_STATID_USERCOUNT             =   1
    STATISTICS_STATID_ACCESSES              =   2
    STATISTICS_STATID_AUTH_CARDS            =   3
    STATISTICS_STATID_WEB_CLIENT            =   4
    STATISTICS_STATID_NODE_ACCESSES         =   5
    STATISTICS_STATID_WEEKDAYS              =   6
    STATISTICS_STATID_LOGINS                =   7
    STATISTICS_STATID_SECURITY              =   8
    STATISTICS_STATID_ACTIVITY_USER_GROUPS  =   9
    STATISTICS_STATID_USER_GROUPS_ACCESSES  =   10
    STATISTICS_STATID_USER_GROUPS_AVERAGE   =   11

    BINNING_NONE = 0

    SERIES_NONE = 0

    SERIES_GENERALUSER = 0
    SERIES_SUPERUSER = 1
    SERIES_ADMINUSER = 2

    SERIES_GROUPS_NO_ACTIVITY = 0
    SERIES_GROUPS_LOW_ACTIVITY = 1
    SERIES_GROUPS_MEDIUM_ACTIVITY = 2
    SERIES_GROUPS_HIGH_ACTIVITY = 3

    SERIES_GROUP_BY_LOW_ACTIVITY = 0
    SERIES_GROUP_BY_MEDIUM_ACTIVITY = 1
    SERIES_GROUP_BY_HIGH_ACTIVITY = 2

    SERIES_CARD_ACCESSES = 0
    SERIES_WEB_ACCESSES = 1

    SERIES_SUCCESFULL_LOGINS = 0
    SERIES_FAILED_LOGINS = 1

    SERIES_SECURITY_FAILED_LOGINS = 0
    SERIES_SECURITY_FAILED_API_AUTH = 1
    SERIES_SECURITY_WORKER_ERRORS = 2

    @staticmethod
    def staticEntryAddOrUpdate(statTye, statId, label, value, month, year, binningId, series):
        statEntry = StatisticEntry.query.filter_by(statId = statId, label = label,series = series, month = month, year = year).first()
        if statEntry is None:
            newEntry = StatisticEntry(statId, label, value, series, month, year, binningId)
            db.session.add(newEntry)
            db.session.commit()
        else:
            if statEntry.value != value:
                statEntry.value = float(value)
                db.session.commit()

    @staticmethod
    def incrementalEntryAddOrUpdate(statTye, statId, label, value, month, year, binningId, series):
        statEntry = StatisticEntry.query.filter_by(statId = statId, label = label,series = series, month = month, year = year).first()
        if statEntry is None:
            newEntry = StatisticEntry(statId, label, value, series, month, year, binningId)
            db.session.add(newEntry)
        else:
            statEntry.value = str(float(statEntry.value) + float(value))
        db.session.commit()


    @staticmethod
    def evaluateUserGroups(userData):
        userDataLowAction = []
        userDataMediumAction = []
        userDataHighAction = []
        userData.sort()

        noActionUsers = 0
        actionUsers = 0

        lowThreshold = 0
        highThreshold = 0

        for i in range(0, len(userData)):
            if userData[i] == 0:
                noActionUsers += 1
            else:
                actionUsers = len(userData)
                mediumThresholdIndex = noActionUsers + int(round((actionUsers - noActionUsers) * 0.5, 0))
                if i > mediumThresholdIndex:
                    highThreshold += userData[i]
                else:
                    lowThreshold += userData[i]

        highThreshold = highThreshold / ((actionUsers - noActionUsers) * 0.5)
        lowThreshold  = lowThreshold / ((actionUsers - noActionUsers) * 0.5)

        lowActionUserAccesses = 0
        mediumActionUserAccesses = 0
        highActionUserAccesses = 0

        for i in range(noActionUsers, len(userData)):
            if userData[i] < lowThreshold:
                userDataLowAction.append(userData[i])
                lowActionUserAccesses += userData[i]
            else:
                if userData[i] < highThreshold:
                    userDataMediumAction.append(userData[i])
                    mediumActionUserAccesses += userData[i]
                else:
                    userDataHighAction.append(userData[i])
                    highActionUserAccesses += userData[i]

        result = []
        result.append(noActionUsers)
        result.append(len(userDataLowAction))
        result.append(len(userDataMediumAction))
        result.append(len(userDataHighAction))
        result.append(lowActionUserAccesses)
        result.append(mediumActionUserAccesses)
        result.append(highActionUserAccesses)

        if len(userDataLowAction) != 0:
            result.append(float(lowActionUserAccesses) / float(len(userDataLowAction)))
        else:
            result.append(0)

        if len(userDataMediumAction) != 0:
            result.append(float(mediumActionUserAccesses) / float(len(userDataMediumAction)))
        else:
            result.append(0)

        if len(userDataHighAction) != 0:
            result.append(float(highActionUserAccesses) / float(len(userDataHighAction)))
        else:
            result.append(0)

        return result

    @staticmethod
    def updateUserCountStat(updateData):
        print "Update UserCount stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_USERCOUNT).first()
        if stat == None:
            newStat = Statistic("User total", StatisticsManager.STATISTICS_STATID_USERCOUNT, Statistic.STATTYPE_LINE_SERIES, 0, 3, "", 0, "Users", "Supervisors", "Admins")
            db.session.add(newStat)
            db.session.commit()

        now = datetime.datetime.now() #- datetime.timedelta(days=30)
        month = now.month
        year = now.year
        for i in range(0, 3):
            StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USERCOUNT, str(month) + "/" + str(year % 1000), updateData[i], month, year, StatisticsManager.BINNING_NONE, i)

    @staticmethod
    def updateUserActivityGroups(userData):
        print "Update User Groups stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_ACTIVITY_USER_GROUPS).first()
        if stat == None:
            newStat = Statistic("User activity groups", StatisticsManager.STATISTICS_STATID_ACTIVITY_USER_GROUPS, Statistic.STATTYPE_YEARLY_BAR_SERIES, 0, 4, "", Statistic.STATDISPLAY_CONFIG_NO_TOTAL, "Zero activity users", "Low activity users", "Medium activity users", "High activity users")
            db.session.add(newStat)
            db.session.commit()

        result = StatisticsManager.evaluateUserGroups(userData)

        now = datetime.datetime.now()
        month = now.month
        year = now.year

        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_YEARLY_BAR_SERIES, StatisticsManager.STATISTICS_STATID_ACTIVITY_USER_GROUPS, str(month) + "/" + str(year % 1000), result[0], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUPS_NO_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_YEARLY_BAR_SERIES, StatisticsManager.STATISTICS_STATID_ACTIVITY_USER_GROUPS, str(month) + "/" + str(year % 1000), result[1], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUPS_LOW_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_YEARLY_BAR_SERIES, StatisticsManager.STATISTICS_STATID_ACTIVITY_USER_GROUPS, str(month) + "/" + str(year % 1000), result[2], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUPS_MEDIUM_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_YEARLY_BAR_SERIES, StatisticsManager.STATISTICS_STATID_ACTIVITY_USER_GROUPS, str(month) + "/" + str(year % 1000), result[3], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUPS_HIGH_ACTIVITY)

    @staticmethod
    def updateUserActivityGroupAccesses(userData):
        print "Update User Group Accesses stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_USER_GROUPS_ACCESSES).first()
        if stat == None:
            newStat = Statistic("Average accesses of user groups", StatisticsManager.STATISTICS_STATID_USER_GROUPS_ACCESSES, Statistic.STATTYPE_LINE_SERIES, 0, 3, "",  Statistic.STATDISPLAY_CONFIG_NO_TOTAL, "Low activity users", "Medium activity users", "High activity users")
            db.session.add(newStat)
            db.session.commit()

        result = StatisticsManager.evaluateUserGroups(userData)

        now = datetime.datetime.now()
        month = now.month
        year = now.year

        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USER_GROUPS_ACCESSES, str(month) + "/" + str(year % 1000), result[4], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUP_BY_LOW_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USER_GROUPS_ACCESSES, str(month) + "/" + str(year % 1000), result[5], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUP_BY_MEDIUM_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USER_GROUPS_ACCESSES, str(month) + "/" + str(year % 1000), result[6], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUP_BY_HIGH_ACTIVITY)


    @staticmethod
    def updateUserActivityGroupAverages(userData):
        print "Update User Group Accesses stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_USER_GROUPS_AVERAGE).first()
        if stat == None:
            newStat = Statistic("Total accesses of user groups", StatisticsManager.STATISTICS_STATID_USER_GROUPS_AVERAGE, Statistic.STATTYPE_YEARLY_BAR_SERIES, 0, 3, "", Statistic.STATDISPLAY_CONFIG_NO_TOTAL, "Low activity users", "Medium activity users", "High activity users")
            db.session.add(newStat)
            db.session.commit()

        result = StatisticsManager.evaluateUserGroups(userData)

        now = datetime.datetime.now()
        month = now.month
        year = now.year

        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USER_GROUPS_AVERAGE, str(month) + "/" + str(year % 1000), result[7], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUP_BY_LOW_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USER_GROUPS_AVERAGE, str(month) + "/" + str(year % 1000), result[8], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUP_BY_MEDIUM_ACTIVITY)
        StatisticsManager.staticEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_USER_GROUPS_AVERAGE, str(month) + "/" + str(year % 1000), result[9], month, year, StatisticsManager.BINNING_NONE, StatisticsManager.SERIES_GROUP_BY_HIGH_ACTIVITY)


    @staticmethod
    def updateAccessesStat(updateData):
        print "Update Accesses stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_ACCESSES).first()
        if stat == None:
            newStat = Statistic("Accesses total", StatisticsManager.STATISTICS_STATID_ACCESSES, Statistic.STATTYPE_LINE_SERIES, 0, 2, "", 0, "Card auth.", "Web auth.")
            db.session.add(newStat)
            db.session.commit()

        for year in updateData:
            for month in updateData[year]:
                for seriesIndex in range(len(updateData[year][month])):
                    StatisticsManager.incrementalEntryAddOrUpdate(Statistic.STATTYPE_LINE_SERIES, StatisticsManager.STATISTICS_STATID_ACCESSES, str(month) + "/" + str(year % 1000), updateData[year][month][seriesIndex], month, year, StatisticsManager.BINNING_NONE, seriesIndex)

    @staticmethod
    def updateWeekdaysStat(updateData):
        print "Update Weekdate stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_WEEKDAYS).first()
        if stat == None:
            newStat = Statistic("Accesses per weekday", StatisticsManager.STATISTICS_STATID_WEEKDAYS, Statistic.STATTYPE_RADAR_SERIES, 7, 1, "", 0, "Weekdays")
            db.session.add(newStat)
            db.session.commit()

        for day in range(0,7):
            daynamesList = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dayname = daynamesList[day]
            #dayEntry = StatisticEntry(StatisticsManager.STATISTICS_STATID_WEEKDAYS,dayname,random.randrange(10,100), 0, 0, 0, day)
            StatisticsManager.incrementalEntryAddOrUpdate(Statistic.STATTYPE_RADAR_SERIES,StatisticsManager.STATISTICS_STATID_WEEKDAYS,dayname,updateData[day], 0, 0, day, 0)

    @staticmethod
    def updateNodeAccessStat(updateData):
        print "Update node accesses stat"
        stat = Statistic.query.filter(Statistic.statId == StatisticsManager.STATISTICS_STATID_NODE_ACCESSES).first()
        if stat == None:
            newStat = Statistic("Accesses per node", StatisticsManager.STATISTICS_STATID_NODE_ACCESSES, Statistic.STATTYPE_DOUGHNUT_CLASSES, 0, 0)
            db.session.add(newStat)
            db.session.commit()

        for nodeName in updateData:
            StatisticsManager.incrementalEntryAddOrUpdate(Statistic.STATTYPE_DOUGHNUT_CLASSES, StatisticsManager.STATISTICS_STATID_NODE_ACCESSES,nodeName,updateData[nodeName],0,0,0,0)

    @staticmethod
    def updateLoginStat():
        print "Update Login stat"

    @staticmethod
    def updateSecurityStat():
        print "Update Security stat"

