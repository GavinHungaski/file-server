#!/usr/bin/env python3

# Author: Gavin Hungaski

from library import *
import argparse
import socket
import os


class FileClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.home_dir = os.getcwd()

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.host, self.port))
            while True:
                message = input("~ ")
                if not message:
                    continue
                command, *_ = message.split(maxsplit=1)
                if command == "exit":
                    response = self.handle_exit(s)
                elif self.is_command(command):
                    if command in ['mkdir', 'cd', 'pwd']:
                        command = "basic"
                    response = getattr(self, f"handle_{command}")(s, message)
                else:
                    response = f"Unknown command: \'{message}\'"
                if response:
                    print(response)
                if response == "Exiting":
                    break
        except KeyboardInterrupt:
            print("\nExiting...")
            try:
                _ = self.handle_exit(s)
            except OSError as e:
                print(e)
        except ConnectionRefusedError:
            print(f"ERROR: Connection refused to {self.host}:{self.port}")
        except OSError as e:
            print(e)
        finally:
            s.close()
    
    def is_command(self, command):
        good_commands = ['cd', 'lcd', 'ls', 'lls', 'pwd', 'lpwd', 'mkdir', 
                         'lmkdir', 'get', 'put', 'rm']
        if command in good_commands:
            return True
        else:
            return False

    def handle_exit(self, s):
        message = "exit"
        s.sendall(f"{len(message)}~".encode())
        s.sendall(f"{message}~".encode())
        return really_recv(s, 1024).decode()

    def handle_ls(self, s, message):
        response = self.handle_basic(s, message)
        if response == 'success':
            num_of_items = int(really_recv(s, 1024).decode())
            response = []
            for _ in range(num_of_items):
                item = really_recv(s, 1024).decode()
                if '.' in item:
                    prGreen(item)
                else:
                    prCyan(f"{item}\\")
        else:
            return response
        return ""

    def handle_lls(self, s, message):
        contents = message.split()
        if len(contents) > 1:
            path = os.path.abspath(contents[1])
        else:
            path = ""
        items = listDirectory(path)
        for item in items:
            if '.' in item:
                    prGreen(item)
            else:
                prCyan(f"{item}\\")

    def handle_lpwd(self, s, message):
        print(os.getcwd())
        
    def handle_lcd(self, s, message):
        contents = message.split()
        if len(contents) > 1:
            path = os.path.abspath(contents[1])
            os.chdir(path)
        else:
            os.chdir(self.home_dir)
        print(f"Changed to: {os.getcwd()}")
        
    def handle_lmkdir(self, s, message):
        contents = message.split()
        if len(contents) > 1:
            path = os.path.abspath(contents[1])
            if (path != ""):
                os.mkdir(path, 0o766)
            print(f"Created directory: {path}")
        else:
            print("Error: No directory name provided.")
            
    def handle_rm(self, s, message):
        s.sendall(f"{len(message)}~".encode())
        s.sendall(f"{message}~".encode())
        return really_recv(s, 1024).decode()

    def handle_basic(self, s, message):
        s.sendall(f"{len(message)}~".encode())
        s.sendall(f"{message}~".encode())
        return really_recv(s, 1024).decode()

    def handle_get(self, s, message):
        s.sendall(f"{len(message)}~".encode())
        s.sendall(f"{message}~".encode())
        key = really_recv(s, 4096).decode()         # receive the key
        print(key)
        if key == 'f':                              # receive a single file
            self.receive_file(s)
            return really_recv(s, 4096).decode()
        if key == 'd':                              # receive a directory
            self.receive_dir(s)
            return really_recv(s, 4096).decode()
        elif key == 'e':                            # receive an error
            return really_recv(s, 4096).decode()

    def receive_dir(self, s, base_dir="./"):
        dir_path = really_recv(s, 4096).decode()  # receive directory path
        dir_name = os.path.basename(dir_path)
        dir_path = os.path.join(base_dir, dir_name)
        os.mkdir(dir_path)                        # create the directory
        num_items = int(really_recv(s, 4096).decode())   # receive the number of items in the directory
        for _ in range(num_items):
            key = really_recv(s, 4096).decode()   # receive the key (file or directory)
            if key == 'f':                        # receive a file
                self.receive_file(s, dir_path)
            elif key == 'd':
                self.receive_dir(s, dir_path)

    def receive_file(self, s, base_dir="./"):
        file_path = really_recv(s, 4096).decode()   # receive file path
        file_name = os.path.basename(file_path)
        file_size = really_recv(s, 4096).decode()   # receive file size
        received_data = bytearray()
        while len(received_data) < int(file_size):
            chunk = s.recv(4096)
            received_data.extend(chunk)
        file_path = os.path.join(base_dir, file_name)
        with open(file_path, "wb") as file:
            file.write(received_data)

    def handle_put(self, s, message):
        s.sendall(f"{len(message)}~".encode())
        s.sendall(f"{message}~".encode())
        message = message.split()
        recursive = is_recursive(message)
        path = os.path.abspath(message[1])
        if os.path.isdir(path) and recursive:
            s.sendall("d~".encode())
            self.send_directory(s, path)
            return really_recv(s, 4096).decode()
        elif os.path.isdir(path):
            s.sendall("d~".encode())
            s.sendall(f"{path}~".encode())
            s.sendall("0~".encode())
            return really_recv(s, 4096).decode()
        else:
            s.sendall("f~".encode())
            self.send_file(s, path)
            return really_recv(s, 4096).decode()

    def send_file(self, s, file_path):
        try:
            s.sendall(f"{file_path}~".encode())
            file_size = os.path.getsize(file_path)
            s.sendall(f"{file_size}~".encode())
            with open(file_path, "rb") as file:         
                s.sendfile(file)
        except Exception as e:
            print(f"Error: {e}")

    def send_directory(self, s, dir_path):
            try:
                s.sendall(f"{dir_path}~".encode())
                contents_list = listDirectory(dir_path)
                s.sendall(f"{len(contents_list)}~".encode()) 
                for item in contents_list:
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        s.sendall("f~".encode())
                        self.send_file(s, item_path)
                    elif os.path.isdir(item_path):
                        s.sendall("d~".encode())
                        self.send_directory(s, item_path)
            except Exception as e:
                print(f"Error: {e}")


def parse():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', help='Host', required=True)
    parser.add_argument('-p', type=int, help='Port', required=True)
    args = parser.parse_args()
    return args


def main():
    args = parse()
    
    client = FileClient(args.h, int(args.p))
    client.connect()


if __name__ == "__main__":
    main()
