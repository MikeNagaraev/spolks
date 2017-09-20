import socket
import threading
from datetime import datetime
import sys
import os
import os.path
import time
from commands import server_commands, client_commands, help_list
#
# ip = '192.168.100.5'
ip = ''
# port = 8081

# ip = '192.168.0.110'

port = 9001
BUFFER_SIZE = 2048


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((ip, port))
server.listen(5)



def send_status_and_message(client, request, status, message):
    message = str("" + request + " " + str(status) + " " + message)
    client.send(message.encode('utf-8'))

def send_status(client, request, status):
    message = str("" + request + " " + str(status))
    client.send(message.encode('utf-8'))

def is_file_exist(file_name):
    return os.path.exists(file_name)

def handle_client(client):
    while True:
        if (client["is_closed"] == False):
            request = client['socket'].recv(BUFFER_SIZE).decode('utf-8')
            request = request.strip()
            if request != '':
                print("[*] Received: %s" %request)
                handle_client_request(client, request)

def handle_client_request(client, request):
    command = request.split()
    name_command = command[0]

    if (len(command) == 2):
        file_name = command[1]

    if (client_commands.get(name_command) == "download"):
        if (is_file_exist(file_name)):
            send_status(client['socket'], name_command, 200)
            download(client, file_name)
        else:
            no_file = "File: " + file_name + " is not exist."
            send_status_and_message(client['socket'], name_command, 500, "No such file")

    elif (client_commands.get(name_command) == "delete"):
        if (is_file_exist(file_name)):
            send_status(client['socket'], name_command, 200)
            delete(client, file_name)
        else:
            no_file = "File: " + file_name + " is not exist."
            send_status_and_message(client['socket'], name_command, 500, "No such file")

    elif (client_commands.get(name_command) == "upload"):
        if (is_file_exist(file_name)):
            send_status(client['socket'], name_command, 200)
            upload(client, file_name)
        else:
            no_file = "File: " + file_name + " is not exist."
            send_status_and_message(client['socket'], name_command, 500, no_file)
    else:
        send_status_and_message(client['socket'], name_command, 500, "Unknown command")

def delete(client, file_name):
    pass

def is_client_available(client_ip):
    #timeout
    i = 0

    while(i < 10):
        print("wait for client ...")
        found_client = search_by_ip(clients_pool, client_ip)
        print(found_client)
        if(found_client):
            print("client has returned")
            return True

        i += 1
        time.sleep(1)

    return False


def search_by_ip(list, ip):
    found_client = [element for element in list if element['ip'] == ip]
    return found_client[0] if len(found_client) > 0 else False

def save_temporary_client(ip, command, file_name, progress):
    waiting_clients.append(
        {
            'ip': ip,
            'command': command,
            'file_name': file_name,
            'progress': progress
        })

def handle_disconnect(client, command, file_name, progress):
    save_temporary_client(client['ip'], command, file_name, progress)

    client['socket'].close()
    clients_pool.remove(client)

def wait_ok(client):
    while (client['socket'].recv(2).decode('utf-8') != "OK"):
        print("wait for OK")


def get_data(client):
    return client['socket'].recv(BUFFER_SIZE).decode('utf-8')

def send_data(client, data):
    client['socket'].send(str(data).encode('utf-8'))

def download(client, file_name):
    f = open (file_name, "rb+")

    size = int(os.path.getsize(file_name))

    send_data(client, size) #1

    wait_ok(client) #2

    waiting_client = search_by_ip(waiting_clients, client['ip'])
    waiting_clients[:] = []

    data_size_recv = int(get_data(client)) #3

    if (waiting_client):
        if (waiting_client['file_name'] == file_name and waiting_client['command'] == 'download'):
            data_size_recv = int(waiting_client['progress'])
            send_data(client, data_size_recv)
    else:
        send_data(client, data_size_recv) #4

    wait_ok(client) #5

    f.seek(data_size_recv, 0)

    while (data_size_recv < size):
        try:
            data_file = f.read(BUFFER_SIZE)
            client['socket'].sendall(data_file)
            received_data = get_data(client)

        except socket.error as e:
            data_size_recv = data_size_recv
            handle_disconnect(client, "download", file_name, data_size_recv)
            client['is_closed'] = True
            return

        except KeyboardInterrupt:
            print("KeyboardInterrupt was handled")
            server.close()
            client.socket.close()
            os._exit(1)

        if received_data:
            data_size_recv = int(received_data)
            f.seek(data_size_recv)

        time.sleep(0.4)

    print("file server was downloaded")
    f.close()

def upload(client, client_id, file_name):
    f = open(file_name, 'wb')
    size = int(client.recv(BUFFER_SIZE).decode('utf-8'))
    client.send("OK".encode('utf-8'))
    data_size_recv = 0

    while (data_size_recv != size):
        time.sleep(1)

        data = client.recv(BUFFER_SIZE)
        f.write(data)
        data_size_recv += len(data)
        client.send(str(data_size_recv).encode('utf-8'))

    f.close()

def server_cli():
    while True:
        command = input()
        parsed_data = parse_server_command(command)
        if (parsed_data == False):
            pass
        elif (len(parsed_data) == 2):
            command, body = parsed_data
            handle_server_command(command, body)

def parse_server_command(command):
    command = command.split()
    if (len(command) == 0):
        return False

    name_command = command[0]
    if (len(command) == 2):
        body = command[1]
    else:
        body = ""
    return [name_command, body]

def handle_server_command(command, body):
    if (server_commands.get(command) == "help"):
        show_server_menu()
    if (server_commands.get(command) == "echo"):
        print(body)
    if (server_commands.get(command) == "time"):
        print("Server time: " + str(datetime.now())[:19])
    if (server_commands.get(command) == "exit"):
        server.close()
        os._exit(1)

def show_server_menu():
    for x in help_list:
        print(x, ": ", help_list[x])


def show_start_message():
    print("Hello, listened on %s:%d" %(ip, port))
    show_server_menu()

show_start_message();
server_cli = threading.Thread(target=server_cli)
server_cli.start()
clients_pool = []
waiting_clients = []



while True:

    client_ID = 0
    client, client_info = server.accept()

    client_ip = client_info[0]
    client_port = client_info[1]

    print("[*] Accepted connection from: %s:%d" % (client_ip, client_port))

    clients_pool.append({ "socket": client, "ip": client_ip, "is_closed": False })

    client_handle = threading.Thread(target=handle_client, args=(clients_pool[client_ID], ))
    client_handle.start()

    client_ID += 1;
