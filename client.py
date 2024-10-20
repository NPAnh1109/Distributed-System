import os
import json
import socket
import math
import random
import time
import threading
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import re, sys

kilobytes = 1024
chunksize = kilobytes * 100
readsize = kilobytes
BYTES = 102400

LOCAL_PORT = 35255
SERVER_PORT = 18520
# FILE_PORT = 228223

id_download = {}
id_upload = {}


class Chunk:
    chunks_dict = {}

    # init function
    def __init__(self, name, total):
        self.name = name
        self.total = total
        self.number_of_chunk = 0
        self.chunks_dict = {}

    def add_chunk(self, order, data):
        if order not in self.chunks_dict:
            self.number_of_chunk += 1
        self.chunks_dict[order] = data

    def find_chunk(self, order):
        return self.chunks_dict[order]

    def delect_chunk(self, order):
        if order in self.chunks_dict:
            self.number_of_chunk -= 1
            self.chunks_dict.pop(order)

    def print_chunks(self):
        for i in self.chunks_dict.keys():
            print(self.chunks_dict[i])
            print(f"key {i}: {self.chunks_dict[i]}")

    def isComplete(self):
        return self.total == self.number_of_chunk

    def split_chunks(self, id, fromfile, todir):
        if not os.path.exists(todir):  # caller handles errors
            os.mkdir(todir)  # make dir, read/write parts
        else:
            for fname in os.listdir(todir):  # delete any existing files
                os.remove(os.path.join(todir, fname))
        partnum = 0
        input = open(fromfile, 'rb')  # use binary mode on Windows
        while 1:  # eof=empty string from read
            chunk = input.read(chunksize)  # get next part <= chunksize
            if not chunk: break
            partnum = partnum + 1
            filename = os.path.join(todir, (f'{id}_{partnum}.txt'))
            fileobj = open(filename, 'wb')
            fileobj.write(chunk)
            self.add_chunk(partnum, filename)
            fileobj.close()  # or simply open(  ).write(  )
        input.close()
        return partnum

    def merge_chunks(self, tofile):
        path = f"{tofile}\{self.name}"
        output = open(path, 'wb')
        for order in range(self.total):
            filepath = self.chunks_dict[order + 1]
            with open(filepath, 'rb') as fileobj:
                # fileobj.readline()
                while 1:
                    filebytes = fileobj.read(readsize)
                    if not filebytes: break
                    output.write(filebytes)
                fileobj.close()
        output.close()


class Client_dict:
    dict = {}

    def __init__(self):
        self.dict = {}

    def add_file(self, file_id, file_name, total):
        if file_id not in self.dict:
            self.dict[file_id] = Chunk(file_name, total)
        else:
            if self.dict[file_id].name == "undefined":
                self.dict[file_id].name = file_name
                self.dict[file_id].total = total

    def delete_file(self, file_id):
        self.dict.pop(file_id)

    def add_chunk(self, file_id, path, order):
        if file_id not in self.dict:
            self.add_file(file_id, "undefined", 9999)
        self.dict[file_id].add_chunk(order, path)
        return 0

    def add_undefine_chunk(self, path):
        with open(path, 'rb') as fileobj:
            first_line = fileobj.readline()
            id, order = first_line.split()
            self.add_chunk(int(id), path, int(order))

    def delete_chunk(self, file_id, order):
        if file_id in self.dict:
            self.dict[file_id].delect_chunk(order)

    def print_dict(self):
        for i in self.dict.keys():
            print(f"file id:{i}, file name: {self.dict[i].name}, total: {self.dict[i].total}")
            print(f"number of current chunks: {self.dict[i].number_of_chunk}")
            for j in self.dict[i].chunks_dict.keys():
                print(f"-----order {j}: {self.dict[i].chunks_dict[j]}")

    def is_complete(self, file_id):
        return self.dict[file_id].isComplete()

    def missing_file(self, file_id):
        list_of_missing = []
        if (file_id not in self.dict):
            list_of_missing.append(0)
            return list_of_missing
        stop = self.dict[file_id].total
        for i in range(1, stop + 1):
            if i not in self.dict[file_id].chunks_dict:
                list_of_missing.append(i)
        return list_of_missing

    def scan_and_add_from_folder(self, dir):
        pattern = re.compile(r'^\d+_\d+\.txt$')
        all_files = os.listdir(dir)
        files = []
        for filename in all_files:
            if pattern.match(filename):
                id_part, order_part = filename.split('.')[0].split('_')
                id = int(id_part)
                order = int(order_part)
                path = f"{dir}\{filename}"
                self.add_chunk(id, path, order)

    def check_chunks(self, json_path):
        with open(json_path, 'r') as json_file:
            file_info = json.load(json_file)
            id = int(file_info.get("id"))
            if id in self.dict:
                for order in list(self.dict[id].chunks_dict):
                    sizeofchunk = int(file_info.get(f"{order}"))
                    path = self.dict[id].chunks_dict[order]
                    print(f"path{path}")
                    sizeoffile = os.path.getsize(path)
                    if (sizeofchunk != sizeoffile):
                        os.remove(path)
                        self.delete_chunk(id, order)

    def add_chunks_from_dir(self, dir, id):
        all_files = os.listdir(dir)
        print(all_files)
        chunk_files = [file for file in all_files if file.startswith(f'{id}_')]
        for filename in chunk_files:
            filepath = f"{dir}\{filename}"
            # with open(filepath, 'rb') as fileobj:
            #     content = fileobj.readline()
            #     values = content.split()
            match = re.search(rf"{id}_(\d+)\.txt", filename)
            if match:
                extracted_number = int(match.group(1))
                self.add_chunk(id, filepath, extracted_number)
            else:
                print("Fail")

    def create_JSON(self, id, dirpath, chunkspath):
        file_info = {}
        if id in self.dict:
            file_info['id'] = id
            file_info['name'] = self.dict[id].name
            file_info['total'] = self.dict[id].total
            for order in range(1, self.dict[id].total + 1):
                filepath = f"{chunkspath}\{id}_{order}.txt"
                # with open(filepath, 'rb') as fileobj:
                #     content = fileobj.readline()
                #     values = content.split()
                file_info[order] = os.path.getsize(filepath)
        json_file_path = f'{dirpath}\{self.dict[id].name}.json'
        with open(json_file_path, 'w') as json_file:
            json.dump(file_info, json_file, indent=4)
        return json_file_path

    def add_file_from_JSON(self, JSONpath):
        with open(JSONpath, 'r') as json_file:
            file_info = json.load(json_file)
            self.add_file(int(file_info.get("id")), file_info.get("name"), int(file_info.get("total")))
            return int(file_info.get("id"))

    def merge(self, other_client_dict: 'Client_dict'):
        for i in other_client_dict.dict.keys():
            if i not in self.dict:
                self.add_file(i, other_client_dict.dict[i].name, other_client_dict.dict[i].total)
            for j in other_client_dict.dict[i].chunks_dict.keys():
                self.add_chunk(i, other_client_dict.dict[i].chunks_dict[j], j)

    def split_chunks(self, id, fromfile, todir):
        name = os.path.basename(fromfile)
        filesize = os.path.getsize(fromfile)
        total = math.ceil(filesize / chunksize)
        self.add_file(id, name, total)
        self.dict[id].split_chunks(id, fromfile, todir)

    def merge_chunks(self, id, tofile):
        if self.is_complete(id):
            self.dict[id].merge_chunks(tofile)


general_dict = Client_dict()


class client:
    def __init__(self):
        self.is_connected = False  # Connection status flag
        self.file_list = Client_dict()
        self.client_host = self.get_local_ip()
        self.client_port = LOCAL_PORT
        self.server_host = ""
        self.server_port = SERVER_PORT
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_soket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.message = ""
        self.log = []
        self.upload_path = ""
        self.download_path = ""
        self.json_path = ""
        self.chunk_path = ""
        self.id = -1
        self.status = 0

    def get_local_ip(self):
        try:
            # Create a socket object and connect to an external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))  # Google's public DNS server and port 80
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except socket.error as e:
            return f"Unable to determine local IP: {str(e)}"

    def set_server_host(self, host):
        self.server_host = host

    def set_client_upload_path(self, path):
        self.upload_path = path

    def set_client_download_path(self, path):
        self.download_path = path

    def set_message(self, message):
        self.message = message

    def get_server_host(self):
        return self.server_host

    def get_client_host(self):
        return self.client_host

    def get_download_dir(self):
        return self.download_path

    def get_upload_dir(self):
        return self.upload_path

    def get_message(self):
        return self.message

    def get_files_list(self):
        return self.file_list

    def send_chunk_to_client(self, clientConnect, clientSocket):
        print(f'Prepare to serve {clientSocket}...')
        receive_message = clientConnect.recv(BYTES).decode("utf-8")
        print(receive_message)
        uniqueID = receive_message.split("--")[0]
        start = receive_message.split("--")[1]
        chunk_files = os.listdir(self.chunk_path)
        correct_chunk_files = [file for file in chunk_files if file.startswith(f'{uniqueID}_')]
        clientConnect.send(f"{len(correct_chunk_files)}".encode("utf-8"))  # send file count
        time.sleep(0.01)
        correct_path = []
        # Always make the file order ascendingly
        sorted_file_names = sorted(correct_chunk_files, key=lambda x: int(x.split('_')[1].split(".")[0]))
        for file in sorted_file_names:
            print(f"sending file:{file}")
            correct_path.append(self.chunk_path + "\\" + file)

        # print(correct_path)

        for i in range(int(start) - 1, len(correct_chunk_files)):
            filesize = os.path.getsize(correct_path[i])
            with open(correct_path[i], "rb") as f:
                text = f.read(chunksize)
                while len(text) != filesize:
                    text = b''
                    text = f.read(chunksize)
                    print("Wrong")
                clientConnect.sendall(text)
                time.sleep(0.3)

            status_file = clientConnect.recv(BYTES).decode("utf-8")
            print(status_file)

            if status_file == "OK":
                self.log.append(f"Continue--{i}")
                print(f"Continue--{i}")
                # self.log.append("[Announcement] Disconnect from the server !")
            else:
                frag_message = status_file.split("--")
                if frag_message[0] == "Fail":
                    i = int(frag_message[1])
                    self.log.append(f"Fail--{i}")
                    print(f"Fail--{i}")
            status_file = ""

    def open_file_serving_socket(self):
        self.file_soket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print(self.get_client_host())
        try:
            self.file_soket.bind((self.get_client_host(), LOCAL_PORT))

        except:
            print("Something went wrong")

        self.file_soket.listen()
        print(f"The file serving socket is {self.file_soket.getsockname()}")
        while True:
            try:
                peer_client, peer_client_socket = self.file_soket.accept()
                s_file_client = threading.Thread(target=self.send_chunk_to_client,
                                                 args=(peer_client, peer_client_socket))
                s_file_client.start()
            except:
                pass

    def handle_server(self):
        self.client_socket.connect((self.get_server_host(), SERVER_PORT))

        while True:
            receive_message = self.client_socket.recv(BYTES).decode("utf-8")
            msg_split = receive_message.split("--")
            cmd = msg_split[1]
            if "Welcome" in cmd:
                self.client_socket.send(f'{LOCAL_PORT}'.encode("utf-8"))
                print("welcome")
                self.log.append(receive_message)

            elif "Upload Successfully" in cmd:
                if len(msg_split) == 3:
                    uniqueID = int(msg_split[2])  # Get unique ID
                    name = os.path.basename(self.upload_path)
                    total_chunks = math.ceil(os.path.getsize(self.upload_path) / chunksize)
                    general_dict.add_file(uniqueID, name, total_chunks)
                    general_dict.split_chunks(uniqueID, self.upload_path, self.chunk_path)
                    general_dict.create_JSON(uniqueID, self.download_path, self.chunk_path)
                self.log.append(receive_message)
                print(f"Upload successfully {uniqueID}")
                break

            elif "Download Successfully" in cmd:
                print(f"Receive: {receive_message}")

                if len(msg_split) == 4:
                    # Get information
                    self.id = int(msg_split[2])
                    peer_info = eval(msg_split[3])

                    # Initialize message
                    general_dict.add_file_from_JSON(self.json_path)
                    general_dict.check_chunks(self.json_path)
                    list_of_missing = (general_dict.missing_file(self.id))
                    size = len(list_of_missing)
                    chunkIdx = 1
                    while size:
                        # Random choose a client to connect
                        # rand_int = random.randint(0, len(peer_info['ip']) - 1)
                        chunkIdx = min(list_of_missing)
                        rand_int = len(peer_info['ip']) - 1
                        miniServerIP = peer_info['ip'][rand_int]
                        miniServerPort = peer_info['port'][rand_int]
                        connect_tuple = (miniServerIP, miniServerPort)  # connect client
                        # Pop connected client out of list
                        print(f"{connect_tuple}")
                        peer_info['ip'].remove(miniServerIP)
                        peer_info['port'].remove(miniServerPort)
                        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                        new_socket.connect(connect_tuple)

                        new_socket.send(f"{self.id}--{chunkIdx}".encode("utf-8"))  # Send uniqueID--chunkStart
                        size = new_socket.recv(BYTES).decode("utf-8")
                        print(f"chunk id:{chunkIdx}")
                        for i in range(chunkIdx - 1, int(size)):
                            path = self.chunk_path + "\\" + f"{self.id}_{chunkIdx}.txt"
                            text = new_socket.recv(2 * chunksize)
                            print(f"self{self.json_path}")
                            print(f"{chunkIdx}:{len(text)}")
                            with open(self.json_path, 'r') as json_file:
                                file_info = json.load(json_file)
                                id = int(file_info.get("id"))
                                # print(f"{chunkIdx}size: {file_info.get(f"{chunkIdx}")}")
                                # if(chunkIdx >= size)
                                sizeofchunk = int(file_info.get(f"{chunkIdx}"))

                            try:
                                if (len(text) == sizeofchunk):
                                    with open(path, 'wb') as file:
                                        file.write(text)
                                    print(f"Text file '{path}' created successfully.")
                                    self.log.append(f"Text file '{path}' created successfully.")
                                    new_socket.send(f"OK".encode("utf-8"))
                                    # time.sleep(0.1)
                                    file.close()
                                    chunkIdx += 1
                                else:
                                    print(f"sys size: {len(text)}, ex size: {int(sizeofchunk)}")
                                    self.log.append(f"Fail--{chunkIdx}".encode("utf-8"))
                                    new_socket.send(f"Fail--{chunkIdx}".encode("utf-8"))
                                    i -= 1

                            except IOError as e:
                                print(f"Error: {chunkIdx}")
                                self.log.append(f"Error: {chunkIdx}")
                                new_socket.send(f"Fail--{chunkIdx}".encode("utf-8"))

                        with open(self.json_path, 'r') as json_file:
                            file_info = json.load(json_file)
                            total = int(file_info.get("total"))
                        # Handle enough chunk => break
                        if (chunkIdx - 1) == total:
                            print("Success")
                            self.status = 1
                            print(f"chunk path 2: {self.chunk_path}")
                            general_dict.add_chunks_from_dir(self.chunk_path, id)
                            general_dict.merge_chunks(id, self.download_path)
                            # Close connection
                            new_socket.close()
                            break

                        if chunkIdx < total:
                            if len(peer_info['ip']) == 0:
                                # case : no peer has enough chunk
                                print("Fail - No peer have enough chunk")
                                self.log.append("Fail - No peer have enough chunk")
                                # removing chunk files
                                files = os.listdir(self.chunk_path)
                                self.status = -1
                                for file in files:
                                    if file.startswith(f"{self.id}_"):
                                        os.remove(os.path.join(self.chunk_path, file))
                                # Close connection
                                new_socket.close()
                                break

                    print("Finished")
                    self.log.append("Finished")
                    return
                break

                self.log.append(receive_message)

            elif "Disconnect" in cmd:
                self.log.append(receive_message)
                break

            elif "Waiting" in cmd:
                self.log.append(receive_message)
                break

            else:
                self.log.append(receive_message)
                print("Something went wrong")
                break

            time.sleep(0.1)

            client_cmd = self.get_message()

            if client_cmd == " ":
                pass

            cmd_split = client_cmd.split(" ")
            cmd = cmd_split[0]

            if cmd == "Upload":
                send_data = f"Upload"
                self.client_socket.send(send_data.encode("utf-8"))
                self.set_message(" ")

            elif cmd == "Download" and (len(cmd_split) == 2):
                self.client_socket.send(client_cmd.encode("utf-8"))
                self.set_message(" ")

            elif cmd == "Disconnect":
                self.client_socket.send(cmd.encode("utf-8"))

            elif cmd == "Waiting":
                self.client_socket.send(cmd.encode("utf-8"))
                self.set_message(" ")

            else:
                print("Something's wrong")
                self.set_message(" ")

        self.log.append("[Announcement] Disconnect from the server !")
        self.client_socket.close()

    def stop_connect_to_server(self):
        self.client_socket.close()

    def start_client(self):
        t2 = threading.Thread(target=self.open_file_serving_socket)
        t2.start()
        return

    def sending_messsage_to_server(self, message):
        t1 = threading.Thread(target=self.handle_server)
        t1.start()
        self.set_message(message)
        t1.join()
        self.stop_connect_to_server()


new_client = client()


class ClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Sharing Client")
        self.geometry("480x480")
        self.client = client()

        self.setup_ui()

    def setup_ui(self):
        # Server IP Configuration
        ttk.Label(self, text="Server IP:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.server_ip_entry = ttk.Entry(self, width=25)
        self.server_ip_entry.grid(row=0, column=1, padx=10, pady=5)

        # Directory for Uploads
        ttk.Label(self, text="Upload Directory:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.up_directory_entry = ttk.Entry(self, width=25)
        self.up_directory_entry.grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(self, text="Browse...", command=self.browse_upload_folder).grid(row=1, column=2, padx=10, pady=5)

        # Directory for JSON
        ttk.Label(self, text="JSON File:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.json_file_entry = ttk.Entry(self, width=25)
        self.json_file_entry.grid(row=2, column=1, padx=10, pady=5)
        ttk.Button(self, text="Browse...", command=self.browse_json_file).grid(row=2, column=2, padx=10, pady=5)

        # Directory for Downloads
        ttk.Label(self, text="Download File:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.down_directory_entry = ttk.Entry(self, width=25)
        self.down_directory_entry.grid(row=3, column=1, padx=10, pady=5)
        ttk.Button(self, text="Browse...", command=self.browse_download_folder).grid(row=3, column=2, padx=10, pady=5)

        # Chunk Directory configuration
        ttk.Label(self, text="Chunk Directory:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.chunk_directory_entry = ttk.Entry(self, width=25)
        self.chunk_directory_entry.grid(row=4, column=1, padx=10, pady=5)
        ttk.Button(self, text="Browse...", command=self.browse_chunk_folder).grid(row=4, column=2, padx=10, pady=5)

        # Connect Button
        ttk.Button(self, text="Connect", command=self.connect_to_server).grid(row=5, columnspan=3, pady=10)

        # File List
        self.file_list = tk.Listbox(self, height=10)
        self.file_list.grid(row=6, column=0, columnspan=3, sticky='ew', padx=10, pady=5)

        # Scrollbar for File List
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.file_list.yview)
        scrollbar.grid(row=6, column=3, sticky='ns')
        self.file_list.config(yscrollcommand=scrollbar.set)

        # Upload and Download Buttons
        ttk.Button(self, text="Upload File", command=self.upload_file).grid(row=7, column=0, padx=10, pady=5)
        ttk.Button(self, text="Download Selected", command=self.download_file).grid(row=7, column=2, padx=10, pady=5)

        ttk.Button(self, text="Refresh List", command=self.fetch_logs).grid(row=8, column=0, padx=10, pady=5)

    def browse_json_file(self):
        filename = filedialog.askopenfilename(initialdir="/", title="Select a JSON file",
                                              filetypes=(("JSON files", "*.json"), ("All files", "*.*")))
        if filename:
            self.json_file_entry.delete(0, tk.END)
            self.json_file_entry.insert(0, filename)
            self.client.json_path = filename

    def fetch_logs(self):
        # Function to fetch logs
        # Get logs from server
        logs = self.client.log

        # Clear existing log text
        self.file_list.delete(0, tk.END)

        # Insert new log entries
        for entry in logs:
            self.file_list.insert(tk.END, f"{entry}\n")

    def browse_upload_folder(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.up_directory_entry.delete(0, tk.END)
            self.up_directory_entry.insert(0, filename)
            self.client.set_client_upload_path(filename)

    def browse_download_folder(self):
        directory = filedialog.askdirectory()
        if directory:
            self.down_directory_entry.delete(0, tk.END)
            self.down_directory_entry.insert(0, directory)
            self.client.set_client_download_path(directory)

    def browse_chunk_folder(self):
        directory = filedialog.askdirectory()
        if directory:
            self.chunk_directory_entry.delete(0, tk.END)
            self.chunk_directory_entry.insert(0, directory)
            self.client.chunk_path = directory
            general_dict.scan_and_add_from_folder(directory)
            print(f"chunk path 1: {self.client.chunk_path}")

    def connect_to_server(self):
        # Retrieve the values from the entries
        server_ip = self.server_ip_entry.get()
        upload_directory = self.up_directory_entry.get()
        json_file = self.json_file_entry.get()
        download_directory = self.down_directory_entry.get()
        chunk_directory = self.chunk_directory_entry.get()

        # Check if any field is empty
        # if not (server_ip and upload_directory and json_file and download_directory and chunk_directory):
        #     missing_fields = []
        #     if not server_ip:
        #         missing_fields.append("Server IP")
        #     if not upload_directory:
        #         missing_fields.append("Upload Directory")
        #     if not json_file:
        #         missing_fields.append("JSON File")
        #     if not download_directory:
        #         missing_fields.append("Download Directory")
        #     if not chunk_directory:
        #         missing_fields.append("Chunk Directory")

        #     # Alert the user about the missing fields
        #     messagebox.showerror("Missing Fields", f"Please fill in the following fields: {', '.join(missing_fields)}")
        #     return  # Prevent further execution until fields are filled

        # If all fields are filled, set server IP and start the connection process
        self.client.set_server_host(server_ip)
        self.client.start_client()
        self.client.is_connected = True  # Set connection flag to True after successful connection
        print("Connection to server initiated.")

    def upload_file(self):
        filename = self.up_directory_entry.get()
        # filename = filedialog.askopenfilename(initialdir=upload_path, title="Select file",
        #                                       filetypes=(("all files", "*.*"), ("pdf files", "*.pdf")))
        if not self.client.is_connected:
            messagebox.showwarning("Connection Required", "Please connect to the server first.")
            return

        if filename:
            try:
                # self.client.upload_path = filename
                # Properly create a thread to handle server communication
                # upload_thread = threading.Thread(target=self.client.handle_server)
                # upload_thread.start()
                # print(self.upload_dir_entry.get())
                self.client.sending_messsage_to_server("Upload")
                print(f"Prepared {filename} for upload.")

            except Exception as e:
                print(f"Failed to prepare the file for upload: {e}")
                messagebox.showerror("Upload Failed", f"Could not prepare the file for upload: {e}")

    def download_file(self):
        if not self.client.is_connected:
            messagebox.showwarning("Connection Required", "Please connect to the server first.")
            return
        try:
            with open(self.client.json_path, 'r') as json_file:
                file_info = json.load(json_file)
                id = int(file_info.get("id"))
            self.client.sending_messsage_to_server(f"Download {id}")
            print("Downloading file...")

        except Exception as e:
            print(f"Failed to prepare the file for upload: {e}")
            messagebox.showerror("Upload Failed", f"Could not prepare the file for upload: {e}")


if __name__ == '__main__':
    app = ClientApp()
    app.mainloop()
    # new_client.set_client_download_path(r"D:\232_semester\CN\New folder\testing_data\ouptut")
    # new_client.set_client_upload_path(r"D:\232_semester\CN\New folder\testing_data\Upload\Horus.pdf")
    # new_client.chunk_path = r"D:\232_semester\CN\New folder\testing_data\chunks"
    # new_client.json_path = r"D:\232_semester\CN\New folder\testing_data\Upload\Horus.pdf.json"
    # new_client.set_server_host("192.168.0.105")

    # with open(new_client.json_path, 'r') as json_file:
    #         file_info = json.load(json_file)
    #         id = int(file_info.get("id"))
    #         print(id)
    # new_client.start_client()
    # new_client.sending_messsage_to_server(f"Download {id}")
    # print("Done")