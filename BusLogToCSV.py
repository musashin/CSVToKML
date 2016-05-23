"""
A script to convert Bus Monitor Log files to CSV files easily importable to Excel.
Note: only parameters are exported, and read/write appear are different entries at different times.
"""

import sys
import os.path
import re
import collections

__commentLinePattern__ = re.compile(r'^\*[\s]*[\w:\s\.=]*$')
__aliasLinePattern__ = re.compile(r"""^\*[\s]*ALIAS[\s]*:                #beginning of ALIAS comment line
                                 [\s](?P<busID>[\d]*)\.(?P<portID>[\d]*)\.(?P<ID>[\d]*)
                                 [\s]*=[\s]*                            # equality
                                 (?P<name>[\w]*)
                                 [\s]*$""", re.VERBOSE)                 # end of line
__paramUpdatePattern__ = re.compile(r"""^[\s]*
                                    (?P<time>[\d.]*)
                                    ,(WRITE_PARAM|READ_PARAM|WRITE_MSG_UNPACK_PARAM|READ_MSG_UNPACK_PARAM)[\s]*,[\s]*
                                    (?P<paramID>[\d]*),
                                    (?P<value>.*)
                                    $""", re.VERBOSE)
__openPortPattern__ = re.compile(r"""^[\s]*[\d.]*[\s]*,[\s]*OPEN[\s]*,
                                     (?P<busID>[\d]*)
                                     .
                                     (?P<portID>[\d]*)
                                     [\s]*,[\s]*$""", re.VERBOSE)
__closePortPattern__ = re.compile(r"""^[\s]*[\d.]*[\s]*,[\s]*CLOSE[\s]*,
                                     (?P<busID>[\d]*)
                                     .
                                     (?P<portID>[\d]*)
                                     [\s]*,[\s]*$""", re.VERBOSE)
__invalid_ID__ = 0xFFFFFFFF

BusAddress = collections.namedtuple('BusAddress', 'busID portID ID')
__invalid_Address__ = BusAddress(busID=__invalid_ID__, portID=__invalid_ID__, ID=__invalid_ID__)
__current_context__ = __invalid_Address__
__aliases__ = dict()


class LogFileParameterData:
    """
    This class is:
    - A data container for the parameter values read in the log files.
    - An iterable object that returns CSV file lines
    """

    def __init__(self, aliases):
        """
        Constructor
        """
        self.clear()
        self.aliases = aliases

    def clear(self):
        self.time = list()  #a list for the time axis
        self.data = dict()  #a dictionnary of data streams.
        self.current = 0


    def add_new_data_stream(self, address):
        """
        Add a new data stream.
        If the there are existing values for other data stream (at previous times),
        blank entries are automatically added to the created data stream.
        ""
        :param address: address in bus infrastructure the data stream corresponds to.
        """
        if self.get_name_from_bus_address(address) not in self.data:
            if len(self.data) > 0:
                number_of_missing_entries = max([len(v) for (k, v) in self.data.iteritems()])
                self.data[self.get_name_from_bus_address(address)] = [' '] * number_of_missing_entries
            else:
                self.data[self.get_name_from_bus_address(address)] = list()

    def add_data_point(self, time, address, value):
        """
        Add a new data point to the collection.

        This method:
        - Automatically align time entries by ensuring that data is automatically created for all the streams (the last
        recorded value is automatically inserted).
        - Convert addresses to names using the alias dictionnary passed at creation.
        """
        self.time.append(time)

        self.add_new_data_stream(address)

        self.data[self.get_name_from_bus_address(address)].append(value)

        other_data_streams = {k: v for (k, v) in self.data.iteritems() if self.get_name_from_bus_address(address) != k}

        for name, data_stream in other_data_streams.iteritems():
            data_stream.append(data_stream[len(data_stream)-1])

    def get_name_from_bus_address(self, address):
        """
        Given a bus address, return the equivalent alias name

        Note: if no alias entry existing, the returned name is a string corresponding to the bus address.
        """
        try:
            return self.aliases[address]
        except KeyError as e:
            return str(address.busID)+'.'+str(address.portID)+'.'+str(address.ID)
        except Exception as e:
            sys.stderr.write('Could not convert address to name (address is {!s}).\n'.format(address))
            sys.exit(2)

    def get_data_stream_names_line(self):
        """
        The the data stream names (the first line in the CSV file)
        """
        names = ['TIME(s)']

        for key in self.data:
            names.append(key)

        return ','.join(names)

    def __iter__(self):
        return self

    def next(self):
        """
        Next iteration.
        Returns aC CSV file at the current time entries and move to the next time entry.
        """
        if self.current >= len(self.time):
            raise StopIteration
        else:
            self.current += 1
            csvline = ''
            try:
                csvline = self.time[self.current-1]+','
                csvline += ','.join([str(val[self.current-1]) for (name, val) in self.data.iteritems()])
            except Exception as e:
                pass

            return csvline

__file_data__ = LogFileParameterData(__aliases__)


def print_help():
    """
    Print tool usage
    """
    print "PURPOSE"
    print '\tA script to convert Bus Monitor Log files to CSV files easily importable to Excel.'
    print '\tNote: only parameters are exported, and read/write appear as different entries at different times.'
    print "USAGE"
    print '\tSimply execute passing the log file path as an argument. A CSV file corresponding to the log file will be' +\
          'created in the same folder.'
    print '\tAlternatively, pass a folder, and all the file with a \'bus.log\' extension will be converted.'


def get_options():
    """
    Retrieve options, either from the command line arguments, or opening
    dialogs if necessary.
    """
    if len(sys.argv) != 2:
        sys.stderr.write('Invalid argument.\n')
        print_help()
        sys.exit(2)
    else:
        try:
            path = str(sys.argv[1])
        except Exception as e:
            sys.stderr.write('Argument must be a string (path to file or folder) [{!s}].\n'.format(e))
            sys.exit(2)
        else:
            return path


def parse_alias_line(line, line_number):
    """
    Update the aliases dictionnary from alias log file line.
    :param line: log file line
    :param line_number:  log file line number
    :return: none
    """

    matched_groups = __aliasLinePattern__.match(line)
    try:
        __aliases__[BusAddress(busID=int(matched_groups.group('busID')),
                               portID=int(matched_groups.group('portID')),
                               ID=int(matched_groups.group('ID')))] = matched_groups.group('name')
    except Exception as e:
        sys.stderr.write('Could not import alias at line {!s} [{!s}].\n'.format(line_number, e))
        sys.exit(2)


def parse_parameter_update_line(line, line_number):
    """
    Add a new data point from  a log file parameter read or write entry.
    :param line: log file line
    :param line_number: log file line number
    :return: none
    """

    matched_groups = __paramUpdatePattern__.match(line)

    try:
        address = BusAddress(busID=__current_context__.busID,
                             portID=__current_context__.portID,
                             ID=int(matched_groups.group('paramID')))

        __file_data__.add_data_point(matched_groups.group('time'),
                                     address,
                                     matched_groups.group('value'))

    except Exception as e:
        sys.stderr.write('Malformed parameter update at line {!s} [{!s}].\n'.format(line_number, e))
        sys.exit(2)


def parse_open_port_line(line, line_number):
    """
    Update current context from an OPEN PORT log entry.
    :param line: content of the log file line.
    :param line_number: log file line number.
    :return: None
    """
    global __current_context__

    matched_groups = __openPortPattern__.match(line)

    try:
        __current_context__ = BusAddress(busID=int(matched_groups.group('busID')),
                                         portID=int(matched_groups.group('portID')),
                                         ID=__invalid_ID__)

    except Exception as e:
        sys.stderr.write('Invalid ID at line {!s} [{!s}].\n'.format(line_number, e))
        sys.exit(2)


def parse_close_port_line(line, line_number):
    """
    Reset the current context following a CLOSE port log entry.
    :param line: content of the log file line.
    :param line_number: log file line number.
    :return:
    """
    global __current_context__

    matched_groups = __closePortPattern__.match(line)

    try:
        if int(matched_groups.group('busID')) != __current_context__.busID \
           or int(matched_groups.group('portID')) != __current_context__.portID:

            sys.stderr.write('Malformed file: the context closed at line {!s} was never opened [{!s}], current context is {!s}.\n'.format(line_number,line,__current_context__))

    except Exception as e:
        sys.stderr.write('Invalid ID at line {!s} [{!s}].\n'.format(line_number, e))
        sys.exit(2)
    else:
        __current_context__ = __invalid_Address__

# Below is a list that associates a Regex Pattern unique to a log file line type to a dedicated line handler.
__line_handlers__ = [{'pattern': __aliasLinePattern__,      'handler': parse_alias_line},
                     {'pattern': __paramUpdatePattern__,    'handler': parse_parameter_update_line},
                     {'pattern': __openPortPattern__,       'handler': parse_open_port_line},
                     {'pattern': __closePortPattern__,      'handler': parse_close_port_line}]


def convert_log_to_csv(input_file_path):
    """
    Convert a bus.log file to a CSV file
    """

    __current_context__ = __invalid_Address__
    __aliases__ = dict()
    __file_data__.clear()

    print 'Opened {!s}'.format(input_file_path)

    #Validate the extension
    if input_file_path.split('.')[-2:] != ['bus', 'log']:
        sys.stderr.write('File {!s} does not have the expected extension.\n'.format(input_file_path))
        return

    current_line_number = 0

    try:
        with open(input_file_path) as file:

            for line in file:
                current_line_number += 1

                for line_type in __line_handlers__:
                    if line_type['pattern'].match(line):
                        line_type['handler'](line, current_line_number)

    except Exception as e:
        sys.stderr.write('Could not parse input file.\n'.format(e))
    else:
        csv_file_path = os.path.splitext(input_file_path)[0] + '.csv'
        # Create the CSV file from __file_data__
        try:

            with open(csv_file_path, 'w') as CSVfile:

                CSVfile.write(__file_data__.get_data_stream_names_line() + '\n')

                for data in __file_data__:
                    CSVfile.write(data + '\n')

        except Exception as e:
            sys.stderr.write('Could not write CSV file [{!s}].\n'.format(e))
        print 'created {!s}'.format(csv_file_path)

if __name__ == "__main__":
    """
    Entry point
    """

    path = get_options()

    if os.path.isfile(path):
        list_of_file_to_convert = [path]
    elif os.path.isdir(path):
        list_of_file_to_convert = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))
                                   and f.split('.')[-2:] == ['bus', 'log']]
    else:
        sys.stderr.write('argument {!s} should be a folder or file path.'.format(path))
        sys.exit(2)

    # Read the log file an update __file_data__
    for input_file_path in list_of_file_to_convert:
        convert_log_to_csv(input_file_path)
