__author__ = 'nulysse'
import csv
import simplekml
import os

import collections
line = collections.namedtuple('line', 'name lat_col_index lon_col_index color mark_time')


_CSV_Path = r'C:\Temp\FMS_movement\1\A350-FFS_Tue_May_17_19-04-27_2016.bus.csv'


_time_index = 0
_start_time = 5
_end_time  = 15

linelist = [line(name='CDS_ND_PRP', lat_col_index=19, lon_col_index=5, color=simplekml.Color.red, mark_time=False),
            line(name='ADIR_POS1', lat_col_index=16, lon_col_index=29, color=simplekml.Color.blue, mark_time=False),
            #line(name='ADIR_POS2', lat_col_index=14, lon_col_index=26, color=simplekml.Color.green, mark_time=False),
            #line(name='ADIR_POS3', lat_col_index=15, lon_col_index=27, color=simplekml.Color.yellow, mark_time=False),
            line(name='ADIR_POS1_FINE', lat_col_index=25, lon_col_index=33, color=simplekml.Color.bisque, mark_time=False)
            ]


def isInTimeWindow(row):

    return float(row[_time_index])>=_start_time and float(row[_time_index])<=_end_time

if __name__ == '__main__':

    KMLDoc = simplekml.Kml()

    timepnt = KMLDoc.newmultigeometry(name="Times")

    with open(_CSV_Path, 'rb') as csvfile:
        positionreader = csv.reader(csvfile)
        firstline = True
        linecount = 0

        line_coord = list()
        for id in  range(len(linelist)):
            line_coord.append(list())

        last_time = -10.0
        for row in positionreader:
                #print 'lat {!s}, lon {!s}\n'.format(row[_lat_col_index], row[_lon_col_index])

            for id in range(len(linelist)):
                if not firstline and row[linelist[id].lat_col_index]!=' ' and row[linelist[id].lon_col_index]!=' ' and isInTimeWindow(row):
                    #trajectory.newpoint(name='test',description=row[_time_index], coords=[(row[_lon_col_index], row[_lat_col_index])])
                    line_coord[id].append((row[linelist[id].lon_col_index], row[linelist[id].lat_col_index]))

                    if linelist[id].mark_time and (float(row[_time_index])- last_time)>= 0.1:
                        timepnt = KMLDoc.newpoint(name="Time is {!s}".format(row[_time_index]),
                                                  description="Time is {!s}".format(row[_time_index]),
                                                  coords=[(row[linelist[id].lon_col_index], row[linelist[id].lat_col_index])])

                        last_time = float(row[_time_index])


            firstline = False

            linecount+=1

    trajectory = list()

    for id in range(len(linelist)):
        trajectory.append(KMLDoc.newmultigeometry(name=linelist[id].name))
        trajectory[id]. newlinestring(name='test',description=row[_time_index],coords=line_coord[id])
        trajectory[id].style.linestyle.color = linelist[id].color # Red
        trajectory[id].style.linestyle.width = 10  # 10 pixels
        trajectory[id].style.iconstyle.scale = 3  # Icon thrice as big
        trajectory[id].style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/info-i.png'

    KMLDoc.save(os.path.join(os.path.dirname(_CSV_Path), "lines"+".kml"))