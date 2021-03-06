from datetime import datetime, timedelta
import logging
import os
import platform
import shlex
import subprocess
import sys
import threading

import porcupine
from porcupine import dirs

log = logging.getLogger(__name__)
LOG_DIR = os.path.join(dirs.cachedir, 'logs')    # used in __main__.py
_FILENAME_FORMAT = '%Y-%m-%dT%H-%M-%S.txt'


def _remove_old_logs():
    for filename in os.listdir(LOG_DIR):
        try:
            log_date = datetime.strptime(_FILENAME_FORMAT, filename)
        except ValueError:
            log.info("%s contains a file with an unexpected name: %s",
                     LOG_DIR, filename)
            continue

        how_old = datetime.now() - log_date
        if how_old > timedelta(days=3):
            path = os.path.join(LOG_DIR, filename)
            log.info("%s is more than 3 days old, removing it", path)
            os.remove(path)


def _run_command(command):
    try:
        output = subprocess.check_output(shlex.split(command),
                                         stderr=subprocess.STDOUT)
        log.info("output from '%s':\n%s", command,
                 output.decode('utf-8', errors='replace'))
    except FileNotFoundError as e:
        log.info("cannot run '%s': %s", command, e)
    except (subprocess.CalledProcessError, OSError):
        log.warning("unexpected error when running '%s'", command,
                    exc_info=True)


def setup(verbose):
    os.makedirs(os.path.join(dirs.cachedir, 'logs'), exist_ok=True)
    logfile = os.path.join(dirs.cachedir, 'logs',
                           datetime.now().strftime(_FILENAME_FORMAT))

    if sys.stdout is None and sys.stderr is None:
        # running in pythonw.exe, make sure to log everything
        #
        # logging.StreamHandler has a stream attribute which is set to the file
        # it opens, but that's undocumented, so need to open the file myself
        # and use StreamHandler
        sys.stdout = sys.stderr = open(logfile, 'x', errors='replace')
        file_handler = logging.StreamHandler(sys.stderr)
        file_handler.setLevel(logging.DEBUG)
        print_handler = None

    else:
        file_handler = logging.FileHandler(logfile, 'x')
        file_handler.setLevel(logging.DEBUG)
        print_handler = logging.StreamHandler(sys.stderr)
        print_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)

    handlers = [file_handler]
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(name)s %(levelname)s: %(message)s'))
    if print_handler is not None:
        handlers.append(print_handler)
        print_handler.setFormatter(logging.Formatter(
            '%(name)s %(levelname)s: %(message)s'))

    logging.basicConfig(level=logging.DEBUG,  # no idea why this is needed
                        handlers=handlers,
                        format="[%(levelname)s] %(name)s: %(message)s")

    log.debug("starting Porcupine %s from '%s'", porcupine.__version__,
              porcupine.__path__[0])
    log.debug("log file: %s", logfile)
    log.debug("PID: %d", os.getpid())
    log.debug("running on Python %d.%d.%d from '%s'",
              *(list(sys.version_info[:3]) + [sys.executable]))
    log.debug("platform.system() returned %r", platform.system())
    log.debug("platform.platform() returned %r", platform.platform())
    if platform.system() != 'Windows':
        # lsb_release is a python script on ubuntu so running it takes
        # about 0.12 seconds on this system, i really want porcupine to
        # start as fast as possible
        _run_command('uname -a')
        threading.Thread(target=_run_command, args=['lsb_release -a']).start()

    # don't fail to run if old logs can't be deleted for some reason
    try:
        _remove_old_logs()
    except OSError:
        log.exception("unexpected problem with removing old log files")
