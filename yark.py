import sys, cmds, logging
from utils import color


# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    print(color("[ YARK ]\n", "red"))

    while True:
        try:
            # Get user input
            args = input("> ").split()
            if len(args) == 0:
                continue
            else: cmd = args.pop(0).capitalize()
            if cmd == "Exit": break
        except KeyboardInterrupt:
            print()
            break;

        try:
            # Check if command exists
            try:
                cmd = getattr(cmds, cmd)
                if type(cmd) != type: raise TypeError
            except (AttributeError, TypeError):
                raise Exception(f"Command {cmd} does not exist.\n")

            # Run command and print return value
            if rtn := cmds.run(cmd(), args):
                print(rtn)
            else: print()

        except Exception as e:
            print(color(e, "red"), end="\n\n")
        except KeyboardInterrupt:
            print()
            break


if __name__ == "__main__":
    main()
