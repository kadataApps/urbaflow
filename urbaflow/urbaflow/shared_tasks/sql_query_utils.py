#!/usr/bin/python

import re


def replace_parameters_in_string(string, replace_dict):
    """
    Replace all occurences in string
    """

    def replfunc(match):
        if match.group(0) in replace_dict:
            return replace_dict[match.group(0)]
        else:
            return None

    regex = re.compile("|".join(re.escape(x) for x in replace_dict), re.IGNORECASE)
    string = regex.sub(replfunc, string)
    return string


def replace_parameters_in_script(script_path, replace_dict):
    """
    Replace all parameters in sql scripts
    with given values
    """

    try:
        data = ""
        with open(script_path, encoding="utf-8-sig") as fin:
            data = fin.read()  # .decode("utf-8-sig")

        data = replace_parameters_in_string(data, replace_dict)
        # data = data.encode('utf-8')
        with open(script_path, "w") as fout:
            fout.write(data)

    except IOError as e:
        msg = "<b>Erreur lors du paramétrage des scripts d'import: %s</b>" % e
        return msg
