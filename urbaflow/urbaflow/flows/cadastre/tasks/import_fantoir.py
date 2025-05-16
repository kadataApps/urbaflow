import os
from pathlib import Path
import re


from shared_tasks.config import majic_config
from shared_tasks.db_engine import create_engine
from shared_tasks.db_sql_utils import run_sql_script
from shared_tasks.logging_config import get_logger


def chunk(iterable, n=100000, padvalue=None):
    """
    Chunks an iterable (file, etc.)
    into pieces
    """
    from itertools import zip_longest

    return zip_longest(*[iter(iterable)] * n, fillvalue=padvalue)


def import_fantoir_file(fantoir_source_dir: Path):
    """
    Method wich read each majic file
    and bulk import data intp temp tables
    Returns False if no file processed
    """
    logger = get_logger()
    config = majic_config()
    max_insert_rows = int(config["max_insert_rows"])
    fantoir_files_found = {}

    # Regex to remove all chars not in the range in ASCII table from space to ~
    # http://www.catonmat.net/blog/my-favorite-regex/
    r = re.compile(r"[^ -~]")
    r_quote_string = re.compile(r"'")

    # Loop through all files to find fantoir file

    table = "fanr"
    value = "fan"
    regex_filename = re.compile(r"(" + value + ")", re.IGNORECASE)
    # Get fantoir files
    file_list = []
    for root, dirs, files in os.walk(fantoir_source_dir):
        for i in files:
            # if os.path.split(i)[1] == value:
            if re.search(regex_filename, os.path.split(i)[1]) is not None:
                fpath = os.path.join(root, i)
                logger.info(fpath)
                # Add file path to the list
                file_list.append(fpath)

    fantoir_files_found[table] = file_list

    # Print result of exploring majic files
    logger.info(fantoir_files_found)
    if not fantoir_files_found:
        logger.warning("No fantoir file found in %s" % fantoir_source_dir)
        return False

    # Drop & create tables where to import data
    logger.info("Drop & create table %s" % table)

    e = create_engine()
    with e.begin() as conn:
        sql = (
            'DROP TABLE IF EXISTS "%(table)s"; CREATE TABLE "%(table)s" (tmp text);'
            % {"table": table}
        )
        run_sql_script(sql=sql, connection=conn)

        current_file = 0
        for fpath in fantoir_files_found[table]:
            current_file += 1
            logger.info(
                "Fichier "
                + str(current_file)
                + "/"
                + str(len(fantoir_files_found[table]))
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
                                r_quote_string.sub("\\'", r.sub(" ", x.strip("\r\n"))),
                            )
                            for x in a
                            if x
                        ]
                    )
                    run_sql_script(sql=sql, connection=conn)
        logger.info("Import done and commited for %s" % fpath)
