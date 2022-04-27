import json
import os
import sys

# a hack to replace an emoji with a \n because python doesn't allow \n in an f-string
# you will see `.replace(f'{new_line_emoji}', '\n')` in the code

new_line_emoji = '🍔'
def main():
    settings = _load_settings()
    commands = settings.get('commands', {})
    bot_name = settings.get('bot_name', 'OurTacoBot')
    print(f"# {bot_name.upper()} TWITCH COMMANDS")
    print(f"")
    # icon = settings.get('icon', None)
    # if icon is not None:
    #     print(f"![]({icon})")
    prefixes = settings.get("prefixes", [])
    if len(prefixes) > 0:
        print(f"")
        print(f"### COMMAND PREFIXES")
        print(f"The following prefixes are accepted:  \n")
        print(f"{''.join([f'- `{p}`  {new_line_emoji}' for p in prefixes])}".replace(f'{new_line_emoji}', '\n'))
    print(f"")
    print(f"`!taco <command> [subcommand] [arg1...argN]`")
    print(f"")
    print(f"# COMMAND LIST")
    print(f"")
    for command in commands:
        _process_command_list(commands, command)

    for command in commands:
        print(f"---")
        print(f"")
        _process_command(commands, command)

def _process_command_list(commands, command, parent_command=""):
    c_admin = commands[command].get('admin', False)
    c_name = _get_formatted_key(command)
    shield = '🛡️' if c_admin > 0 else ''

    padding = "" if len(parent_command) == 0 else "  "
    full_name = ' '.join([parent_command, c_name]).strip()
    link_name = full_name.replace(' ', '-')
    print(f'{padding}- [{full_name.upper()}{shield}](#{link_name})  ')
    print(f"")
    c_subcommands = commands[command].get('subcommands', {})
    for sc in c_subcommands:
        _process_command_list(c_subcommands, sc, full_name)

def _process_command(commands, command, parent_command=""):
    c_admin = commands[command].get('admin', False)
    shield = '🛡️' if c_admin > 0 else ''
    c_name = _get_formatted_key(command)
    full_name = ' '.join([parent_command, c_name]).strip()

    print(f'## {full_name.upper()}{shield}')
    c_desc = _replace_prefix(commands[command].get('description', ''))
    print(c_desc)
    print(f"")
    c_usage = _replace_prefix(commands[command].get('usage', ''))
    print(f'### USAGE')
    print(f"")
    print(f'```{c_usage}```')
    print(f"")
    c_aliases = commands[command].get('aliases', [])
    if c_aliases and len(c_aliases) > 0:
        print(f'### ALIASES')
        print(f"")
        print(f'{"".join([f"- `{a}`  {new_line_emoji}" for a in c_aliases])}'.replace(f'{new_line_emoji}', '\n'))
        print(f"")

    c_examples = [ _replace_prefix(example) for example in commands[command].get('example', []) ]
    print(f'### EXAMPLES')
    print(f'{"".join([f"- `{e}`  {new_line_emoji}" for e in c_examples])}\n'.replace(f'{new_line_emoji}', '\n'))
    c_arguments = commands[command].get('arguments', [])
    if c_arguments and len(c_arguments) > 0:
        print(f"### ARGUMENTS")
        print(f"")
        _process_arguments(c_arguments)
        print(f"")

    c_subcommands = commands[command].get('subcommands', {})
    for sc in c_subcommands:
        print(f"---")
        _process_command(c_subcommands, sc, full_name)


def _process_arguments(arguments):
    print(f"| NAME | DESCRIPTION | TYPE | DEFAULT/MIN/MAX | REQUIRED |  ")
    print(f"|---|---|---|---|---|  ")
    for argument in arguments:
        a_name = argument
        a_type = arguments[argument].get('type', 'string')
        a_required = arguments[argument].get('required', False)
        a_description = _replace_prefix(arguments[argument].get('description', ''))
        a_default = arguments[argument].get('default', None)
        a_min = arguments[argument].get('min', None)
        a_max = arguments[argument].get('max', None)
        if a_default is not None:
            a_default = str(a_default)
        if a_min is not None:
            a_min = str(a_min)
        if a_max is not None:
            a_max = str(a_max)
        if a_required:
            a_required = 'YES'
        else:
            a_required = 'NO'
        if a_type == 'number':
            print(f"| `{a_name}` | {a_description} | `{a_type}` | DEFAULT: `{a_default}`  MIN: `{a_min}`  MAX: `{a_max}` | `{a_required}` |  ")
        else:
            print(f"| `{a_name}` | {a_description} | `{a_type}` | DEFAULT: `{a_default}` | `{a_required}` |  ")

def _get_formatted_key(key):
    return key.replace('_', '')
def _replace_prefix(s):
    return s.replace('{{prefix}}', '!taco ')

def _load_settings():
    settings = {}
    try:
        with open("app.manifest", encoding="UTF-8") as json_file:
            settings.update(json.load(json_file))
    except Exception as e:
        print(e, file=sys.stderr)
    return settings

if __name__ == "__main__":
    main()
