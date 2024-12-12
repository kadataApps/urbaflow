import os
from pathlib import Path
import re

from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.config import majic_config
from shared_tasks.logging_config import get_logger


def chunk(iterable, n=100000, padvalue=None):
    """
    Chunks an iterable (file, etc.)
    into pieces
    """
    from itertools import zip_longest

    return zip_longest(*[iter(iterable)] * n, fillvalue=padvalue)


def get_majic_source_filenames(config):
    majic_source_filenames = [
        {
            "key": "[FICHIER_BATI]",
            "value": config["bati"],
            "table": "bati",
            "required": True,
        },
        {
            "key": "[FICHIER_FANTOIR]",
            "value": config["fantoir"],
            "table": "fanr",
            "required": True,
        },
        {
            "key": "[FICHIER_LOTLOCAL]",
            "value": config["lotlocal"],
            "table": "lloc",
            "required": False,
        },
        {
            "key": "[FICHIER_NBATI]",
            "value": config["nbati"],
            "table": "nbat",
            "required": True,
        },
        {
            "key": "[FICHIER_PDL]",
            "value": config["pdll"],
            "table": "pdll",
            "required": False,
        },
        {
            "key": "[FICHIER_PROP]",
            "value": config["prop"],
            "table": "prop",
            "required": True,
        },
    ]
    return majic_source_filenames


def import_majic_files(majic_source_dir: Path):
    """
    Method wich read each majic file
    and bulk import data intp temp tables
    Returns False if no file processed
    """
    logger = get_logger()
    config = majic_config()
    max_insert_rows = int(config["max_insert_rows"])
    majic_source_filenames = get_majic_source_filenames(config)
    total_steps = len(majic_source_filenames)
    majic_files_found = {}

    # Regex to remove all chars not in the range in ASCII table from space to ~
    # http://www.catonmat.net/blog/my-favorite-regex/
    r = re.compile(r"[^ -~]")
    r_quote_string = re.compile(r"'")

    # Loop through all majic files

    # 1st path to build the complete list for each majic source type (nbat, bati, lloc, etc.)
    # and read 1st line to get departement and direction to compare to inputs
    depdirs = {}
    for item in majic_source_filenames:
        table = item["table"]
        value = item["value"]
        regex_filename = re.compile(r"(" + value + ")", re.IGNORECASE)
        # Get majic files for item
        maj_list = []
        for root, dirs, files in os.walk(majic_source_dir):
            for i in files:
                # if os.path.split(i)[1] == value:
                if re.search(regex_filename, os.path.split(i)[1]) is not None:
                    fpath = os.path.join(root, i)
                    logger.info(fpath)
                    # Add file path to the list
                    maj_list.append(fpath)

                    # Store depdir for this file
                    # avoid fantoir, as now it is given for the whole country
                    if table == "fanr":
                        continue
                    # Get depdir : first line with content
                    with open(fpath) as fin:
                        for a in fin:
                            if len(a) < 4:
                                continue
                            depdir = a[0:3]
                            depdirs[depdir] = True
                            break

        majic_files_found[table] = maj_list

    # print result of exploring majic files
    files_to_proceed_counter = 0
    for table in majic_files_found:
        logger.info(table)
        files_to_proceed_counter += len(majic_files_found[table])

    logger.info("Majic files found : (%s files)" % files_to_proceed_counter)
    logger.info(majic_files_found)
    logger.info("Directions found :")
    logger.info(depdirs)

    local_step = 0
    e = create_engine()
    with e.begin() as conn:
        for item in majic_source_filenames:
            table = item["table"]
            local_step += 1
            logger.info(
                "Etape " + str(local_step) + "/" + str(total_steps) + ": " + table
            )

            # Drop & create tables where to import data
            logger.info("Drop & create table %s" % table)
            sql = (
                'DROP TABLE IF EXISTS "%(table)s"; CREATE TABLE "%(table)s" (tmp text);'
                % {"table": table}
            )
            run_sql_script(sql=sql, connection=conn)

            current_file = 0
            for fpath in majic_files_found[table]:
                current_file += 1
                logger.info(
                    "Fichier "
                    + str(current_file)
                    + "/"
                    + str(len(majic_files_found[table]))
                )
                # read file content
                with open(fpath, encoding="ascii", errors="replace") as fin:
                    # Divide file into chuncks
                    for a in chunk(fin, max_insert_rows):
                        # Build INSERT list
                        sql = "\n".join(
                            [
                                "INSERT INTO \"%s\" VALUES (E'%s');"
                                % (
                                    table,
                                    r_quote_string.sub(
                                        "\\'", r.sub(" ", x.strip("\r\n"))
                                    ),
                                )
                                for x in a
                                if x and depdirs.get(x[0:3]) is True
                            ]
                        )
                        run_sql_script(sql=sql, connection=conn)
                logger.info("Import done and commited for %s" % fpath)
