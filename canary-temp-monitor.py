#!/usr/bin/env python3
#Canary environmental monitoring v2
#Chuck Henry 2021

import time
import board
import adafruit_sht31d
from datetime import datetime
import onering
import configparser

def datestamp():
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    return dt_string

def sensorpoll():
    tempc = sensor.temperature
    temp = round((tempc * 1.8) + 32,1)
    humid = round(sensor.relative_humidity,1)
    dt_string = datestamp()
    sensor.heater = True
    time.sleep(1)
    sensor.heater = False
    #print(f"{dt_string} {temp}F {humid}%")
    return [dt_string, temp, humid]

def prepdata(data,interval):
    totaltemp = 0
    totalhumid = 0
    polls = 0
    for t in reversed(data):
        totaltemp = totaltemp + t[1]
        totalhumid = totalhumid + t[2]
        polls = polls + 1
        if polls == interval:
            break
    avgtemp = round(totaltemp / polls,1)
    avghumid = round(totalhumid / polls,1)
    dt_string = datestamp()
    return [dt_string, avgtemp, avghumid]

def alarmcheck(data):
    statusmess = "ok"
    statuscode = 0
    if data[1] > bounds[0]:
        statusmess = "Max temp exceeded"
        statuscode = 1
    if data[1] < bounds[1]:
        statusmess = "Min temp exceeded"
        statuscode = 1
    if data[2] > bounds[2]:
        statusmess = "Max humid exceeded"
        statuscode = 1
    if data[2] < bounds[3]:
        statusmess = "Min humid exceeded"
        statuscode = 1
    return [statuscode, statusmess]

def notify(data,mode,status):
    if sms == '1' and (mode == 'sms' or mode == 'all'):
        for number in phones:
            onering.textbelt(number,key,data)
    if slack == '1' and (mode == 'slack' or mode == 'all'):
        if status == 'alarm':
            for channel in hooks:
                username = "Canary2"
                emoji = ":imp:"
                onering.slackpost(username,emoji,data,channel)
        else:
            username = "Canary2"
            emoji = ":imp:"
            print(hooks[1])
            onering.slackpost(username,emoji,data,hooks[1])

def logrotate(logfile):
    logcurrent = onering.readfile(logfile)
    while len(logcurrent) > loglength:
        logcurrent.pop(0)
        onering.writefile(logcurrent,logfile)

def loadsettings():
    config = configparser.ConfigParser()
    config.read('/var/www/dokuwiki/data/pages/settings.txt')
    global poll, logfile, loglength, bounds, sms, key, slack, hooks, logfreq
    poll = int(config.get('basics','poll'))
    logfile = config.get('basics','logfile')
    loglength = int(config.get('basics','loglength'))
    tempmax = config.get('boundaries','tempmax')
    tempmin = config.get('boundaries','tempmin')
    humidmax = config.get('boundaries','humidmax')
    humidmin = config.get('boundaries','humidmin')
    bounds = [int(tempmax),int(tempmin),int(humidmax),int(humidmin)]
    sms = config.get('notification','sms')
    key = config.get('notification','key')
    phone1 = config.get('notification','phone1')
    phone2 = config.get('notification','phone2')
    phone3 = config.get('notification','phone3')
    if phone1 == '':
        phones = ['123-123-1234']
    else:
        phones = [phone1]
    if phone2 != '':
        phones.append(phone2)
    if phone3 != '':
        phones.append(phone3)
    slack = config.get('notification','slack')
    alarmchannel = config.get('notification','alarmchannel')
    logchannel = config.get('notification','logchannel')
    hooks = [alarmchannel,logchannel]
    logfreq =config.get('notification','logfreq')

if __name__ == "__main__":
    #Config settings
    loadsettings()
    hour = round(3600 / poll,0)
    quarter = round(hour / 4,0)
    sixhour = hour * 6
    twelvehour = hour * 12
    day = hour * 24

    #Init varibles
    i2c = board.I2C()
    sensor = adafruit_sht31d.SHT31D(i2c)
    timer = 0
    sensordata = []

    #Startup work
    quotarem = onering.textbelt_quota(key)
    myip = onering.whatsmyip()
    data = "  * " + datestamp() + " :: Canary monitoring begins, " + str(quotarem) + " sms in quota remaining, logs: http://" + myip + "/start\n"
    notify(data,'slack','log')
    onering.addline(data,logfile)
    while True:
        loadsettings()
        time.sleep((poll - 1)) #Sleeping
        results=sensorpoll() #Get data from sensor
        sensordata.append(results) #Add result to array
        timer = timer + 1
        logrotate(logfile)
        if timer%quarter == 0:
            quarterdata = prepdata(sensordata,quarter)
            alarmstatus = alarmcheck(quarterdata)
            data = "  * " + quarterdata[0] + " :: " + str(quarterdata[1]) + "F " + str(quarterdata[2]) + "% " + alarmstatus[1] + "\n"
            onering.addline(data,logfile)
            if alarmstatus[0] == 1:
                notify(data,'all','alarm')
        if timer%hour == 0:
            if logfreq == "1hour":
                hourdata = prepdata(sensordata,hour)
                notify(data,'slack','log')
        if timer%sixhour == 0:
            if logfreq == "6hour":
                hourdata = prepdata(sensordata,sixhour)
                notify(data,'slack','log')
        if timer%twelvehour == 0:
            if twelvehour == "12hour":
                hourdata = prepdata(sensordata,twelvehour)
                notify(data,'slack','log')
        if timer%day == 0:
            timer = 0
            sensordata = []
