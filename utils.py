from colorama import *

# CONSTANTS
DEFAULT_DESC = "Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world on YouTube."

def err_format(msg, id="", process="youtube"):
    if id: id = f"[{process}] {id}: "
    return f"{Fore.RED}ERROR: {Style.RESET_ALL}{id}{msg}"

# Custom logger
class Logger(object):
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        # TODO: Save event in debug log
        pass

    def error(self=None, msg=None):
        # TODO: Save event in debug log
        if msg: print(msg)

    def info(msg, vid=""):
        vid = "" if vid=="" else " "+vid
        print(f"{Fore.CYAN}INFO: {Style.RESET_ALL} [youtube]{vid}: {msg}")
