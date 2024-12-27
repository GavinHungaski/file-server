#!/usr/bin/env python3

# Author: Gavin Hungaski


from library import *
import argparse
import socket
import shutil
import signal
import time
import os


class FileServer:
    def __init__(self, host, port, serve_dir):
        self.host = host
        self.port = port
        self.serve_dir = serve_dir
        self.current_dir = self.serve_dir
        self.active_clients = []

    def run(self):
        signal.signal(signal.SIGINT, self.__exit_signal_handler)
        changeDirectory(self.serve_dir)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(5)
            while True:
                try:
                    if len(self.active_clients) >= 4:
                        client, _ = s.accept()
                        client.send(b"Error: Server busy, please try again later.")
                        client.close()
                        continue
                    client, _ = s.accept()
                    pid = os.fork()
                    if pid == 0:
                        self.active_clients.append(client)
                        self.__handle_client(client)
                        self.active_clients.remove(client)
                        os._exit(0)
                    else:
                        client.close()
                        os.waitpid(pid, 0)
                except ConnectionRefusedError:
                    print(f"Error: Connection refused to {self.host}:{self.port}")
                except OSError as e:
                    print(e)

    def __exit_signal_handler(self, sig, frame):
        print("\nServer shutting down in 5 seconds . . .")
        if len(self.active_clients) > 0:
            for client in self.active_clients[:]:
                try:
                    client.sendall(b"Server shutting down in 5 seconds, closing connection now . . .~")
                except OSError:
                    pass
                finally:
                    client.close()
                    self.active_clients.remove(client)
        time.sleep(1)
        exit(0)

    def __handle_client(self, client):
        try:
            while True:
                msg_length = really_recv(client, 1024).decode()
                if msg_length != "":
                    content = really_recv(client, int(msg_length)).decode().split()
                    print(f"Length: {msg_length}\nContent: {content}\n")
                    actions = {
                        "cd": self.dir_change,
                        "ls": self.display_dir,
                        "pwd": self.display_path,
                        "mkdir": self.make_dir,
                        "rm": self.remove,
                        "get": self.get_file,
                        "put": self.put_file,
                    }
                    if content[0] in actions:
                        actions[content[0]](client, content)
                    elif content[0] == "exit":
                        client.sendall(f"Exiting~".encode())
                        break;
                    else:
                        client.sendall(b"Unknown content recieved, ignoring . . .~")
                        print("Unknown content recieved, ignoring . . .")
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            print("Closing client connection\n")
            client.close()    
    
    def __prep_path(self, client, content, key=False):
        if len(content) > 1:
            if content[1][0] == "/":
                content[1] = content[1].replace("/", "", 1)
            dir_path = content[1]
        else:
            dir_path = ""
        full_path = os.path.abspath(os.path.join(self.current_dir, dir_path))
        if not os.path.exists(full_path):
            if key:
                client.sendall("e~".encode())
            client.sendall(f"Error: The directory {dir_path} cannot be found~".encode())
            return "0"
        if not os.path.commonpath([full_path, self.serve_dir]) == self.serve_dir:
            if key:
                client.sendall("e~".encode())
            client.sendall(f"Error: Cannot affect directory above the serving directory~".encode())
            return "0"
        return full_path

    def display_dir(self, client, content):
        full_path = self.__prep_path(client, content)
        if full_path != "0":
            try:
                client.sendall(f"success~".encode())
                contents_list = listDirectory(full_path)
                bytes_list = [s.encode()+b'~' for s in contents_list]
                client.sendall(f"{len(bytes_list)}~".encode())
                for item in bytes_list:
                    client.sendall(item)
            except Exception as e:
                print(f"An error occurred: {e}")
                client.sendall(f"Error: Unable to display directory {full_path}~".encode())

    def dir_change(self, client, content):
        full_path = self.__prep_path(client, content)
        if full_path == "0":
            return
        elif full_path == self.current_dir:
            full_path = self.serve_dir
        try:
            changeDirectory(full_path)
            self.current_dir = full_path
            client.sendall(f"Changed server directory to {self.current_dir}~".encode())
        except Exception as e:
            print(f"An error occurred: {e}")
            client.sendall(f"Error: Unable to change directory to {full_path}~".encode())

    def display_path(self, client, content):
        client.sendall(f"{self.current_dir}~".encode())

    def make_dir(self, client, content):
        if len(content) > 1:
            if content[1][0] == "/":
                content[1] = content[1].replace("/", "", 1)
            dir_path = content[1]
        else:
            dir_path = ""
        full_path = os.path.abspath(os.path.join(self.current_dir, dir_path))
        if not os.path.commonpath([full_path, self.serve_dir]) == self.serve_dir:
            client.sendall(f"Error: Cannot affect directory above the serving directory~".encode())
            return
        try:
            makeDirectory(full_path)
            client.sendall(f"Created directory here: {full_path}~".encode())
        except Exception as e:
            print(f"An error occurred: {e}")
            client.sendall(f"Error: Unable to create directory {full_path}~".encode())
            
    def remove(self, client, content):
        try:
            recursive = is_recursive(content)
            if len(content) < 2:
                client.sendall("Error: No file name provided~".encode())
                return
            full_path = self.__prep_path(client, content)
            if os.path.isdir(full_path) and recursive:
                shutil.rmtree(full_path)
                client.sendall(f"Deleted everything at {full_path}~".encode())
            elif os.path.isdir(full_path):
                if len(list(os.scandir(full_path))) == 0:
                    os.rmdir(full_path)
                    client.sendall(f"Deleted the directory {full_path}~".encode())
                else:
                    client.sendall(f"Error: {full_path} has contents.~".encode())
                    return
            else:
                os.remove(full_path)
                client.sendall(f"~".encode())
        except Exception as e:
            client.sendall(f"Error: {e}~".encode())

    def get_file(self, client, content):
        recursive = is_recursive(content)
        if len(content) < 2:
            client.sendall("e~".encode())
            client.sendall("Error: No file name provided~".encode())
            return
        full_path = self.__prep_path(client, content, True)
        if full_path != '0':
            if os.path.isdir(full_path) and recursive:
                client.sendall("d~".encode())
                dir_name = os.path.basename(full_path)
                self.__send_directory(client, full_path)
                client.sendall(f"You successfully fetched {dir_name}~".encode())
            elif os.path.isdir(full_path):
                client.sendall("d~".encode())
                dir_name = os.path.basename(full_path)
                client.sendall(f"{dir_name}~".encode())
                client.sendall("0~".encode())
                client.sendall(f"Successfully fetched {dir_name}~".encode())
            else:
                client.sendall("f~".encode())
                self.__send_file(client, full_path)
                client.sendall(f"Successfully fetched {full_path}~".encode())

    def __send_file(self, client, file_path):
        try:
            client.sendall(f"{file_path}~".encode())
            file_size = os.path.getsize(file_path)
            client.sendall(f"{file_size}~".encode())
            with open(file_path, "rb") as file:         
                client.sendfile(file)
        except Exception as e:
            print(f"Error: {e}")
            client.sendall(f"Error: Unable to send file {file_path}~".encode())

    def __send_directory(self, client, dir_path):
        try:
            client.sendall(f"{dir_path}~".encode())
            contents_list = listDirectory(dir_path)
            client.sendall(f"{len(contents_list)}~".encode())
            for item in contents_list:
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    client.sendall("f~".encode())
                    self.__send_file(client, item_path)
                elif os.path.isdir(item_path):
                    client.sendall("d~".encode())
                    self.__send_directory(client, item_path)
        except Exception as e:
            print(f"An error occurred: {e}")
            client.sendall(f"Error: Unable to send directory {dir_path}~".encode())

    def put_file(self, client, content):
        i = min(len(content) - 1, 2)
        if content[i][0] == "/":
            content[i] = content[i].replace("/", "", 1)
        dir_path = content[i]
        full_path = os.path.abspath(os.path.join(self.current_dir, dir_path))
        if not os.path.commonpath([full_path, self.serve_dir]) == self.serve_dir:
            client.sendall(f"Error: Cannot affect directory above the serving directory~".encode())
            return
        key = really_recv(client, 4096).decode()
        if not key:
            key = really_recv(client, 4096).decode()
        if key == 'd':
            try:
                self.receive_dir(client, self.current_dir)
            finally:
                client.sendall(f"You placed {full_path} dir.~".encode())
        elif key == 'f':
            try:
                self.receive_file(client, self.current_dir)
            finally:
                client.sendall(f"You placed {full_path} file~".encode())
    
    def receive_file_metadata(self, client):
        file_path = really_recv(client, 4096).decode()
        file_size = really_recv(client, 4096).decode()
        if not file_size:
            file_size = really_recv(client, 4096).decode()
        return file_path, file_size

    def receive_file_data(self, client, file_size):
        received_data = bytearray()
        while len(received_data) < int(file_size):
            chunk = client.recv(4096)
            received_data.extend(chunk)
        return received_data

    def write_file_to_disk(self, file_path, file_data):
        try:
            with open(file_path, "wb") as file:
                file.write(file_data)
        except Exception as e:
            print(f"Error writing file: {e}")

    def receive_file(self, client, path):
        file_path, file_size = self.receive_file_metadata(client)
        file_name = os.path.basename(file_path)
        file_path = os.path.join(path, file_name)        
        try:
            file_data = self.receive_file_data(client, file_size)
            self.write_file_to_disk(file_path, file_data)
        except Exception as e:
            print(f"Error receiving file: {e}")
        
    def receive_dir(self, client, path):
        dir_path = really_recv(client, 4096).decode()
        dir_name = os.path.basename(dir_path)
        dir_path = os.path.join(path, dir_name)
        print(f"Making directory: {dir_path}")
        os.mkdir(dir_path, 0o766)
        num_items = int(really_recv(client, 4096).decode())
        for _ in range(num_items):
            key = really_recv(client, 4096).decode()
            if key == 'f':
                self.receive_file(client, dir_path)
            elif key == 'd':
                self.receive_dir(client, dir_path)


def parse_args():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('-p', help='Port #', required=True)
    parser.add_argument('-d', help='Directory to serve from', required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    host = ""
    port = int(args.p)
    serve_dir = os.path.abspath(args.d)
    
    server = FileServer(host, port, serve_dir)
    server.run()


if __name__ == "__main__":
    main()
