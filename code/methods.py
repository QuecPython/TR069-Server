import utime as time
from usr import xmlUtils

INFORM_PARAMS = [
    "Device.DeviceInfo.SpecVersion",
    "InternetGatewayDevice.DeviceInfo.SpecVersion",
    "Device.DeviceInfo.HardwareVersion",
    "InternetGatewayDevice.DeviceInfo.HardwareVersion",
    "Device.DeviceInfo.SoftwareVersion",
    "InternetGatewayDevice.DeviceInfo.SoftwareVersion",
    "Device.DeviceInfo.ProvisioningCode",
    "InternetGatewayDevice.DeviceInfo.ProvisioningCode",
    "Device.ManagementServer.ParameterKey",
    "InternetGatewayDevice.ManagementServer.ParameterKey",
    "Device.ManagementServer.ConnectionRequestURL",
    "InternetGatewayDevice.ManagementServer.ConnectionRequestURL",
    "Device.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress",
    "Device.WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.ExternalIPAddress",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.ExternalIPAddress"
]

pending = []


def getPending():
    return pending.pop(0) if len(pending) > 0 else None


def inform(device, event, callback):
    manufacturer = ""
    if device["DeviceID.Manufacturer"]:
        manufacturer = xmlUtils.node(
            "Manufacturer",
            {},
            device["DeviceID.Manufacturer"][1]
        )
    elif device["Device.DeviceInfo.Manufacturer"]:
        manufacturer = xmlUtils.node(
            "Manufacturer",
            {},
            device["Device.DeviceInfo.Manufacturer"][1]
        )
    elif device["InternetGatewayDevice.DeviceInfo.Manufacturer"]:
        manufacturer = xmlUtils.node(
            "Manufacturer",
            {},
            device["InternetGatewayDevice.DeviceInfo.Manufacturer"][1]
        )
    oui = ""
    if device["DeviceID.OUI"]:
        oui = xmlUtils.node(
            "OUI",
            {},
            device["DeviceID.OUI"][1]
        )
    elif device["Device.DeviceInfo.ManufacturerOUI"]:
        oui = xmlUtils.node(
            "OUI",
            {},
            device["Device.DeviceInfo.ManufacturerOUI"][1]
        )
    elif device["InternetGatewayDevice.DeviceInfo.ManufacturerOUI"]:
        oui = xmlUtils.node(
            "OUI",
            {},
            device["InternetGatewayDevice.DeviceInfo.ManufacturerOUI"][1]
        )
    productClass = ""
    if device["DeviceID.ProductClass"]:
        productClass = xmlUtils.node(
            "ProductClass",
            {},
            device["DeviceID.ProductClass"][1]
        )
    elif device["Device.DeviceInfo.ProductClass"]:
        productClass = xmlUtils.node(
            "ProductClass",
            {},
            device["Device.DeviceInfo.ProductClass"][1]
        )
    elif device["InternetGatewayDevice.DeviceInfo.ProductClass"]:
        productClass = xmlUtils.node(
            "ProductClass",
            {},
            device["InternetGatewayDevice.DeviceInfo.ProductClass"][1]
        )
    serialNumber = ""
    if device["DeviceID.SerialNumber"]:
        serialNumber = xmlUtils.node(
            "SerialNumber",
            {},
            device["DeviceID.SerialNumber"][1])
    elif device["Device.DeviceInfo.SerialNumber"]:
        serialNumber = xmlUtils.node(
            "SerialNumber",
            {},
            device["Device.DeviceInfo.SerialNumber"][1]
        )
    elif device["InternetGatewayDevice.DeviceInfo.SerialNumber"]:
        serialNumber = xmlUtils.node(
            "SerialNumber",
            {},
            device["InternetGatewayDevice.DeviceInfo.SerialNumber"][1]
        )

    deviceId = xmlUtils.node("DeviceId", {}, [manufacturer, oui, productClass, serialNumber])
    eventStruct = xmlUtils.node(
        "EventStruct",
        {},
        [
            xmlUtils.node("EventCode", {}, event or "2 PERIODIC"),
            xmlUtils.node("CommandKey")
        ]
    )
    evnt = xmlUtils.node("Event", {
        "soap-enc:arrayType": "cwmp:EventStruct[1]"
    }, eventStruct)

    params = []
    for p in INFORM_PARAMS:
        param = device.get(p)
        if not param:
            continue
        params.append(
            xmlUtils.node("ParameterValueStruct", {}, [
                xmlUtils.node("Name", {}, p),
                xmlUtils.node("Value", {"xsi:type": param[2]}, param[1])
            ]))

    parameterList = xmlUtils.node("ParameterList", {
        "soap-enc:arrayType": "cwmp:ParameterValueStruct[{}]".format(len(params))
    }, params)

    inform = xmlUtils.node("cwmp:Inform", {}, [
        deviceId,
        evnt,
        xmlUtils.node("MaxEnvelopes", {}, "1"),
        xmlUtils.node("CurrentTime", {}, int(time.mktime(time.localtime()))),
        xmlUtils.node("RetryCount", {}, "0"),
        parameterList
    ])
    return callback(inform)


def getSortedPaths(device):
    if hasattr(device, '_sortedPaths'):
        return device._sortedPaths
    ignore = {"DeviceID", "Downloads", "Tags", "Events", "Reboot", "FactoryReset", "VirtalParameters"}
    sorted_paths = sorted(filter(lambda p: p[0] != '_' and p.split(".")[0] not in ignore, device.keys()))
    device['_sortedPaths'] = sorted_paths
    return sorted_paths


def GetParameterNames(device, request, callback):
    parameterNames = getSortedPaths(device)

    parameterPath, nextLevel = None, None
    for c in request["children"]:
        if c["name"] == "ParameterPath":
            parameterPath = c["text"]
            break
        elif c["name"] == "NextLevel":
            nextLevel = bool(c["text"])
            break

    parameterList = []

    if nextLevel:
        for p in parameterNames:
            if p.startswith(parameterPath) and len(p) > len(parameterPath) + 1:
                i = p.find(".", len(parameterPath) + 1)
                if i == -1 or i == len(p) - 1:
                    parameterList.append(p)
    else:
        for p in parameterNames:
            if p.startswith(parameterPath):
                parameterList.append(p)

    params = []
    for p in parameterList:
        params.append(
            xmlUtils.node("ParameterInfoStruct", {}, [
                xmlUtils.node("Name", {}, p),
                xmlUtils.node("Writable", {}, str(device[p][0]))
            ])
        )

    response = xmlUtils.node(
        "cwmp:GetParameterNamesResponse",
        {},
        xmlUtils.node(
            "ParameterList",
            {"soap-enc:arrayType": "cwmp:ParameterInfoStruct[{}]".format(len(params))},
            params
        )
    )
    return callback(response)


def GetParameterValues(device, request, callback):
    parameterNames = request["children"][0]["children"]
    print(parameterNames)
    params = []
    name = None
    for p in parameterNames:
        name = p["text"]

    if len(device[name]) > 1:
        value = device[name][1]
        _type = device[name][2]
        valueStruct = xmlUtils.node("ParameterValueStruct", {}, [
            xmlUtils.node("Name", {}, name),
            xmlUtils.node("Value", {"xsi:type": _type}, value)
        ])
        params.append(valueStruct)

    response = xmlUtils.node(
        "cwmp:GetParameterValuesResponse",
        {},
        xmlUtils.node(
            "ParameterList",
            {"soap-enc:arrayType": "cwmp:ParameterValueStruct[{}]".format(len(parameterNames))},
            params
        )
    )

    return callback(response)


def SetParameterValues(device, request, callback):
    parameterValues = request["children"][0]["children"]

    name, value = None, None
    for p in parameterValues:
        for c in p["children"]:
            if c["localName"] == "Name":
                name = c["text"]
            elif c["localName"]:
                value = c
                break

    device[name][1] = value["text"]
    for attr in xmlUtils.parseAttrs(value["attrs"]):
        if attr["localName"] == "type":
            device[name][2] = attr['value']
    response = xmlUtils.node("cwmp:SetParameterValuesResponse", {}, xmlUtils.node("Status", {}, "0"))
    return callback(response)


def AddObject(device, request, callback):
    object_name = request["children"][0]["text"]
    instance_number = 1
    if "{}{}.".format(object_name, instance_number) in device:
        instance_number += 1

    device["{}{}.".format(object_name, instance_number)] = [True]

    default_values = {
        "xsd:boolean": "false",
        "xsd:int": "0",
        "xsd:unsignedInt": "0",
        "xsd:dateTime": "0001-01-01T00:00:00Z"
    }

    sorted_paths = getSortedPaths(device)
    for p in sorted_paths:
        if p.startswith(object_name) and len(p) > len(object_name):
            n = "{}{}{}".format(object_name, instance_number, p[p.index('.', len(object_name)):])
            if n not in device:
                default_value = default_values.get(device[p][2], "")
                device[n] = [device[p][0], default_value, device[p][2]]

    instance_number_node = xmlUtils.node("InstanceNumber", {}, str(instance_number))
    status_node = xmlUtils.node("Status", {}, "0")
    response = xmlUtils.node("cwmp:AddObjectResponse", {}, [instance_number_node, status_node])

    device.pop("_sortedPaths", None)
    callback(response)


def DeleteObject(device, request, callback):
    objectName = request["children"][0]["text"]
    for p in list(device.keys()):
        if p.startswith(objectName):
            del device[p]

    response = xmlUtils.node("cwmp:DeleteObjectResponse", {}, xmlUtils.node("Status", {}, "0"))
    del device["_sortedPaths"]
    return callback(response)


def Download(device, request, callback):
    commandKey, url = None, None
    for c in request.children:
        if c.name == "CommandKey":
            commandKey = c.text
        elif c.name == "URL":
            url = c.text

    faultCode = "9010"
    faultString = "Download timeout"

    if url.startswith("http://"):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                faultCode = "0"
                faultString = ""
            else:
                faultCode = "9016"
                faultString = "Unexpected response {}".format(res.status_code)
        except requests.exceptions.Timeout:
            faultString = "Download timeout"
        except requests.exceptions.RequestException as e:
            faultString = str(e)
    elif url.startswith("https://"):
        try:
            res = requests.get(url, timeout=5, verify=False)
            if res.status_code == 200:
                faultCode = "0"
                faultString = ""
            else:
                faultCode = "9016"
                faultString = "Unexpected response {}".format(res.status_code)
        except requests.exceptions.Timeout:
            faultString = "Download timeout"
        except requests.exceptions.RequestException as e:
            faultString = str(e)

    startTime = datetime.now()
    pending.append(
        lambda cb: cb(
            xmlUtils.node("cwmp:TransferComplete", {}, [
                xmlUtils.node("CommandKey", {}, commandKey),
                xmlUtils.node("StartTime", {}, startTime.isoformat()),
                xmlUtils.node("CompleteTime", {}, time.mktime(time.localtime())),
                xmlUtils.node("FaultStruct", {}, [
                    xmlUtils.node("FaultCode", {}, faultCode),
                    xmlUtils.node("FaultString", {}, faultString)
                ])
            ]),
            lambda xml, cb: cb()
        )
    )

    response = xmlUtils.node("cwmp:DownloadResponse", {}, [
        xmlUtils.node("Status", {}, "1"),
        xmlUtils.node("StartTime", {}, "0001-01-01T00:00:00Z"),
        xmlUtils.node("CompleteTime", {}, "0001-01-01T00:00:00Z")
    ])

    return callback(response)


def Reboot(device, request, callback):
    response = xmlUtils.node("cwmp:Reboot ", {}, [
        xmlUtils.node("RebootResponse", {}, ""),
    ])
    return callback(response)


INCLODE = {
    "inform": inform,
    "getPending": getPending,
    "GetParameterNames": GetParameterNames,
    "GetParameterValues": GetParameterValues,
    "SetParameterValues": SetParameterValues,
    "AddObject": AddObject,
    "DeleteObject": DeleteObject,
    "Download": Download,
    "Reboot": Reboot
}
