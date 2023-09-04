import _thread
import usys
import osTimer
import ubinascii
import urandom as random
from usr import urequest
# import request
from usr import methods
from usr import xmlUtils
import ujson as json
from usr.tcp_server import TcpServer

NAMESPACES = {
    "soap-enc": "http://schemas.xmlsoap.org/soap/encoding/",
    "soap-env": "http://schemas.xmlsoap.org/soap/envelope/",
    "xsd": "http://www.w3.org/2001/XMLSchema",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "cwmp": "urn:dslforum-org:cwmp-1-0"
}

nextInformTimeout = osTimer()
pendingInform = False
http = None
requestOptions = None
control_cwmp = None
device = None
httpAgent = None
basicAuth = None
cookie = None
first = True
tr069_server = None


def createSoapDocument(id, body):
    headerNode = xmlUtils.node(
        "soap-env:Header",
        {},
        xmlUtils.node(
            "cwmp:ID",
            {"soap-env:mustUnderstand": 1},
            id
        )
    )

    bodyNode = xmlUtils.node("soap-env:Body", {}, body)
    namespaces = {}
    for prefix in NAMESPACES:
        namespaces["xmlns:{}".format(prefix)] = NAMESPACES[prefix]

    env = xmlUtils.node("soap-env:Envelope", namespaces, [headerNode, bodyNode])

    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{}".format(env)


def sendRequest(xml, callback):
    global httpAgent, cookie
    headers = {}
    body = xml or ""

    headers["Content-Type"] = "text/xml; charset=\"utf-8\""
    # TODO 暂时不用
    headers["Accept-Encoding"] = "gzip, deflate"
    headers["Accept"] = "*/*"
    headers["Authorization"] = basicAuth

    if cookie:
        headers["Cookie"] = cookie

    options = {
        "method": "POST",
        "headers": headers,
    }
    options.update(requestOptions)
    print("------------------ headers & body ------------------")
    # print(headers)
    # print(body)
    try:
        # print("request = ", requestOptions["url"], "headers = ", options["headers"], "data = ",body)
        response = httpAgent.post(url=requestOptions["url"], headers=options["headers"], data=body)

        # print("response.headers = ", response.headers)

        if response.status_code // 100 != 2:
            raise Exception("Unexpected response Code {}".format(response.status_code))
        if int(response.headers.get("Content-Length", 0)) > 0:
            body = b""
            body = response.recv_size()
            # print("response body =", body)
            xml = xmlUtils.parseXml(body.decode())
        else:
            print("response None")
            xml = None

        if "Set-Cookie" in response.headers:
            cookie = response.headers["Set-Cookie"]

        _thread.start_new_thread(callback, (xml,))
    except Exception as e:
        periodic_inform()


def startSession(event):
    print("------------------start session ------------ {}".format(event))
    global pendingInform, nextInformTimeout
    nextInformTimeout = None
    pendingInform = False
    requestId = ""
    for i in range(8):
        requestId += random.choice('abcdefghijklmnopqrstuvwxyz0123456789')

    def func(body):
        xml = createSoapDocument(requestId, body)
        sendRequest(xml, lambda xml: cpeRequest())

    methods.inform(device, event, func)


def createFaultResponse(code, message):
    fault = xmlUtils.node(
        "detail",
        {},
        xmlUtils.node("cwmp:Fault", {}, [
            xmlUtils.node("FaultCode", {}, code),
            xmlUtils.node("FaultString", {}, message)
        ])
    )

    soapFault = xmlUtils.node("soap-env:Fault", {}, [
        xmlUtils.node("faultcode", {}, "Client"),
        xmlUtils.node("faultstring", {}, "CWMP fault"),
        fault
    ])

    return soapFault


def cpeRequest():
    pending = methods.getPending()
    if not pending:
        sendRequest(None, lambda xml: handleMethod(xml))
        return

    requestId = ""
    for i in range(8):
        requestId += random.choice('abcdefghijklmnopqrstuvwxyz0123456789')

    def callback(body, func):
        xml = createSoapDocument(requestId, body)
        sendRequest(xml, lambda xml: func(xml, cpeRequest))

    pending(callback)


def restart_session(*args):
    # print("wait ~~~~~~~~~~~~~~~~ args {}".format(args))
    global httpAgent
    httpAgent = urequest.Session()
    startSession(None)


def _restart_session(*args):
    _thread.start_new_thread(restart_session, (args,))


def periodic_inform():
    # print("-------------- periodic_inform------------")
    global nextInformTimeout, control_cwmp
    # print(control_cwmp.get("report_interval"))
    # TODO: 测试注释
    # report_interval = control_cwmp.get("report_interval", 120)
    report_interval = 0
    if report_interval == 0:
        report_interval = 120
    informInterval = int(report_interval) * 1000
    # print("informInterval -> {}".format(informInterval))
    if not nextInformTimeout:
        nextInformTimeout = osTimer()
    nextInformTimeout.stop()
    nextInformTimeout.start(informInterval, 0, _restart_session)


def handleMethod(xml):
    global pendingInform, first, cookie
    if not xml:
        httpAgent.close()
        cookie = None
        print("httpAgent.close")
        informInterval = 120
        if "Device.ManagementServer.PeriodicInformInterval" in device:
            informInterval = int(device["Device.ManagementServer.PeriodicInformInterval"][1])
        elif "InternetGatewayDevice.ManagementServer.PeriodicInformInterval" in device:
            informInterval = int(device["InternetGatewayDevice.ManagementServer.PeriodicInformInterval"][1])
        if pendingInform:
            print("pendingInform ~~~ {}".format(pendingInform))
            _thread.start_new_thread(restart_session, ())
        else:
            if not first:
                periodic_inform()
            else:
                print("----- startSession")
                _thread.start_new_thread(restart_session, ())
                first = False
            return

    headerElement, bodyElement = None, None
    envelope = xml["children"][0]
    for c in envelope["children"]:
        if c["localName"] == "Header":
            headerElement = c
        elif c["localName"] == "Body":
            bodyElement = c

    requestId = None
    for c in headerElement["children"]:
        if c["localName"] == "ID":
            requestId = c["text"]
            break

    requestElement = None
    for c in bodyElement["children"]:
        if c["name"].startswith("cwmp:"):
            requestElement = c
            break
    method = methods.INCLODE.get(requestElement["localName"])

    if not method:
        body = createFaultResponse(9000, "Method not supported")
        xml = createSoapDocument(requestId, body)
        sendRequest(xml, lambda xml: handleMethod(xml))
        return

    def func(body):
        xml = createSoapDocument(requestId, body)
        sendRequest(xml, lambda xml: handleMethod(xml))

    method(device, requestElement, func)


def listenForConnectionRequests(serialNumber, acsUrlOptions, callback):
    global tr069_server
    tr069_server = TcpServer(acsUrlOptions["server_ip"], acsUrlOptions["server_port"])
    tr069_server.set_callback(callback)
    connectionRequestUrl = "http://{}:{}".format(acsUrlOptions["server_ip"], acsUrlOptions["server_port"])
    if device["InternetGatewayDevice.ManagementServer.ConnectionRequestURL"]:
        device["InternetGatewayDevice.ManagementServer.ConnectionRequestURL"][1] = connectionRequestUrl
    elif device["Device.ManagementServer.ConnectionRequestURL"]:
        device["Device.ManagementServer.ConnectionRequestURL"][1] = connectionRequestUrl
    startSession("6 CONNECTION REQUEST")
    tr069_server.run()


def _start(dataModel, serialNumber, acsUrl):
    global device, httpAgent, basicAuth, pendingInform
    device = dataModel

    if device.get("DeviceID.SerialNumber"):
        device["DeviceID.SerialNumber"][1] = serialNumber
    if device.get("Device.DeviceInfo.SerialNumber"):
        device["Device.DeviceInfo.SerialNumber"][1] = serialNumber
    if device.get("InternetGatewayDevice.DeviceInfo.SerialNumber"):
        device["InternetGatewayDevice.DeviceInfo.SerialNumber"][1] = serialNumber

    username = requestOptions.get("username")
    password = requestOptions.get("password")
    if device.get("Device.ManagementServer.Username"):
        username = device["Device.ManagementServer.Username"][1]
        password = device["Device.ManagementServer.Password"][1]
    elif device.get("InternetGatewayDevice.ManagementServer.Username"):
        username = device["InternetGatewayDevice.ManagementServer.Username"][1]
        password = device["InternetGatewayDevice.ManagementServer.Password"][1]

    httpAgent = urequest.Session()

    # session.request()
    auth_data = "{}:{}".format(username, password)
    # 加密
    basicAuth = "Basic " + ubinascii.b2a_base64(auth_data)[:-1].decode()

    def func(conn, ip, port):
        print("func ----- {} {}".format(ip, port))
        global pendingInform
        if not nextInformTimeout:
            pendingInform = True
        else:
            nextInformTimeout.stop()
            startSession("6 CONNECTION REQUEST")

    listenForConnectionRequests(serialNumber, requestOptions, func)


def start(dataModel, serialNumber, acsUrl):
    import utime
    while True:
        try:
            # 获取tr069控制参数
            _start(dataModel, serialNumber, acsUrl)
        except Exception as e:
            usys.print_exception(e)
            # print("--------------------------------------111")
            nextInformTimeout.stop()
            utime.sleep(120)
        else:
            break


class CWMPRepository(object):
    _instance = None
    _file = None

    @classmethod
    def get(cls, key):
        print('get data model instance -> ', cls._instance)
        return cls._instance[key]

    @classmethod
    def post(cls, key, value):
        print('set data model instance -> ', cls._instance)
        cls._instance[key] = value
        cls.store()

    @classmethod
    def post_all(cls, data):
        for item in data:
            print('set data model instance -> ', cls._instance)
            cls._instance[item['key']] = item['value']
        cls.store()

    @classmethod
    def data(cls):
        return cls._instance

    @classmethod
    def store(cls):
        with open(cls._file, 'w') as f:
            json.dump(cls._instance, f)

    @classmethod
    def _read(cls):
        with open(cls._file, 'r') as f:
            # 使用json.load()方法将JSON数据读取为Python对象
            return json.load(f)

    @classmethod
    def build(cls, file):
        if not cls._instance:
            cls._file = file
            cls._instance = cls._read()
        return cls


def SetRequestOptions(data, c_data):
    print('SetRequestOptions -> ', data)
    global requestOptions, control_cwmp
    requestOptions = data
    control_cwmp = c_data


if __name__ == '__main__':
    _thread.stack_size(32 * 1024)
    requestOptions = {
        "protocol": 'http:',
        "slashes": True,
        "auth": None,
        "host": '39.106.195.193:9090',
        "port": '9090',
        "hostname": '39.106.195.193',
        "server_ip": '0.0.0.0',
        "server_port": 8001,
        "hash": None,
        "search": None,
        "query": None,
        "pathname": '/ACS-server/ACS/pawn',
        "path": '/ACS-server/ACS/pawn',
        "href": 'http://39.106.195.193:9090/ACS-server/ACS/pawn',
        "url": 'http://39.106.195.193:9090/ACS-server/ACS/pawn'
    }
    import ujson as json

    with open('usr/data_model_2021.json', 'r') as f:
        # 使用json.load()方法将JSON数据读取为Python对象
        data = json.load(f)
    serialNumber = "000020"  # 设备序列号
    start(data, serialNumber, "http://39.106.195.193:9090/ACS-server/ACS/xjin")
