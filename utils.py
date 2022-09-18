import colorama

# CONSTANTS
DEFAULT_DESC = "Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world on YouTube."


# Custom logger
class Logger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        # Save event in debug log
        pass

    def error(self, msg):
        # Save event in debug log
        print(msg)

    def info(msg, vid):
        print(f"{colorama.Fore.CYAN}INFO:{colorama.Style.RESET_ALL}  [youtube] {vid}: {msg}")
