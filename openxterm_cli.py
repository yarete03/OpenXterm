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
    create_parser = subparsers.add_parser('import', help='Import a new object')
    create_parser.add_argument('object_type', 
                               choices=['session'],  # Defining allowed choices for object_type
                               help='Type of the object to import')
    create_parser.add_argument('object_name', help='Path to the file containing shared sessions')

    # Subparser for the 'delete' action
    delete_parser = subparsers.add_parser('delete', help='Delete an object')
    delete_parser.add_argument('object_type', 
                               choices=['session'],  # Defining allowed choices for object_type
                               help='Type of the object to delete')
    delete_parser.add_argument('object_name', 
                               help='Name of the object to delete')

    # Subparser for the 'search' action
    search_parser = subparsers.add_parser('search', help='Search an object')
    search_parser.add_argument('object_type', 
                               choices=['session', 'directory', 'any'],  # Defining allowed choices for object_type
                               default='any',
                               help='Type of the object to search. Default: any')
    search_parser.add_argument('object_name', 
                               help='Name of the object to search.')

    # Subparser for the 'connect' action
    connect_parser = subparsers.add_parser('connect', help='Connect to an object')
    connect_parser.add_argument('object_name', 
                               help='Name of the session to establish connection')


    # Parse arguments
    args = parser.parse_args()
    return args


def ensure_mxtsessions_path():
    if not mxtsessions_directory_path.exists():
        mxtsessions_directory_path.mkdir(parents=True)
    if not mxtsessions_file_path.exists():
        mxtsessions_file_path.touch()


def import_object(mxtsessions_file_path, object_type, object_name):
    if object_type == 'session':
        session_path = object_name
        with open(mxtsessions_file_path, 'r+') as file:
            content = file.read()
            if not session_path + '\n' in content:
                file.write(session_path + '\n')


def delete_object(mxtsessions_file_path, object_type, object_name):
    if object_type == "session":
        with open(mxtsessions_file_path, 'r+') as file:
            content = file.read()
            if object_name + '\n' in content:
                content = content.replace(object_name + '\n', "")
                file.seek(0)
                file.write(content)
                file.truncate()


def imported_mxtsessions_reader(mxtsessions_file_path):
    with open(mxtsessions_file_path, 'r') as file:
        imported_mxtsessions_array = file.readlines()
    return imported_mxtsessions_array


def search_objects(mxtsessions_file_path, object_type, object_name):
    imported_mxtsessions_array = imported_mxtsessions_reader(mxtsessions_file_path)
    for imported_mxtsession in imported_mxtsessions_array:
        with open(imported_mxtsession[:-1], 'r', encoding='ISO-8859-1') as file:
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
                            print(f'{directory}/{session_name}')
                else:
                    directory = directory_match.group(1)
                    directory = directory.replace('\\','/')
                    if object_type == "directory" or object_type == "any":
                        if object_name.lower() in directory.lower():
                            print(f'{directory}/')


def connect_to_object(mxtsessions_file_path, session_name):
    session_name_directory = "\\".join(session_name.split('/')[:-1])
    session_name = session_name.split('/')[-1]
    imported_mxtsessions_array = imported_mxtsessions_reader(mxtsessions_file_path)
    for imported_mxtsession in imported_mxtsessions_array:
        session_name_directory_hit = False
        session_string_hit = False
        with open(imported_mxtsession[:-1], 'r', encoding='ISO-8859-1') as file:
            content = file.readlines()
            for line in content:
                if session_name_directory in line:
                    session_name_directory_hit = True
                if session_name_directory_hit:
                    session_match = re.match(r'^{}(.*)'.format(session_name), line)
                    if session_match:
                        session_string = line
                        session_string_hit = True
                        break
            if session_string_hit:
                break
    if session_string_hit:
        session_array = session_string.strip().split('%')
        session_protocol = ("ssh" if session_array[0].strip().split('=')[1] == '#109#0' else ('rdp' if session_array[0].strip().split('=')[1] == '#91#4' else None))
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
            print('The found session is not compatible with remote control [SSH | RDP]')
            exit(1)
    else:
        print("The session you tried to connect to was not found")
        exit(1)


def main():
    global args 
    args = args_parser()
    ensure_mxtsessions_path()
    if args.action == 'import':
        import_object(mxtsessions_file_path, args.object_type, args.object_name)
    elif args.action == 'delete':
        delete_object(mxtsessions_file_path, args.object_type, args.object_name)
    elif args.action == 'search':
        search_objects(mxtsessions_file_path, args.object_type, args.object_name)
    elif args.action == 'connect':
        connect_to_object(mxtsessions_file_path, args.object_name)


if __name__ == "__main__":
    main()
