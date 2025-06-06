#!/usr/bin/python3
import re
import argparse
from ssh import open_interactive_ssh
from pathlib import Path
import getpass

# Path to store imported sessions
home_directory = Path.home()
mxtsessions_directory_path = Path(home_directory / ".mxtsessions")
mxtsessions_file_path = mxtsessions_directory_path / "imported_mxtsessions"


def args_parser():
    # ArgParse
    parser = argparse.ArgumentParser(description="Perform actions on objects")

    # Create subparsers for different actions
    subparsers = parser.add_subparsers(dest='action', help='Actions for objects', required=True)

    # Subparser for the 'import' action
    import_parser = subparsers.add_parser('import', help='Import a new object')
    import_parser.add_argument('object_type',
                               choices=['session_stack'],  # Defining allowed choices for object_type
                               help='Type of the object to import')
    import_parser.add_argument('object_path', help='Path to the file containing shared sessions')
    import_parser.add_argument('object_name', help='Name you want to give to the shared sessions')

    # Subparser for the 'delete' action
    delete_parser = subparsers.add_parser('delete', help='Delete an object on the session_stack')
    delete_parser.add_argument('object_type', 
                               choices=['session_stack'],  # Defining allowed choices for object_type
                               help='Type of the object to delete')
    delete_parser.add_argument('object_name', 
                               help='Name of the object to delete')

    # Subparser for the 'create' action
    create_parser = subparsers.add_parser('create', help='Create an object on the session_stack')
    create_subparsers = create_parser.add_subparsers(dest='object_type', help='Type of object to create',
                                                     required=True)

    # Subparser for 'create directory'
    create_dir_parser = create_subparsers.add_parser('directory', help='Create a new directory')
    create_dir_parser.add_argument('object_name', help='Name of the directory to create')
    create_dir_parser.add_argument('-p', '--parents', action='store_true',
                                   help='Make parent directories as needed')

    # Subparser for 'create session'
    create_session_parser = create_subparsers.add_parser('session', help='Create a new session')
    create_session_parser.add_argument('object_name', help='Name of the session to create')
    create_session_parser.add_argument('--host', required=True, help='Host of the session')
    create_session_parser.add_argument('--port', type=int, required=True, help='Port of the session')
    create_session_parser.add_argument('--user', required=True, help='User for the session')
    create_session_parser.add_argument('--protocol', required=True, help='Protocol of the session',
                                       choices=['ssh','rdp'])
    create_session_parser.add_argument('-p', '--parents', action='store_true',
                                       help='Make parent directories as needed')
    group = create_session_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--password', help='Password for the session')
    group.add_argument('--pem-path', help='Path to the PEM file for the session')

    # Subparser for the 'search' action
    search_parser = subparsers.add_parser('search', help='Search an object')
    search_parser.add_argument('-t', '--object_type', 
                               choices=['session', 'directory', 'any'],  # Defining allowed choices for object_type
                               default='any',
                               help='Type of the object to search. Default: any')
    search_parser.add_argument('object_name', 
                               help='Name of the object to search.')

    # Subparser for the 'connect' action
    connect_parser = subparsers.add_parser('connect', help='Connect to an object')
    connect_parser.add_argument('object_name',
                                help='Name of the session to establish connection')

    # Subparser for the 'connect' action
    list_parser = subparsers.add_parser('list', help='List sessions | directories')
    list_parser.add_argument('object_name',
                             help='Name of the directory to list',
                             nargs='?',
                             default=None)

    # Parse arguments
    args = parser.parse_args()
    return args


def ensure_mxtsessions_path():
    if not mxtsessions_directory_path.exists():
        mxtsessions_directory_path.mkdir(parents=True)
    if not mxtsessions_file_path.exists():
        mxtsessions_file_path.touch()


def import_object(mxtsessions_file_path, object_type, object_path, object_name):
    if object_type == 'session_stack':
        with open(mxtsessions_file_path, 'r+') as file:
            content = file.read()
        if not f'\\{object_name}\n' in content:
            if not f'{object_path}' in content:
                file.write(f'{object_path}\\{object_name}\n')
            else:
                print(f"[!] Error: Since there is already a session_stack aiming to "
                      f"\"{object_path}\", it won't be imported a new one. ")
                exit(1)
        else:
            print(f"[!] Error: Since there is already a session_stack called "
                  f"\"{object_name}\", it won't be imported a new one. ")
            exit(1)


def delete_object(mxtsessions_file_path, object_type, object_name):
    if object_type == "session_stack":
        with open(mxtsessions_file_path, 'r') as file:
            content = file.readlines()
        filtered_content = [line for line in content if f"\\{object_name}\n" not in line]
        with open(mxtsessions_file_path, 'w') as file:
            file.writelines(filtered_content)


def imported_mxtsessions_reader(mxtsessions_file_path):
    imported_mxtsessions_dict = {}
    line_existence = False
    with open(mxtsessions_file_path, 'r') as file:
        for line in file:
            line_splitted = line.strip().split('\\')
            imported_mxtsessions_dict[line_splitted[1]] = line_splitted[0]
            line_existence = True
    if not line_existence:
        print("[!] Error: There is no session_stack yet. Please import one before retrying this action")
        exit(1)
    else:
        return imported_mxtsessions_dict


def search_objects(mxtsessions_file_path, object_type, object_name):
    imported_mxtsessions_dict = imported_mxtsessions_reader(mxtsessions_file_path)
    for imported_mxtsession_name, imported_mxtsession_path in imported_mxtsessions_dict.items():
        with open(imported_mxtsession_path, 'r', encoding='ISO-8859-1') as file:
            content = file.readlines()
        for line in content:
            directory_match = re.match(r'^SubRep=(.*)', line)
            if not directory_match:
                if object_type == "session" or object_type == "any":
                    if object_name.lower() in line.lower():
                        line_psv = line.strip().split('%')
                        session_name_protocol = line_psv[0].strip().split('=')
                        session_name = session_name_protocol[0]
                        session_protocol = session_name_protocol[1]
                        session_protocol_str = ("[+] SSH" if '#109#0' == session_protocol
                            else ('[+] RDP' if '#91#4' == session_protocol else '[!] Not Known'))
                        print(f'/{imported_mxtsession_name}/{directory}/{session_name}  {session_protocol_str}')
            else:
                directory = directory_match.group(1)
                directory = directory.replace('\\','/')
                if object_type == "directory" or object_type == "any":
                    if object_name.lower() in directory.lower():
                        print(f'/{imported_mxtsession_name}/{directory}/')


def connect_to_object(mxtsessions_file_path, session_name):
    session_name_directory = "\\".join(session_name.split('/')[2:-1])
    session_array = session_name.split('/')
    session_name = session_array[-1]
    session_stack_name = session_array[1]
    imported_mxtsessions_dict = imported_mxtsessions_reader(mxtsessions_file_path)
    imported_mxtsession_path = imported_mxtsessions_dict[session_stack_name]
    session_name_directory_hit = False
    session_string_hit = False
    with open(imported_mxtsession_path, 'r', encoding='ISO-8859-1') as file:
        content = file.readlines()
    session_name = session_name.replace("\\", "\\\\")
    session_name = session_name.replace("(", "\(")
    session_name = session_name.replace(")", "\)")
    for line in content:
        if session_name_directory in line:
            session_name_directory_hit = True
        if session_name_directory_hit:
            session_match_string = f"^{session_name}(.*)=(.*)#(.*)"
            session_match = re.match(r"{}".format(session_match_string), line)
            if session_match:
                session_string = line
                session_string_hit = True

    if session_string_hit:
        session_array = session_string.strip().split('%')
        session_protocol = ("ssh" if '#109#0' in session_array[0].strip().split('=')[1]
                            else ('rdp' if '#91#4' in session_array[0].strip().split('=')[1] else None))
        session_host = session_array[1]
        session_port = session_array[2]
        session_user = session_array[3]
        session_pem = session_array[14].strip().split('\\')[-1]
        if session_protocol == "ssh":
            if session_pem != "":
                session_pem = f"~/.ssh/{session_pem}"
                open_interactive_ssh(host=session_host, port=session_port, user=session_user, key_path=session_pem)
            else:
                password = getpass.getpass(prompt=f"{session_user}@{session_host}'s password: ")
                open_interactive_ssh(host=session_host, port=session_port, user=session_user, password=password)
                
        elif session_protocol == "rdp":
            pass
        else:
            print('[!] Error: The found session is not compatible with remote control [SSH | RDP]')
            exit(1)
    else:
        print("[!] Error: The session you tried to connect to was not found")
        exit(1)


def list_objects(mxtsessions_file_path, object_name):
    imported_mxtsessions_dict = imported_mxtsessions_reader(mxtsessions_file_path)
    if object_name is None:
        for imported_mxtsession_name, imported_mxtsession_path in imported_mxtsessions_dict.items():
            with open(imported_mxtsession_path, 'r', encoding='ISO-8859-1') as file:
                content = file.readlines()
            directory_before = None
            for line in content:
                directory_match = re.match(r'^SubRep=(.*)', line)
                if not directory_match:
                    if '=#' in line or '= #' in line:
                        line_psv = line.strip().split('%')
                        session_name = line_psv[0].strip().split('=')[0]
                        session_protocol = ("[+] SSH" if '#109#0' in line_psv[0].strip().split('=')[1]
                                            else ('[+] RDP' if '#91#4' in line_psv[0].strip().split('=')[1] else '[!] Not Known'))
                        print(f"{blank_string}  - {session_name}  {session_protocol}")
                else:
                    blank_string = ""
                    directory = directory_match.group(1)
                    directory = directory.strip().split('\\')
                    for i in directory:
                        blank_string += "  "
                    if directory[0] == "":
                        print(f"[{imported_mxtsession_name}]")
                    elif not directory[-1] in directory_before:
                        print(f"{blank_string}[{directory[-1]}]")
                    directory_before = directory[:-1]
    else:
        session_name_directory = "\\".join(object_name.split('/')[2:-1])
        session_array = object_name.split('/')
        session_stack_name = session_array[1]
        imported_mxtsessions_dict = imported_mxtsessions_reader(mxtsessions_file_path)
        imported_mxtsession_path = imported_mxtsessions_dict[session_stack_name]
        with open(imported_mxtsession_path, 'r', encoding='ISO-8859-1') as file:
            content = file.readlines()
        directory_before = ""
        print(f"[{session_stack_name}]")
        directory_match_hit = False
        for line in content:
            directory_match = re.match(r'^SubRep=(.*)', line)
            session_name_directory = session_name_directory.replace('\\', "\\\\")
            directory_name_match_string = f'^SubRep={session_name_directory}(.*)'
            directory_name_match = re.match(r'{}'.format(directory_name_match_string), line)
            if directory_match and not directory_name_match:
                directory_match_hit = False
            elif directory_name_match:
                directory_match_hit = True
                blank_string = ""
                directory = f"{session_name_directory}{directory_name_match.group(1)}"
                directory = directory.strip().split('\\')
                for _ in directory:
                    blank_string += "  "

                if not directory[-1] in directory_before:
                    print(f"{blank_string}[{directory[-1]}]")
                directory_before = directory[:-1]
            elif ('=#' in line or '= #' in line) and directory_match_hit:
                line_psv = line.strip().split('%')
                session_name = line_psv[0].strip().split('=')[0]
                print(f"{blank_string}  - {session_name}")


def create_directory_object(mxtsessions_file_path, object_name, parents):
    if object_name[-1] != "/":
        print("[!] Error: The directory name must end with character '/' to be recognized as a directory")
        exit(1)
    try:
        object_name_directory = "\\\\".join(object_name.split('/')[2:-1])
        object_array = object_name.split('/')
        object_stack_name = object_array[1]
        imported_mxtsessions_dict = imported_mxtsessions_reader(mxtsessions_file_path)
        imported_mxtsession_path = imported_mxtsessions_dict[object_stack_name]
        with open(imported_mxtsession_path, 'r', encoding='ISO-8859-1') as file:
            content = file.readlines()
        for line in content:
            directory_match = re.match(r'^SubRep={}'.format(object_name_directory), line)
            if not directory_match:
                pass
    except KeyError:
        print("[!] Error: The name of the session you are tring to modify have not been imported")
        exit(1)


def create_session_object(mxtsessions_file_path, object_name, host, port, user, password, pem_path, protocol, parents):
    pass


def main():
    args = args_parser()
    ensure_mxtsessions_path()
    if args.action == 'import':
        import_object(mxtsessions_file_path, args.object_type, args.object_path, args.object_name)
    elif args.action == 'delete':
        delete_object(mxtsessions_file_path, args.object_type, args.object_name)
    elif args.action == 'search':
        search_objects(mxtsessions_file_path, args.object_type, args.object_name)
    elif args.action == 'connect':
        connect_to_object(mxtsessions_file_path, args.object_name)
    elif args.action == 'list':
        list_objects(mxtsessions_file_path, args.object_name)
    elif args.action == 'create':
        if args.object_type == "directory":
            create_directory_object(mxtsessions_file_path, args.object_name, args.parents)
        elif args.object_type == "session":
            create_session_object(mxtsessions_file_path, args.object_name, args.host,
                        args.port, args.user, args.password, args.pem_path, args.protocol, args.parents)


if __name__ == "__main__":
    main()
