import json
from utils import color, YtLogger



DEFAULT_CONFIGS = {"thumbnails": True, "comments": True}
options = {
    "quiet": True,
    "logger": YtLogger(),
    "extract_flat":"in_playlist"
}


# Read configuration or write defaults
with open("configs.json", "a+") as config_file:
    try:
        config_file.seek(0)
        configs = json.loads(config_file.read())
        if configs.keys() != DEFAULT_CONFIGS.keys():
            raise ValueError("Invalid keys")

        for key in DEFAULT_CONFIGS:
            if not isinstance(configs[key], type(DEFAULT_CONFIGS[key])):
                raise ValueError(f"Invalid value datatype for {key}")
    except (json.JSONDecodeError, ValueError) as e:
        logging.error(f"{e}, resetting configs.")
        configs = None

    if not configs:
        configs = DEFAULT_CONFIGS
        config_file.seek(0)
        config_file.truncate()
        config_file.write(json.dumps(DEFAULT_CONFIGS))


class Config:
    """Config command:

    Manage your configurations.
    To show current configs just type 'config'.

    get: configs get [thing] [true/false]
      Whether or not to get something.
      This method takes in the thing to
      change and its state. This will
      probably be changed in the future.
    """
    def help(self, args): return self.__doc__
    
    def default(self):
        for key in configs:
            key_value = color(configs[key], "green" if configs[key] else "red", True)
            print(f"{key}: {key_value.lower()}")

    def get(self, args):
        if not args: raise ValueError("Get what ?")
        if len(args) < 2: raise ValueError("True or False ?")

        if args[0] not in configs:
            raise ValueError(f"Configuration {args[0]} does not exist")

        args[1] = args[1].lower()
        if args[1] == "true":
            configs[args[0]] = True
        elif args[1] == "false":
            configs[args[0]] = False
        else: raise ValueError("True or false ?")

        with open("configs.json", "w") as config_file:
            config_file.write(json.dumps(configs))

        print(f"Get {args[0]} set to <False>")
