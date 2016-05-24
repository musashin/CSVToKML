__author__ = 'nulysse'
import csv
import simplekml
import os
import ConfigParser
import collections
import sys
from geopy.distance import great_circle

line = collections.namedtuple('line', 'name lat_col_index lon_col_index color mark_time timestep')


_CSV_Path = r'C:\Ascent\Development\A350-FFS\DEVELOPMENT\Tools\CSVToKML\Dumps\TestStation2\A350-FFS_Tue_May_24_07-09-52_2016.bus.csv'


_color_map = {'red': simplekml.Color.red,
              'blue': simplekml.Color.blue,
              'green': simplekml.Color.green,
              'yellow': simplekml.Color.yellow}

time_index = 0
start_time = 5
end_time = 15
ref_speed_in_kts = 250
linelist = list()

def loadConfig(configFilePath, CSVfirstRow):
    """
    Load the INI Configuration file data

    From the config file, load:
        - Start and End time
        - name of the time column
        - for each trajectory, the name of the column, the sampling time and color

    :param configFilePath:  path to the INI configuration file
    :param CSVfirstRow: first row in the CSV file

    """

    global start_time,end_time,time_index,ref_speed_in_kts
    config = ConfigParser.RawConfigParser()
    config.read(configFilePath)

    start_time = config.getfloat('GENERAL', 'STARTTIME')
    end_time = config.getfloat('GENERAL', 'ENDTIME')
    timeColumnName = config.get('GENERAL', 'TIMECOLNAME')

    time_index = CSVfirstRow.index(timeColumnName)

    for section in config.sections():
        if 'traj' in section:

            latcolname = config.get(section, 'LATCOLNAME')
            loncolname = config.get(section, 'LONCOLNAME')

            try:
                latcolindex = CSVfirstRow.index(latcolname)
            except ValueError:
                sys.stderr.write('could not find {!s} in the CSV file'.format(latcolname))
                sys.exit(-1)

            try:
                loncolindex = CSVfirstRow.index(loncolname)
            except ValueError:
                sys.stderr.write('could not find {!s} in the CSV file'.format(loncolname))
                sys.exit(-1)
            try:
                ref_speed_in_kts=config.getfloat(section, "REFSPEEDKTS")
            except:
                ref_speed_in_kts = 250

            try:
                marktime=config.getboolean(section, "MARKTIME")
            except:
                marktime = False

            try:
                timestep=config.getfloat(section, "TIMESTEP")
            except:
                timestep = 0.01

            try:
                color= _color_map[config.get(section, "COLOR")]
            except:
                color = simplekml.Color.red

            linelist.append(line(name=section,
                                 lat_col_index=latcolindex,
                                 lon_col_index=loncolindex,
                                 color=color,
                                 mark_time=marktime,
                                 timestep=timestep))

def isValidLine(row, traj_data):
    """

    :param row:
    :return:
    """
    return row[traj_data.lat_col_index]!=' ' and row[traj_data.lon_col_index]!=' '


def isInTimeWindow(row):

    return float(row[time_index])>=start_time and float(row[time_index])<=end_time

def get_last_speed(current_time, id):
    return great_circle(line_coord[id][-1], line_coord[id][-2]).nm / (current_time - line_times[id]) * 3600


if __name__ == '__main__':

    KMLDoc = simplekml.Kml()

    timepnt = KMLDoc.newmultigeometry(name="Times")

    with open(_CSV_Path, 'rb') as csvfile:
        positionreader = csv.reader(csvfile)
        firstline = True
        linecount = 0
        last_time = -10.0

        for row in positionreader:
            if firstline:
                loadConfig(os.path.join(os.path.dirname(_CSV_Path), "config.ini"), row)
                line_coord = list()
                line_times = list()
                for id in  range(len(linelist)):
                    line_coord.append(list())
                    line_times.append(-10.0)

            else:
                for id in range(len(linelist)):
                    if isValidLine(row, linelist[id]) and isInTimeWindow(row) and (float(row[time_index]) - line_times[id])>= linelist[id].timestep:

                        line_coord[id].append((row[linelist[id].lon_col_index], row[linelist[id].lat_col_index]))

                        if linelist[id].mark_time:
                            timepnt = KMLDoc.newpoint(name="Time is {!s}".format(row[time_index]),
                                                      description="Time is {!s}".format(row[time_index]),
                                                      coords=[(row[linelist[id].lon_col_index], row[linelist[id].lat_col_index])])

                        if len(line_coord[id])>2:
                            if get_last_speed(float(row[time_index]), id) > (ref_speed_in_kts + (ref_speed_in_kts*5.0)):
                                print 'potential jump for trajectory {!s} at time {!s}'.format(linelist[id].name, row[time_index])

                        line_times[id] = float(row[time_index])


            firstline = False

            linecount+=1

    trajectory = list()

    for id in range(len(linelist)):
        trajectory.append(KMLDoc.newmultigeometry(name=linelist[id].name))
        trajectory[id]. newlinestring(name='test',description=row[time_index],coords=line_coord[id])
        trajectory[id].style.linestyle.color = linelist[id].color # Red
        trajectory[id].style.linestyle.width = 10  # 10 pixels
        trajectory[id].style.iconstyle.scale = 3  # Icon thrice as big
        trajectory[id].style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/info-i.png'

    KMLDoc.save(os.path.join(os.path.dirname(_CSV_Path), "lines"+".kml"))
