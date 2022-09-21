import time
from colorama import Style, Fore, Back

# CONSTANTS
VIDEO_ID_LENGTH = 11
PLAYLIST_ID_LENGTH = 34
RYD_API = "https://returnyoutubedislikeapi.com/"
WAYBACK = "https://web.archive.org/web/"
YOUTUBE = "https://www.youtube.com/"
DEFAULT_DESC = "Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world on YouTube."
DELETE = "\033[K\033[A"*2

def err_format(msg, id="", process="youtube"):
    if id: id = f"[{process}] {id}: "
    return f"{Fore.RED}ERROR: {Style.RESET_ALL}{id}{msg}"


def step_format(position, length, started):
    measures = ["sec", "min", "hr"]
    eta = (time.time() - started) * (length / position - 1)
    if eta < 0: eta = 0

    measure = 0
    for i in range(2):
        if eta >= 60:
            eta /= 60
            measure += 1
    eta = round(eta, 1)
    if eta % 1 == 0: eta = int(eta)

    print(f"\n{Fore.CYAN}[{position} / {length}]{Style.RESET_ALL} ETA: {eta} {measures[measure]}")

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

    def info(msg, vid="", process="youtube"):
        if vid: vid = f"[{process}] {vid}: "
        print(f"{Fore.CYAN}INFO: {Style.RESET_ALL}{vid}{msg}")
