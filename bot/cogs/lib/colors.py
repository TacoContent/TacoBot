from bot.cogs.lib import loglevel


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def colorize(color, text, bold=False, underline=False):
        if bold:
            text = f"{Colors.BOLD}{text}{Colors.ENDC}"
        if underline:
            text = f"{Colors.UNDERLINE}{text}{Colors.ENDC}"
        return f"{color}{text}{Colors.ENDC}"

    @staticmethod
    def get_color(level: loglevel.LogLevel):
        if level == loglevel.LogLevel.DEBUG:
            return Colors.OKBLUE
        elif level == loglevel.LogLevel.INFO:
            return Colors.OKGREEN
        elif level == loglevel.LogLevel.WARNING:
            return Colors.WARNING
        elif level == loglevel.LogLevel.ERROR:
            return Colors.FAIL
        elif level == loglevel.LogLevel.FATAL:
            return Colors.FAIL
        else:
            return Colors.ENDC
