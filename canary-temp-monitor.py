#!/usr/bin/env python3
#Canary environmental monitoring v2
#Chuck Henry 2021

import time
import board
import adafruit_sht31d
import onering
import configparser
import RPi.GPIO as GPIO

def sensor_reading(sensor, use_water_sensor):
    tempc = sensor.temperature
    temp = round((tempc * 1.8) + 32,1)
    humid = round(sensor.relative_humidity,1)
    datetime_string = onering.get_current_datetime()
    wet = 0
    if use_water_sensor == "1":
        if GPIO.input(22) > 0:
            wet = 1
    sensor.heater = True
    time.sleep(1)
    sensor.heater = False
    return [datetime_string, temp, humid, wet]

def prepare_data(data,interval):
    total_temp = 0
    total_humid = 0
    total_wet_readings = 0
    polls = 0
    wet = 0
    for reading in reversed(data):
        total_temp = total_temp + reading[1]
        total_humid = total_humid + reading[2]
        total_wet_readings = total_wet_readings + reading[3]
        polls = polls + 1
        if polls == interval:
            break
    avg_temp = round(total_temp / polls, 1)
    avg_humid = round(total_humid / polls, 1)
    datetime_string = onering.get_current_datetime()
    if total_wet_readings > 0:
        wet = total_wet_readings
    return datetime_string, avg_temp, avg_humid, wet

def alarm_check(data, temp_max, temp_min, humid_max, humid_min):
    status_message = "ok"
    status_code = 0
    if data[1] > float(temp_max):
        status_message = "Max temp exceeded"
        status_code = 1
    if data[1] < float(temp_min):
        status_message = "Min temp exceeded"
        status_code = 1
    if data[2] > float(humid_max):
        status_message = "Max humid exceeded"
        status_code = 1
    if data[2] < float(humid_min):
        status_message = "Min humid exceeded"
        status_code = 1
    if data[3] > 0:
        status_message = f"Wet! (data[3])"
        status_code = 1
    return [status_code, status_message]

def notify(display, sms_contacts, slack_contacts, mode):
    if mode == 'alarm':
        if len(sms_contacts) > 1:
            for number in sms_contacts[1]:
                onering.post_to_sms(number, sms_contacts[0], display)
        if len(slack_contacts) > 0:
            for channel in slack_contacts:
                username = "Canary2"
                emoji = ":imp:"
                onering.post_to_slack(username,emoji,display,channel)
    else:
        if len(slack_contacts) > 0:
            username = "Canary2"
            emoji = ":imp:"
            onering.post_to_slack(username,emoji,display,slack_contacts[1])

def log_rotate(log_file, log_length):
    current_log = onering.read_file(log_file)
    while len(current_log) > log_length:
        current_log.pop(0)
        onering.write_file(current_log,log_file)

def load_settings(settings_path):
    config = configparser.ConfigParser()
    config.read(settings_path)
    log_file = config.get('basics', 'log_file')
    log_length = int(config.get('basics', 'log_length'))
    use_water_sensor = config.get('basics', 'use_water_sensor')
    temp_max = config.get('boundaries', 'temp_max')
    temp_min = config.get('boundaries', 'temp_min')
    humid_max = config.get('boundaries', 'humid_max')
    humid_min = config.get('boundaries', 'humid_min')
    use_sms = config.get('notification', 'use_sms')
    key = config.get('notification', 'key')
    phone1 = config.get('notification', 'phone1')
    phone2 = config.get('notification', 'phone2')
    phone3 = config.get('notification', 'phone3')
    use_slack = config.get('notification','use_slack')
    slack_alarm_channel = config.get('notification','slack_alarm_channel')
    slack_log_channel = config.get('notification','slack_log_channel')
    slack_log_freq = config.get('notification','slack_log_freq')
    slack_contacts = []
    sms_contacts = []
    if use_slack == "1":
        slack_contacts = slack_alarm_channel, slack_log_channel
    if use_sms == "1":
        sms_contacts = key, [phone1, phone2, phone3]
    return log_file, log_length, temp_max, temp_min, humid_max, humid_min, \
    slack_log_freq, slack_contacts, sms_contacts, key, use_water_sensor

if __name__ == "__main__":
    #Config settings
    SETTINGS_PATH = '/var/www/dokuwiki/data/pages/settings.txt'
    log_file, log_length, temp_max, temp_min, humid_max, humid_min, \
    slack_log_freq, slack_contacts, sms_contacts, key, \
    use_water_sensor = load_settings(SETTINGS_PATH)
    POLL = 59 #seconds
    QUARTERHOUR = 15 #minutes
    HOUR = 60 #minutes
    SIXHOUR = 360 #minutes
    TWELVEHOUR = 720 #minutes
    DAY = 1440 #minutes

    #Init varibles
    i2c = board.I2C()
    sensor = adafruit_sht31d.SHT31D(i2c)
    timer = 0
    sensor_data = []
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(22, GPIO.IN)

    #Startup work
    quota_remaining = onering.get_textbelt_quota(key)
    ip = onering.whatsmyip()
    display = (f"{onering.get_current_datetime()} :: "
                f"Canary monitoring begins, {quota_remaining}"
                f"sms in quota remaining, logs: http://{ip}/start"
    )
    wiki_display = "  * " + display + "\n"
    notify(display, sms_contacts, slack_contacts, "log")
    onering.add_line(wiki_display, log_file)
    while True:
        log_file, log_length, temp_max, temp_min, humid_max, humid_min, \
        slack_log_freq, slack_contacts, sms_contacts, key, \
        use_water_sensor = load_settings(SETTINGS_PATH)
        time.sleep(POLL) #Sleeping
        results=sensor_reading(sensor, use_water_sensor) #Get data from sensor
        sensor_data.append(results) #Add result to array
        timer = timer + 1
        log_rotate(log_file, log_length)
        if timer % QUARTERHOUR == 0:
            quarter_data = prepare_data(sensor_data, QUARTERHOUR)
            alarm_status = alarm_check(quarter_data, temp_max, temp_min, \
            humid_max, humid_min)
            display = (f"{quarter_data[0]} :: {quarter_data[1]}F "
                        f"{quarter_data[2]}% {alarm_status[1]}"
            )
            wiki_display = "  * " + display + "\n"
            onering.add_line(wiki_display, log_file)
            if alarm_status[0] == 1:
                notify(display, sms_contacts, slack_contacts, "alarm")
        if timer % HOUR == 0:
            if slack_log_freq == "1hour":
                hour_data = prepare_data(sensor_data, HOUR)
                display = (f"One Hour Report: {hour_data[0]} :: {hour_data[1]}F "
                            f" {hour_data[2]}% {alarm_status[1]}"
                )
                notify(display, sms_contacts, slack_contacts, "log")
        if timer % SIXHOUR == 0:
            if slack_log_freq == "6hour":
                six_hour_data = prepare_data(sensor_data, SIXHOUR)
                display = (f"Six Hour Report: {six_hour_data[0]} :: "
                            f"{six_hour_data[1]}F {six_hour_data[2]}% "
                            f"{alarm_status[1]}"
                )
                notify(display, sms_contacts, slack_contacts, "log")
        if timer % TWELVEHOUR == 0:
            if slack_log_freq == "12hour":
                twelve_hour_data = prepare_data(sensor_data, TWELVEHOUR)
                display = (f"Twelve Hour Report: {twelve_hour_data[0]} :: "
                            f"{twelve_hour_data[1]}F {twelve_hour_data[2]}% "
                            f"{alarm_status[1]}"
                )
                notify(display, sms_contacts, slack_contacts, "log")
        if timer % DAY == 0:
            timer = 0
            sensordata = []
