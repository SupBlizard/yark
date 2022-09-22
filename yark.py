import sys, cmds

def main():
    print(cmds.utils.color(f"[ YARK ]\n", "red"))

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
                raise Exception(f"Command {cmd} does not exist.")

            # Run command and print return value
            if rtn := cmds.run(cmd(), args):
                print(rtn)
            else: print()

        except Exception as e:
            print(cmds.utils.color(e, "red"))
        except KeyboardInterrupt:
            print()
            break

    # Close database
    cmds.db.close()


if __name__ == "__main__":
    main()
