import sys

from shared_tasks.logging_config import get_logger


def reporthook(blocknum, blocksize, totalsize):
    logger = get_logger()
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        log_message = f"{percent:5.1f}% {readsofar:{len(str(totalsize))}d} / {totalsize}"
        if blocknum % 10 == 0 or readsofar >= totalsize:
            logger.info(log_message)
        if readsofar >= totalsize:  # near the end
            logger.info("Download completed.")
    else:  # total size is unknown
        logger.info(f"Read {readsofar} bytes so far.")
