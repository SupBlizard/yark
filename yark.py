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
            args = input("> ").split()
            if len(args) == 0: continue
            cmd = args.pop(0).capitalize()
            if cmd == "Exit": break

            try:
                # Check if command exists
                cmd = getattr(cmds, cmd)
                if type(cmd) != type: raise TypeError
            except (AttributeError, TypeError):
                raise Exception(f"Command {cmd} does not exist.")

            # Run command and print return value
            if rtn := cmds.run(cmd(), args):
                print(rtn)
        except Exception as e:
            print(color(e, "red"), end="\n")
        except KeyboardInterrupt:
            print()
            break

        print()


if __name__ == "__main__":
    main()
