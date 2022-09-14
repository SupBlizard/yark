import sys, cmds, colorama

def main():
    print(f"{colorama.Fore.RED} [ YARK ] {colorama.Style.RESET_ALL}\n")

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
            print()

        except Exception as e:
            print(f"{colorama.Fore.RED}{e}{colorama.Style.RESET_ALL}\n")
        except KeyboardInterrupt:
            print()
            break


    cmds.db.close()


if __name__ == "__main__":
    main()
