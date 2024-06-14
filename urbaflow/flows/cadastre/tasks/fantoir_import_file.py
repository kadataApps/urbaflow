import os, glob
import io
import string, sys
import re
import time
import tempfile
import shutil

from datetime import datetime

from utils.config import majic_config, db_config
from utils.dbutils import pg_connection


class import_fantoir_file(object):

    def __init__(self, path):
        self.majic_config = majic_config()
        self.majicSourceDir = path

        self.maxInsertRows = int(self.majic_config['maxinsertrows'])


    def chunk(self, iterable, n=100000, padvalue=None):
        '''
        Chunks an iterable (file, etc.)
        into pieces
        '''
        from itertools import zip_longest
        return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)
    
    def startImport(self):
        '''
        Method wich read each majic file
        and bulk import data intp temp tables
        Returns False if no file processed
        '''
        majicFilesFound = {}

        # Regex to remove all chars not in the range in ASCII table from space to ~
        # http://www.catonmat.net/blog/my-favorite-regex/
        r = re.compile(r"[^ -~]")
        rQuoteString = re.compile(r"'")

        # Loop through all files to find fantoir file
    
        table = 'fanr'
        value = 'fan'
        regexFileName = re.compile(r'('+value+')', re.IGNORECASE)
        # Get majic files for item
        majList = []
        for root, dirs, files in os.walk(self.majicSourceDir):
            for i in files:
                #if os.path.split(i)[1] == value:
                if re.search(regexFileName, os.path.split(i)[1]) is not None:
                    fpath = os.path.join(root, i)
                    print(fpath)
                    # Add file path to the list
                    majList.append(fpath)

        majicFilesFound[table] = majList
        
        #Print result of exploring majic files
        
        # 2nd path to insert data
        # Open connection & set search_path
        connection = pg_connection()
    
        # Drop & create tables where to import data
        print("Drop & create table %s" % table)
        sql = "DROP TABLE IF EXISTS \"%(table)s\"; CREATE TABLE \"%(table)s\" (tmp text);" % {
            'table': table}
        connection.executeSql(sql)
        connection.commit()

        currentFile = 0
        for fpath in majicFilesFound[table]:
            currentFile += 1
            print("Fichier " + str(currentFile) + '/' + str(len(majicFilesFound[table])))
            # read file content
            with open(fpath, encoding='ascii', errors='replace') as fin:
                # Divide file into chuncks
                for a in self.chunk(fin, self.maxInsertRows):
                    # Build INSERT list
                    sql = '\n'.join(
                        [
                            "INSERT INTO \"%s\" VALUES (E\'%s\');" % (
                                table,
                                rQuoteString.sub("\\'", r.sub(' ', x.strip('\r\n')))
                            ) for x in a if x
                        ]
                    )
                    connection.executeSql(sql)
            connection.commit()
            print("Import done and commited for %s" % fpath)
        connection.closeConnection()
