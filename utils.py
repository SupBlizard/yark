import time, re
from colorama import Style, Fore, Back

# CONSTANTS
RYD_API = "https://returnyoutubedislikeapi.com/"
WAYBACK = "https://web.archive.org/web/"
YOUTUBE = "https://www.youtube.com/"
CONFIGS_DEFAULT = {"thumbnails": True, "comments": True}
DEFAULT_DESC = "Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world on YouTube."
DELETE = "\033[K\033[A"*2

ID_LENGTH = {
    "video": 11,
    "playlist": 34
}

YES = ["yes", "y", "yep", "sure", "ight", "ok", "okey", "go ahead", "cool", "ye", "yeh", "yee", "do it", "why not"]
MAYBE = ["maybe", "perhaps", "possibly", "conceivably", "probably"]
NO = ["no", "n", "nah", "nou", "dont", "don't"]


def is_(thing, id):
    if not id: raise ValueError("Missing ID")
    length = ID_LENGTH[thing]

    if len(id) == length:
        chars = "[0-9A-Za-z_-]"
        start = ""
        if thing == "playlist":
            start = "^PL"
            length -= 2
        expression = re.search(f"{start}{chars}{{{length}}}", id)
        if expression: return expression.group()
    raise ValueError(f"Invalid {thing} ID")



def err_format(msg, id="", process="youtube"):
    if id: id = f"[{process}] {id}: "
    return f"{color('ERROR:', 'red')} {id}{msg}"

def step_format(position, length, started):
    measures = ["sec", "min", "hr"]
    eta = (time.perf_counter() - started) * (length / position - 1)
    if eta < 0: eta = 0

    measure = 0
    for i in range(2):
        if eta >= 60:
            eta /= 60
            measure += 1
    eta = round(eta, 1)
    if eta % 1 == 0: eta = int(eta)

    print(f"\n{color(f'[{position} / {length}]', 'cyan')} ETA: {eta} {measures[measure]}")

def user_confirm():
    doit = input(f"{color('[', 'red')}{color('confirm', 'red', True)}{color(']:', 'red')} ").lower()
    if doit in YES: return True
    elif doit in MAYBE: print("I'll let you think about it.")
    elif doit in NO: pass
    else: print("What ?")
    return False

# Custom logger
class Logger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        # TODO: Save event in debug log
        pass

    def error(self=None, msg=None):
        # TODO: Save event in debug log
        if msg: print(msg)

    def info(msg, vid="", process="youtube"):
        if vid: vid = f"[{process}] {vid}: "
        print(f"{color('INFO:', 'cyan')} {vid}{msg}")


def color(text, color="", bright=""):
    try:
        if color: color = getattr(Fore, color.upper())
        if bright: bright = getattr(Style, "BRIGHT")
    except AttributeError:
        color, bright = ("","")
    return f"{bright}{color}{text}{Style.RESET_ALL}"
