#========================================================================
# ChronosSync
# Synchronization application from Chronos timetables to Google Calendar
# By Anthony SEURE
# 2013
#========================================================================
import sys
import json
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET

import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow as run

#==============================================
# Get the starting time (Google Calendar form)
#==============================================
def startTime(rawHour):
  hours = int(rawHour) / 4
  minutes = (int(rawHour) % 4) * 15
  if (hours < 10):
    final = "0" + str(hours) + ":"
  else:
    final = str(hours) + ":"
  if (minutes < 10):
    final += "0"
  final += str(minutes) + ":00.000"
  return final

#============================================
# Get the ending time (Google Calendar form)
#============================================
def endTime(rawHour, rawDuration):
  return startTime(str(int(rawHour) + int(rawDuration)))

# Get the starting datetime (Google Calendar form)
def getStart(rawDate, rawHour):
  day = rawDate[:2]
  month = rawDate[3:5]
  year = rawDate[6:10]
  final = year + "-" + month + "-" + day + "T"
  final += startTime(rawHour)
  final += "+01:00"
  return final

#================================================
# Get the ending datetime (Google Calendar form)
#================================================
def getEnd(rawDate, rawHour, rawDuration):
  day = rawDate[:2]
  month = rawDate[3:5]
  year = rawDate[6:10]
  final = year + "-" + month + "-" + day + "T"
  final += endTime(rawHour, rawDuration)
  final += "+01:00"
  return final


#===============================================================================
# MAIN
#===============================================================================
def main():
  print('-- ChronosSync starting')
  #==============================
  # Read JSON configuration file
  #==============================
  print('Reading configuration file...')
  with open('csi.json') as f:
    conf = json.load(f)

    auth = conf['chronos']['auth']
    num = conf['chronos']['num']
    week = conf['chronos']['week']
    group = conf['chronos']['group']

    cid = conf['google-calendar']['cid']
    cs = conf['google-calendar']['cs']
    scope = conf['google-calendar']['scope']
    calid = conf['google-calendar']['calid']

  #=========================
  # Getting the Chronos XML
  #=========================
  print('Recovering Chronos timetables...')
  chronosXML = urllib.request.urlopen('http://webservices.chronos.epita.net/GetWeeks.aspx?'
                              + 'auth=' + auth + '&num=' + num
                              + '&week=' + week + '&group=' + group)
  tree = ET.parse(chronosXML)
  root = tree.getroot()

  #=======================================
  # Getting and formating all the courses
  #=======================================
  print('Formating courses...')
  courses = []
  for day in root.iter('day'):
    rawDate = day.find('date').text
    for course in day.iter('course'):
      if course.find('title') != None:
        rawTitle = course.find('title').text
      if course.find('hour') != None:
        rawHour = course.find('hour').text
      if course.find('duration') != None:
        rawDuration = course.find('duration').text
      if course.find('instructor') != None:
        rawTeacher = course.find('instructor').text
      if course.find('room') != None:
        rawRoom = course.find('room').text
      courses.append([
        getStart(rawDate, rawHour),
        getEnd(rawDate, rawHour, rawDuration),
        rawTitle,
        rawRoom,
        rawTeacher
        ])

  #===================================
  # Connecting to Google Calendar API
  #===================================
  print('Connection to Google Calendar...')
  flow = OAuth2WebServerFlow(cid, cs, scope)
  storage = Storage('credentials.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = run(flow, storage)
  http = httplib2.Http()
  http = credentials.authorize(http)
  service = build('calendar', 'v3', http=http)

  try:
    #============================================
    # Cleaning old events from the Google Agenda
    #============================================
    print('Cleaning Google Agenda...')
    page_token = None
    while True:
      events = service.events().list(calendarId=calid, pageToken=page_token).execute()
      if events['items']:
        for event in events['items']:
          service.events().delete(calendarId=calid, eventId=event['id']).execute()
      page_token = events.get('nextPageToken')
      if not page_token:
        break

    #===========================
    # Uploding on Google Agenda
    #===========================
    print('Uploading courses on Google Calendar...')
    for c in courses:
      event = {
        'start': {
          'dateTime': c[0]
        },
        'end': {
          'dateTime': c[1]
        },
        'summary': c[2], # title
        'location': c[3], # room
        'description': c[4] # teacher
      }
      created_event = service.events().insert(calendarId=calid, body=event).execute()

    print('-- Goodbye')
  except AccessTokenRefreshError:
    print('Credentials have been revoked')

if __name__ == '__main__':
  main()
