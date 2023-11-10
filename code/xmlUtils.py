CHAR_SINGLE_QUOTE = 39
CHAR_DOUBLE_QUOTE = 34
CHAR_LESS_THAN = 60
CHAR_GREATER_THAN = 62
CHAR_COLON = 58
CHAR_SPACE = 32
CHAR_TAB = 9
CHAR_CR = 13
CHAR_LF = 10
CHAR_SLASH = 47
CHAR_EXMARK = 33
CHAR_QMARK = 63
CHAR_EQUAL = 61

STATE_LESS_THAN = 1
STATE_SINGLE_QUOTE = 2
STATE_DOUBLE_QUOTE = 3


def node(key, attrs=None, value=""):
    if not attrs:
        attrs = {}
    if isinstance(value, list):
        value = "".join(value)
    attrsStr = ""
    for k, v in attrs.items():
        attrsStr += ' {}="{}"'.format(k, v)
    if not value:
        return '<{}{}/>'.format(key, attrsStr)
    return '<{}{}>{}</{}>'.format(key, attrsStr, value, key)


def parseAttrs(string):
    attrs = []
    len_str = len(string)
    state = 0
    name = ""
    namespace = ""
    local_name = ""
    idx = 0
    colon_idx = 0

    for i in range(len_str):
        c = ord(string[i])
        if c == CHAR_SINGLE_QUOTE or c == CHAR_DOUBLE_QUOTE:
            if state == c:
                state = 0
                if name:
                    value = string[idx + 1:i]
                    e = {"name": name, "namespace": namespace, "localName": local_name, "value": value}
                    attrs.append(e)
                    name = ""
                    idx = i + 1
            else:
                state = c
                idx = i
            continue
        elif c == CHAR_COLON:
            if idx >= colon_idx:
                colon_idx = i
            continue
        elif c == CHAR_EQUAL:
            if name:
                raise Exception("Unexpected character at {}".format(i))
            name = string[idx:i].strip()
            if colon_idx > idx:
                namespace = string[idx:colon_idx].strip()
                local_name = string[colon_idx + 1:i].strip()
            else:
                namespace = ""
                local_name = name
    if name:
        raise Exception("Attribute must have value at {}".format(idx))
    tail = string[idx:]
    if tail.strip():
        raise Exception("Unexpected string at {}".format(len_str - len(tail)))
    return attrs


def parseXml(string):
    _len = len(string)
    state1 = 0
    state1Index = 0
    state2 = 0
    state2Index = 0

    root = {
        'name': 'root',
        'namespace': '',
        'localName': 'root',
        'attrs': '',
        'text': '',
        'bodyIndex': 0,
        'children': []
    }
    stack = [root]

    for i in range(_len):
        char_code = ord(string[i])
        if char_code == CHAR_SINGLE_QUOTE:
            if (state1 & 0xff) == STATE_SINGLE_QUOTE:
                state1 = state2
                state1Index = state2Index
                state2 = 0
                continue
            elif (state1 & 0xff) == STATE_LESS_THAN:
                state2 = state1
                state2Index = state1Index
                state1 = STATE_SINGLE_QUOTE
                state1Index = i
                continue
        elif char_code == CHAR_DOUBLE_QUOTE:
            if (state1 & 0xff) == STATE_DOUBLE_QUOTE:
                state1 = state2
                state1Index = state2Index
                state2 = 0
                continue
            elif (state1 & 0xff) == STATE_LESS_THAN:
                state2 = state1
                state2Index = state1Index
                state1 = STATE_DOUBLE_QUOTE
                state1Index = i
                continue
        elif char_code == CHAR_LESS_THAN:
            if (state1 & 0xff) == 0:
                state2 = state1
                state2Index = state1Index
                state1 = STATE_LESS_THAN
                state1Index = i
        elif char_code == CHAR_COLON:
            if (state1 & 0xff) == STATE_LESS_THAN:
                colonIndex = (state1 >> 8) & 0xff
                if colonIndex == 0:
                    state1 ^= ((i - state1Index) & 0xff) << 8
        elif char_code == CHAR_SPACE or char_code == CHAR_TAB or char_code == CHAR_CR or char_code == CHAR_LF:
            if (state1 & 0xff) == STATE_LESS_THAN:
                wsIndex = (state1 >> 16) & 0xff
                if wsIndex == 0:
                    state1 ^= ((i - state1Index) & 0xff) << 16
        elif char_code == CHAR_GREATER_THAN:
            if (state1 & 0xff) == STATE_LESS_THAN:
                secondChar = ord(string[state1Index + 1])
                wsIndex = (state1 >> 16) & 0xff
                if secondChar == CHAR_SLASH:
                    e = stack.pop()
                    if wsIndex == 0:
                        name = string[state1Index + 2:i]
                    else:
                        name = string[state1Index + 2:state1Index + wsIndex]
                    if e['name'] != name:
                        raise Exception("Unmatched closing tag at {}".format(i))
                    if not e['children']:
                        e['text'] = string[e['bodyIndex']:state1Index]
                    state1 = state2
                    state1Index = state2Index
                    state2 = 0
                    continue
                elif secondChar == CHAR_EXMARK:
                    if string.startswith("![CDATA[", state1Index + 1):
                        if string.endswith("]]", i):
                            raise Exception("CDATA nodes are not supported at {}".format(i))
                    elif string.startswith("!--", state1Index + 1):
                        if string.endswith("--", i):
                            state1 = state2
                            state1Index = state2Index
                            state2 = 0
                    continue
                elif secondChar == CHAR_QMARK:
                    if ord(string[i - 1]) == CHAR_QMARK:
                        state1 = state2
                        state1Index = state2Index
                        state2 = 0
                    continue
                else:
                    selfClosing = +int(ord(string[i - 1]) == CHAR_SLASH)
                    parent = stack[-1]
                    colonIndex = (state1 >> 8) & 0xff

                    name = string[state1Index + 1:i - selfClosing] if wsIndex == 0 else string[
                                                                                        state1Index + 1:state1Index + wsIndex]
                    if colonIndex and (not wsIndex or colonIndex < wsIndex):
                        localName = name[colonIndex:]
                        namespace = name[:colonIndex - 1]
                    else:
                        localName = name
                        namespace = ""
                    e = {
                        "name": name,
                        "namespace": namespace,
                        "localName": localName,
                        "attrs": string[state1Index + wsIndex + 1:i - selfClosing] if wsIndex else "",
                        "text": "",
                        "bodyIndex": i + 1,
                        "children": []
                    }
                    parent["children"].append(e)
                    if not selfClosing:
                        stack.append(e)

                    state1 = state2
                    state1Index = state2Index
                    state2 = 0

    if state1:
        raise ValueError("Unclosed token at {}".format(state1Index))

    if len(stack) > 1:
        e = stack[-1]
        raise ValueError("Unclosed XML element at {}".format(e['bodyIndex']))

    return root
