#This is a library of stuff I seem to reuse a lot.
#Written by Chuck Henry 2021 unless otherwise stated.
import requests
import json
import socket
import os
from datetime import datetime

def get_current_datetime():
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %I:%M:%S %p")
    return dt_string

def post_to_slack(username,emoji,message,url):
    slack_data = {'username': username,
        'icon_emoji': emoji,
        'text': message
    }
    response = requests.post(
        url,
        data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'}
    )
    return response

def post_to_sms(phone,key,message):
    textbelt_data = {
        "phone": phone,
        "message": message,
        "key": key
    }
    response = requests.post(
        "https://textbelt.com/text",
        textbelt_data)
    return response

def get_textbelt_quota(key):
    response = requests.get(
        "https://textbelt.com/quota/" + key
    )
    info = response.json()
    quota = info.get("quotaRemaining")
    return quota

def read_file(file):
    if os.path.exists(file):
        f = open(file, "r")
        lines = f.read().splitlines()
        f.close()
    else:
        lines=[]
    return lines

def write_file(data,file):
    f = open(file, "w")
    for l in data:
        f.write("{}\n".format(l))
    f.close()

def add_line(data,file):
    f = open(file, "a")
    f.write(data)
    f.close()

def whatsmyip():
    #from https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
