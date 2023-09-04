# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import usocket
import ujson
import utime
import uio
import _thread

def parse_chunked_data(sock):
    data = b''
    while True:
        chunk_size_str = b''
        while True:
            char = sock.recv(1)
            if char == b'\r':
                continue
            if char == b'\n':
                break
            chunk_size_str += char
        chunk_size = int(chunk_size_str, 16)
        if chunk_size == 0:
            break
        chunk_data = sock.recv(chunk_size)
        data += chunk_data
        sock.recv(2)  # discard \r\n
    return data

class Response:
    def __init__(self, f, decode=True, sizeof=4096):
        self.raw = f
        self.encoding = "utf-8"
        self.decode = decode
        self.sizeof = sizeof

    def close(self):
        if self.raw:
            if s_isopen:
                self.raw.close()
                self.raw = None
        if s_isopen:
            if self.raw:
                # jian.yao 2021-02-22 将套接字标记为关闭并释放所有资源
                self.raw.close()

    @property
    def content(self):
        global s_isopen
        # jian.yao 2021-01-04 新增参数decode,用户可选择开启关闭
        try:
            while True:
                # jian.yao 2020-12-28 分块yield输出
                block = self.raw.read(self.sizeof)
                # jian.yao 2021-01-11 增加read读取块的大小配置
                if block:
                    yield block.decode() if self.decode else block
                else:
                    self.raw.close()  # jian.yao 2021-02-22 将套接字标记为关闭并释放所有资源
                    s_isopen = False
                    break
        except Exception as e:
            self.raw.close() # 2021-05-27
            s_isopen = False
            pass

    def recv_size(self):
        try:
            block = self.raw.read(int(self.sizeof))
            #s_isopen = False
            #s.close()
            #print("recv_size block = %s"%str(block))
            return block
        except Exception as e:
            print("Exception e = %s"%str(e))
            self.raw.close()
        return ""

    @property
    def text(self):
        # jian.yao 2021-01-04 text yield输出
        for i in self.content:
            yield str(i)
        return ""

    def json(self):
        # jian.yao 2021-01-04 TODO 大文件输出会出错
        try:
            json_str = ""
            for i in self.content:
                json_str += i
            # jian.yao 2021-02-07 如果调用此方法前使用了content/text则返回空
            if json_str:
                return ujson.loads(json_str)
            else:
                return None
        except Exception as e:
            raise ValueError(
                "The data for the response cannot be converted to JSON-type data,please try use response.content method")


def request(method, url, data=None, json=None, files=None, stream=None, decode=True, sizeof=255, timeout=None, headers=None,
            ssl_params=None, version=0, s=None):
    global port
    global s_isopen
    s_isopen = True
    port_exist = False
    URL = url
    if not url.split(".")[0].isdigit():
        if not url.startswith("http"):
            url = "http://" + url
        try:
            proto, dummy, host, path = url.split("/", 3)
        except ValueError:
            proto, dummy, host = url.split("/", 2)
            path = ""
        # jian.yao 2020-12-08 新增对ip:port格式的判断
        if ":" in host:
            url_info = host.split(":")
            host = url_info[0]
            port = int(url_info[1])
            port_exist = True
        # jian.yao 2020-12-09
        if proto == "http:":
            if not port_exist:
                port = 80
        # jian.yao 2020-12-09
        elif proto == "https:":
            if not port_exist:
                port = 443
        else:
            raise ValueError("Unsupported protocol: " + proto)
        try:
            ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
            ai = ai[0]
        except IndexError:
            raise IndexError("Domain name resolution error, please check network connection")

    # jian.yao 2020-12-08 新增对错误ip的判断并提醒用户重新输入正确的ip:port
    elif url.split(".")[0].isdigit() and ":" not in url:
        raise ValueError(
            "MissingSchema: Invalid URL '{}': No schema supplied. Perhaps you meant http://{}? ".format(url, url))
    else:
        path = ""
        proto = ""
        if ":" not in url:
            raise ValueError("URL address error: !" + url)
        try:
            if "/" in url:
                ip_info = url.split('/', 1)
                path = ip_info[1]
                host, port = ip_info[0].split(":")
            else:
                host, port = url.split(":")
        except:
            raise ValueError("URL address error: " + url)
        try:
            ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
            ai = ai[0]
        except IndexError:
            raise IndexError("Domain name resolution error, please check network connection")
    #global s
    try:
        if s is None:
            # jian.yao 2020-12-09 check connect error
            try:
                s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
                # jian.yao 2021-01-11 增加socket超时时间
                s.settimeout(timeout)  # 设置socket阻塞模式
                s.connect(ai[-1])
            except Exception as e:
                raise RuntimeError("HTTP Connection FAIL='{}'(host='{}', port=8080):'))".format(str(e), URL))
            if proto == "https:":
                import ussl
                try:
                    if ssl_params:
                        s = ussl.wrap_socket(s, **ssl_params)
                    else:
                        s = ussl.wrap_socket(s, server_hostname=host)
                except Exception as e:
                    raise RuntimeError("HTTP SSL INIT FAIL")
        if version == 1:
            s.write(b"%s /%s HTTP/1.1\r\n" % (method, path))
        else:
            s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))
        s.write(b"Host: %s\r\n" % host)

        if version == 1:
            s.write(b"Connection: keep-alive\r\n")
        if headers:
            if files:
                boundary = str(utime.time())
                if not (files.get("filepath") and files.get("filename")):
                    raise ValueError("Missing key parameters 'filepath' and 'filename'")
                if headers.get('Content-Type') == "multipart/form-data":
                    headers['Content-Type'] = headers['Content-Type'] + '; boundary={}'.format(boundary)
                    headers['charset'] = 'UTF-8'
        else:
            headers = dict()
            if files:
                boundary = str(utime.time())
                headers['Content-Type'] = "multipart/form-data; boundary={}".format(boundary)
                headers['charset'] = 'UTF-8'
            if json:
                headers['Content-Type'] = "application/json"
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")
        if json is not None:
            assert data is None
            data = ujson.dumps(json)
        if data:
            s.write(b"Content-Length: %d\r\n" % len(data))
            s.write(b"\r\n")
            s.write(data)
        else:
            s.write(b"Content-Length: 0\r\n")
        if files:
            import uos
            file_path = files.get("filepath")
            with open(file_path, 'rb') as f:
                content = f.read(4096)
                if files.get("name") is not None:
                    datas = '--{0}{1}Content-Disposition: form-data; {2}{1}{1}{3}{1}--{0}'. \
                        format(boundary, '\r\n', files.get("name"), content)
                else:
                    datas = '--{0}{1}Content-Disposition: form-data; name="file"; filename="{2}"{1}Content-Type: application/octet-stream{1}{1}'.format(
                        boundary, '\r\n', files.get("filename"))
                if files.get("filepath1") is not None:
                    with open('{}'.format(files.get("filepath1")), 'r') as f1:
                        content1 = f1.read()
                        if files.get("name1") is not None:
                            datas += '{1}Content-Disposition: form-data; {2}{1}{1}{3}{1}--{0}'. \
                                    format(boundary, '\r\n', files.get("name1"), content1)
                        else:
                            if files.get("filename1") is None:
                                raise ValueError("Missing key parameters 'filename1' ")
                            datas += '{1}Content-Disposition: form-data; name="file"; filename="{2}"{1}Content-Type: application/octet-stream{1}{1}{3}{1}--{0}'. \
                                      format(boundary, '\r\n', files.get("filename1"), content1)
                suffix = '{1}--{0}--{1}'.format(boundary, '\r\n')
                len_d = uos.stat(file_path)[-4] + len(datas) + len(suffix)
                s.write(b"Content-Length: %d\r\n" % len_d)
                s.write(b"\r\n")
                s.write(datas)
                while content:
                    s.write(content)
                    content = f.read(4096)
                s.write(suffix)
        if not (files and data):
            s.write(b"\r\n")
        l = s.readline()
        uheaders = {}
        chunked_encoding = False
        try:
            # jian.yao 2020-12-09 Abnormal response handle
            l = l.split(None, 2)
            status = int(l[1])
        except:
            raise ValueError("InvalidSchema: No connection adapters were found for '{}'".format(URL))
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            j = l.decode().split(":")
            if j[0] == "Content-Length":
                sizeof =  j[1].replace("\n", "").replace("\r", "")
                #print("Content-Length = %s"%sizeof)
            try:
                uheaders[j[0]] = j[1].replace("\n", "").replace("\r", "")
            except Exception as e:
                pass
            if not l or l == b"\r\n":
                break

            if l.lower().startswith(b"transfer-encoding:"):
                if b"chunked" in l.lower():
                    chunked_encoding = True
            if l.startswith(b"Location:") and not 200 <= status <= 299:
                raise NotImplementedError("Redirects not yet supported")
    except OSError:
        s.close()
        raise
    if chunked_encoding:
        resp = Response(uio.BytesIO(parse_chunked_data(s)))
    else:
        resp = Response(s, sizeof=sizeof)
    resp.status_code = status
    resp.reason = reason
    resp.headers = uheaders
    return resp


def head(url, **kw):
    return request("HEAD", url, **kw)


def get(url, **kw):
    return request("GET", url, **kw)


def post(url, **kw):
    return request("POST", url, **kw)


def put(url, **kw):
    return request("PUT", url, **kw)


def patch(url, **kw):
    return request("PATCH", url, **kw)


def delete(url, **kw):
    return request("DELETE", url, **kw)

class Session(object):
    def __init__(self, timeout=20):
        self.conn_flag = False
        self.host = None
        self.port = 0
        self.socket = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        self.socket.settimeout(timeout)

    def __conn_address(self, url):
        print("[xjin] __conn_address url=%s self.conn_flag =%s"%(url,self.conn_flag))
        # while(True):
        #     if self.httplock is not None and self.httplock.locked():
        #         utime.sleep_ms(10)
        #     else:
        #         print("[xjin] __conn_address httplock break ")
        #         break

        if self.conn_flag:
            return 0

        # print("[xjin] __conn_address httplock acquire ")
        if not url.split(".")[0].isdigit():
            if not url.startswith("http"):
                url = "http://" + url
            try:
                proto, dummy, host, path = url.split("/", 3)
            except ValueError:
                proto, dummy, host = url.split("/", 2)
                path = ""
            self.host = host
            if ":" in host:
                url_info = host.split(":")
                self.host = url_info[0]
                self.port = int(url_info[1])
            elif proto == "http:":
                self.port = 80
            # jian.yao 2020-12-09
            elif proto == "https:":
                self.port = 443
            else:
                raise ValueError("Unsupported protocol: " + proto)
            #self.host = host

        # jian.yao 2020-12-08 新增对错误ip的判断并提醒用户重新输入正确的ip:port
        elif url.split(".")[0].isdigit() and ":" not in url:
            raise ValueError(
                "MissingSchema: Invalid URL '{}': No schema supplied. Perhaps you meant http://{}? ".format(url, url))
        else:
            path = ""
            proto = ""
            if ":" not in url:
                raise ValueError("URL address error: !" + url)
            try:
                if "/" in url:
                    ip_info = url.split('/', 1)
                    path = ip_info[1]
                    self.host, self.port = ip_info[0].split(":")
                else:
                    self.host, self.port = url.split(":")
            except:
                raise ValueError("URL address error: " + url)

        try:
            ai = usocket.getaddrinfo(self.host, self.port)
            ai = ai[0]
            print(ai[-1])
            self.socket.connect(ai[-1])
            print("[xjin] connect self.host %s self.port %s success"%(self.host,self.port))
        except Exception as e:
            raise RuntimeError("HTTP Connection FAIL='{}'(host='{}', port=8080):'))".format(str(e), url))
        if proto == "https:":
            import ussl
            try:
                if ssl_params:
                    self.socket = ussl.wrap_socket(s, **ssl_params)
                else:
                    self.socket = ussl.wrap_socket(s, server_hostname=self.host)
                self.conn_flag = True
            except Exception as e:
                raise RuntimeError("HTTP SSL INIT FAIL")
        else:
            self.conn_flag = True

    def head(self, url, **kw):
        self.__conn_address(url)
        return request("HEAD", url, **kw, version=1, s=self.socket)

    def get(self, url, **kw):
        self.__conn_address(url)
        return request("GET", url, **kw, version=1, s=self.socket)


    def post(self, url, **kw):
        self.__conn_address(url)
        return request("POST", url, **kw, version=1, s=self.socket)


    def put(self, url, **kw):
        self.__conn_address(url)
        return request("PUT", url, **kw, version=1, s=self.socket)


    def patch(self, url, **kw):
        self.__conn_address(url)
        return request("PATCH", url, **kw, version=1, s=self.socket)


    def delete(self, url, **kw):
        self.__conn_address(url)
        return request("DELETE", url, **kw, version=1, s=self.socket)

    def close(self):
        self.socket.close()


