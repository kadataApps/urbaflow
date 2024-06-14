#!/usr/bin/python

import re
import os
from distutils import dir_util


def replace_parameters_in_string(string, replaceDict):
    '''
    Replace all occurences in string
    '''

    def replfunc(match):
        if match.group(0) in replaceDict:
            return replaceDict[match.group(0)]
        else:
            return None

    regex = re.compile('|'.join(re.escape(x)
                                for x in replaceDict), re.IGNORECASE)
    string = regex.sub(replfunc, string)
    return string


def replace_parameters_in_script(scriptPath, replaceDict):
    '''
    Replace all parameters in sql scripts
    with given values
    '''

    try:
        data = ''
        with open(scriptPath, encoding='utf-8-sig') as fin:
            data = fin.read()  # .decode("utf-8-sig")

        data = replace_parameters_in_string(data, replaceDict)
        # data = data.encode('utf-8')
        with open(scriptPath, 'w') as fout:
            fout.write(data)

    except IOError as e:
        msg = u"<b>Erreur lors du paramétrage des scripts d'import: %s</b>" % e
        return msg


def copy_files_to_temp( source, target):
    '''
    Copy cadastre scripts
    into a temporary folder
    '''
    # copy script directory
    try:
        dir_util.copy_tree(source, target)
        os.chmod(target, 0o777)
    except IOError as e:
        msg = u"<b>Erreur lors de la copie des scripts d'import: %s</b>" % e
        return msg

    return None

