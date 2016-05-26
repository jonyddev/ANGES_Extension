
import sys
import time

from collections import defaultdict

from data_structures import markers
from data_structures import intervals
from data_structures import genomes
from data_structures import comparisons

import optimization
import assembly

    
def getOverlappingPairs(hom_fams):
    """
    getOverlappingPairs: receives a list of hom_fams and returns a list of overlapping pairs (each pair is a tuple containing two Locus)
    hom_fams - HomFam: list of objects from HomFam class
    """
        #import pdb; pdb.set_trace()
    loci_dict = defaultdict(list)
    overlapping_pairs_list = []
    for hom_fam_index, marker_family in enumerate(hom_fams):
        for locus_index, locus in enumerate(marker_family.loci):
           loci_dict[locus.species].append((hom_fam_index, locus_index))
        #endfor
    #endfor
    for species, species_indexes in loci_dict.items():
        # species name and a list of tuples with (hom_fam_index, locus_index)
        # hom_fam_index => access to hom_fam ID and loci list
        print (species, species_indexes)
        i = 1
        locus1 = hom_fams[species_indexes[0][0]].loci[species_indexes[0][1]]
        while i < len(species_indexes):
            locus2 = hom_fams[species_indexes[i][0]].loci[species_indexes[i][1]]
            print (locus1, locus2)
            is_overlapping_pair = locus1.overlappingPairs(locus2)
            if is_overlapping_pair:
                overlapping_pairs_list.append(is_overlapping_pair)
            #endif
            i = i + 1
        #endwhile
    #endfor
    return overlapping_pairs_list
#enddef

def filterByID(hom_fams, ids):
    """ 
    filterByID: Receives a list of IDs and remove them from the main markers list
    Returns a list 
    hom_fams - HomFam: list of HomFam
    ids - int: list of IDs to be removed from the hom_fams list
    """
    return filter(lambda fam: int(fam.id) not in ids, hom_fams)

def filterByCopyNumber(hom_fams, threshold):
    """
    filterByCopyNumber: receives a threshold and filter the main markers list by comparing the 
    copy_number with the threshold (if copy_number > threshold, remove from the list).
    Returns a list without the filtered markers.
    hom_fams - HomFam: List of markers
    theshold - int: filter using the threshold (filter if the copy_number is > threshold)
    """
    return filter(lambda fam: fam.copy_number <= threshold, hom_fams)

def strtime():
    """
    Function to format time to string
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def write_intervals( ints, f, log ):
    """
    Function to write intervals to file
    Arguments:
    ints: IntervalDict
    f: the file to write to
    log: log stream to write errors to
    """
    try:
        output = open( f, 'w' )
        for interval in ints.itervalues():
            output.write( str( interval ) + "\n" )
    except IOError:
        log.write( "%s  ERROR (master.py) - could not write intervals to"
                   "file: %s\n" %( strtime(), f ) )
        sys.exit()


class MasterScript:
    def __init__(self):
        self.log = -1
        self.debug = -1
        self.output_dir = -1
        self.io_dict = {}
        self.markers_param_dict = {}
        self.hom_fams_file_stream = -1
        self.pairs_file_stream = -1

    def isConfigSyntaxError(self, splitted_line, config_file, line_number):
        if len(splitted_line) != 3: # syntax error
            print("\n{} SYNTAX ERROR (process.py) in the configuration file\n'{}' at line {}: incorrect number of configuration parameters".format(strtime(), config_file, line_number))
            print("\tThe line '{}' must follow one of these syntaxes:"
                    .format(line[:-1]))
            print("\t\t'i> <input_type> <input_file_directory>'")
            print("\tor\n\t\t'o> output_directory <output_directory>'")
            print("\tor\n\t\t'm> <marker_parameter_name> <config_value>'")
            
            return True
        else:
            return False
        #endif
    #enddef

    def dealWithMarkersConfig(self, splitted_line):
        if splitted_line[2][0] == "[" and splitted_line[2][-1] == "]": # is a list definition
            splitted_line[2] = splitted_line[2][1:-1] # remove the [ ]
            splitted_line[2] = splitted_line[2].split(",") 
            splitted_line[2] = [element for element in splitted_line[2] if element != ""] # remove ''
            if splitted_line[2]: 
                self.markers_param_dict[splitted_line[1]] = splitted_line[2]
            else: # if empty list: do not want to filter by ID
                self.markers_param_dict[splitted_line[1]] = -1 
        #endif
        else:
            #splitted_line[1] = <marker_parameter_name>
            #splitted_line[2] = <config_value>
            self.markers_param_dict[splitted_line[1]] = int(splitted_line[2])
        #endelse
    #enddef

    def formatLine(self, line):
        line = line.rsplit("#",1)[0] # ignore comments
        line = line[:-1] # remove last character (space or newline)
        splitted_line = line.split(" ") 
        splitted_line = [element for element in splitted_line if element != ""]

        return line, splitted_line
    #enddef

    def readConfigFile(self, config_file, len_arguments):
        """
        Function to read the configuration file and return all the interpreted information
        Arguments:
        config_file - string: configuration file directory
        len_arguments - int: arguments length

        Returns: homologous families file directory
                 species tree file directory 
                 output directory
                 markers parameters (markers_doubled - int, markers_unique - int, markers_universal - int,
                                     markers_overlap - int, filter_copy_number - int, filter_by_id - list of int)
                where homologous families, species tree and output are keys for a dictionary and their respective 
                directories are the values for these keys;
                markers parameters is a dictionary using markers_doubled, ..., filter_by_id as keys and the values
                are the parameter values of each parameter (informed in the configuration file)
        """

        if len_arguments != 2:
            print ( "{}  ERROR (master.py -> process.py) - script called with incorrect number "
                     "of arguments.".format(strtime()))
            sys.exit()
        #endif
        
        try:
            with open(config_file, "r") as pairs_file_stream:
                #collect the information from config file
                syntax_error = False
                line_number = 1
                line = pairs_file_stream.readline()
                while len(line) > 0:
                    if line.startswith("i>") or line.startswith("o>") or line.startswith("m>"):
                        # input/output files directories of markers parameter config
                        line, splitted_line = self.formatLine(line)
                        syntax_error = self.isConfigSyntaxError(splitted_line, config_file, line_number)

                        if not syntax_error:
                            if line.startswith("m>"): # markers config
                                self.dealWithMarkersConfig(splitted_line)
                            #endif
                            else: # io directory name
                                #splitted_line[1] = <input_type>
                                #splitted_line[2] = <input_file_directory>
                                self.io_dict[splitted_line[1]] = splitted_line[2]
                            #endelse
                        #endif
                    #endif
                    #else: is a commented line/empty line/invalid line
                    line = pairs_file_stream.readline()
                    line_number = line_number + 1
                #endwhile
            #endwith    
        except IOError:
            print("{}  ERROR (master.py -> process.py) - could not open configuration file: {}\n"
                    .format(strtime(),config_file))
            sys.exit()
        
        if syntax_error:
            sys.exit()

        self.printDictInfo()
    #enddef

    def printDictInfo(self):
        print("Configuration File info:\n")
        for key, value in self.io_dict.items():
            print(key, value)
        for key, value in self.markers_param_dict.items():
            print(key, value)
        print("\n")

    def setFileStreams(self, homologous_families, pairs_file):
        self.log = open( self.output_dir + "/log", 'w' )
        self.debug = open( self.output_dir + "/debug", 'w' )

    def openIOFiles(hom_fams_file, pairs_file):
        pass

    def getIODictionary(self):
        return self.io_dict, self.markers_param_dict