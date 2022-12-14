import time, re, logging, math
from colorama import Style, Fore, Back

# CONSTANTS
RYD_API = "https://returnyoutubedislikeapi.com/"
WAYBACK = "https://web.archive.org/web/"
YOUTUBE = "https://www.youtube.com/"
DEFAULT_DESC = "Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world on YouTube."
DELETE = "\033[K\033[A"*2

# https://stackoverflow.com/a/14693789/12727730
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

YES = ["yes", "y", "yep", "sure", "ight", "ok", "okey", "go ahead", "cool", "ye", "yeh", "yee", "do it", "why not"]
MAYBE = ["maybe", "perhaps", "possibly", "conceivably", "probably"]
NO = ["no", "n", "nah", "nou", "dont", "don't"]


def is_video(id):
    if not id: raise ValueError("Missing ID")
    if len(id) == 11:
        expression = re.search("[0-9A-Za-z_-]{11}", id)
        if expression: return expression.group()
    raise ValueError(f"Invalid video ID")


TIMEUNITS = ["sec", "min", "hr"]
def format_time(tim):
    unit = 0
    if tim < 0: tim = 0
    for i in range(2):
        if tim >= 60:
            tim /= 60
            unit += 1
        else: break

    tim = math.floor(tim*10)/10
    if tim % 1 == 0: tim = int(tim)
    return {"time":tim, "unit":TIMEUNITS[unit]}

def step_format(position, length, started):
    eta = format_time((time.perf_counter() - started) * (length / position - 1))
    print(f"\n{color(f'[{position} / {length}]', 'cyan')} ETA: {eta['time']} {eta['unit']}")

def user_confirm():
    doit = input(f"{color('[', 'red')}{color('confirm', 'red', True)}{color(']:', 'red')} ").lower()
    if doit in YES: return True
    elif doit in MAYBE: print("I'll let you think about it.")
    elif doit not in NO: print("What ?")
    return False

# Custom logger
class YtLogger(object):
    def __cleanup(self, msg):
        return ANSI_ESCAPE.sub("", msg)

    def debug(self, msg):
        logging.debug(self.__cleanup(msg))

    def warning(self, msg):
        logging.warning(self.__cleanup(msg))

    def error(self, msg):
        logging.error(self.__cleanup(msg).replace("ERROR: ",""))

    def info(self, msg):
        logging.info(self.__cleanup(msg))


def color(text, color="", bright=""):
    try:
        if color: color = getattr(Fore, color.upper())
        if bright: bright = getattr(Style, "BRIGHT")
    except AttributeError:
        color, bright = ("","")
    return f"{bright}{color}{text}{Style.RESET_ALL}"
