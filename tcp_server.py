import _thread
import usocket


class TcpServer(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.answer = """"""
        self.tx_id = None
        self.callback = None

    def set_callback(self, callback):
        self.callback = callback

    def process(self, conn, ip_addr, port):
        while True:
            try:
                # 接收客户端发送的数据
                data = conn.recv(1024)
                print('[server] [client addr: %s, %s] recv data:' % (ip_addr, port), data)
                # 向客户端回送数据
                data = """HTTP/1.1 200 OK\r\nConnection: keep-alive\r\nKeep-Alive: timeout=5\r\nContent-Length: 0\r\n\r\n"""
                conn.send(data)
                conn.close()
                if self.callback:
                    self.callback(conn, self.ip, self.port)
                break
            except Exception as e:
                # 出现异常，连接断开
                print('[server] [client addr: %s, %s] disconnected' % (ip_addr, port))
                conn.close()
                break

    def __run(self):
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM, usocket.IPPROTO_TCP_SER)
        print('[server] socket object created.')

        # 绑定服务器 IP 地址和端口
        sock.bind((self.ip, self.port))
        print('[server] bind address: %s, %s' % (self.ip, self.port))

        # 监听客户端连接请求
        sock.listen(10)
        print('[server] started, listening ...')

        while True:
            # 接受客户端连接请求
            cli_conn, cli_ip_addr, cli_port = sock.accept()
            print('[server] accept a client: %s, %s' % (cli_ip_addr, cli_port))

            # 每接入一个客户端连接，新建一个线程，即连接并行处理
            _thread.start_new_thread(self.process, (cli_conn, cli_ip_addr, cli_port))

    def run(self):
        self.tx_id = _thread.start_new_thread(self.__run, ())

    def close(self):  # close
        if self.tx_id:
            _thread.stop_thread(self.tx_id)
