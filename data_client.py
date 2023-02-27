import socket
from datetime import datetime
import pickle
import struct

ADDR = ("192.168.0.10", 20002)

class DoubleValue:
    def __init__(self) -> None:
        self.id = 1
        self.time = 0.0
        self.value = 0.0

    def pack(self):
        return struct.pack("<bdd", self.id, self.time, self.value)

    def unpack(self, bytes):
        self.id, self.time, self.value = struct.unpack("<bdd", bytes)

    def size(self):
        return 17 # 1 + 8 + 8

    def valid_value(value):
        return isinstance(value, float)

class IntegerValue:
    def __init__(self) -> None:
        self.id = 2
        self.time = 0.0
        self.value = 0

    def pack(self):
        return struct.pack("<bdi", self.id, self.time, self.value)

    def unpack(self, bytes):
        self.id, self.time, self.value = struct.unpack("<bdi", bytes)

    def size(self):
        return 13 # 1 + 8 + 4

    def valid_value(value):
        return isinstance(value, int)

class BooleanValue:
    def __init__(self) -> None:
        self.id = 3
        self.time = 0.0
        self.value = False

    def pack(self):
        return struct.pack("<bd?", self.id, self.time, self.value)

    def unpack(self, bytes):
        self.id, self.time, self.value = struct.unpack("<bd?", bytes)

    def size(self):
        return 10 # 1 + 8 + 1

    def valid_value(value):
        return isinstance(value, bool)

class StringValue:
    def __init__(self) -> None:
        self.id = 4
        self.time = 0.0
        self.value = ""

    def pack(self):
        size = len(self.value)
        extra = f"{size}s"
        fmt = "<bdh"+extra
        return struct.pack(fmt, self.id, self.time, size, self.value.encode())

    def unpack(self, bytes):
        _, _, size = struct.unpack("<bdh", bytes[0:18])
        extra = f"{size}s"
        fmt = "<bdh"+extra
        self.id, self.time, _, self.value = struct.unpack(fmt, bytes)
        self.value = self.value.decode('utf-8')

    def size(self):
        size = len(self.value)
        return 11 + size # 1 + 8 + 2 + length of string

    def valid_value(value):
        return isinstance(value, str)


TYPES = [   
            DoubleValue,  # in ID order, note that
            IntegerValue, # index here is id - 1
            BooleanValue, 
            StringValue,
        ]

PACK = [   
            BooleanValue, # Re-ordered for ensuring bools and ints go first
            IntegerValue,
            DoubleValue, 
            StringValue,
        ]

def pack_data(timestamp, value):
    for _type in PACK:
        if _type.valid_value(value):
            time_num = timestamp.timestamp()
            var = _type()        
            var.time = time_num
            var.value = value
            return var.pack()
    return None

def unpack_data(bytes):
    id = int(bytes[0]) - 1
    var = TYPES[id]()
    size = var.size()
    bytes = bytes[0:size]
    var.unpack(bytes)
    return var

DELIM = b':__:'
DALIM = b'_::_'
GET = b'get'
SET = b'set'
ALL = b'all'
CLEAR = b'clear'
OPEN = b'open'
CLOSE = b'close'
HELLO = b'hello'
KEY_ERR = b'key_err!'
MODE_ERR = b'mode_err!'
UNPACK_ERR = b'unpack_err'
SUCCESS = b'success!'
FILLER = b"??"
BUFSIZE = 1024

# Server -> client messages
SETSUCCESS = SUCCESS + DALIM + SET
ALLSUCCESS = SUCCESS + DALIM + SET
MODE_ERR_MSG = MODE_ERR + DALIM + MODE_ERR
KEY_ERR_MSG = KEY_ERR + DALIM + KEY_ERR
HELLO_FROM_SERVER = HELLO + DALIM + HELLO
CLOSED = SUCCESS + DALIM + CLOSE

# Client -> server messages
_open_cmd = OPEN + DELIM + FILLER + OPEN
_close_cmd = CLOSE + DELIM + FILLER + CLOSE
# _hello = HELLO + DELIM + HELLO
all_request = ALL + DELIM + FILLER + ALL

def pack_value(timestamp, value):
    pack = (timestamp,value)
    packed = pack_data(timestamp, value)
    if packed is not None:
        return packed
    return pickle.dumps(pack)

def unpack_value(bytes):
    args = bytes.split(DALIM)
    if args[0] == SUCCESS:
        if args[1] == ALL:
            return False, args[0], ALL
        return False, args[0], UNPACK_ERR
    # Server appends the size of the expected object to the front
    # so args[0][0:2] is the packaged expected size.
    key = args[0][2:].decode('utf-8')
    if key == KEY_ERR:
        return False, key, KEY_ERR
    data = args[1]
    # int_values = [x for x in data]
    # print(f"Number: {len(data)}")
    # print(int_values)
    if data == ALL:
        return False, key, ALL
    if data == KEY_ERR:
        return False, key, KEY_ERR
    elif data == MODE_ERR:
        return False, key, MODE_ERR
    try:
        try:
            value = pickle.loads(data)
            return True, key, value
        except Exception:
            # Not a pickle thing, lets try custom values
            unpacked = unpack_data(data)
            timestamp = datetime.fromtimestamp(unpacked.time)
            value = (timestamp, unpacked.value)
        return True, key, value
    except Exception as err:
        print(f'Error unpacking value {key}: {err}')
        print(bytes)
        return False, key, UNPACK_ERR

def check_set(_,  bytes):
    args = bytes.split(DALIM)
    data = args[0]
    return data == SUCCESS

def set_msg(key, timestamp, value):
    packed = str.encode(key) + DALIM + pack_value(timestamp, value)
    s = len(packed)
    size = struct.pack("<bb", int(s&31), int(s>>5))
    msg = SET + DELIM + size + packed
    # print([int(x) for x in msg])
    return msg

def get_msg(key):
    return GET + DELIM + FILLER + str.encode(key)

class BaseDataClient:
    def __init__(self, addr=ADDR, custom_port=False) -> None:
        self.connection = None
        self.addr = addr
        self.root_port = addr[1]
        self.reads = {}
        self.values = {}
        self.init_connection()
        if custom_port:
            self.select()

    def change_port(self, port):
        self.close()
        self.init_connection()
        self.addr = (self.addr[0], port)

    def init_connection(self):
        if self.connection is not None:
            self.close()
        self.connection = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.connection.settimeout(0.1)

    def close(self):
        if self.connection is not None:
            try:
                self.connection.sendto(_close_cmd, self.addr)
                self.connection.close()
                self.connection = None
            except:
                print('error closing?')
                pass

    def select(self):
        # This is the Python equivalent of the "connect" function in C++ version
        try:
            # ensure we are in the initial port
            # this also closes the connection if it existed
            self.change_port(self.root_port)
            self.connection.sendto(_open_cmd, self.addr)
            msgFromServer = self.connection.recvfrom(BUFSIZE)
            new_port = int(msgFromServer[0].decode("utf-8").replace("open:__:", "").replace("open_::_", ""))
            self.change_port(new_port)
            return True
        except Exception as err:
            print(f'error selecting? {err}')
            pass
        return False

    def get_value(self, key):
        _key = key
        if _key in self.reads:
            return self.reads.pop(_key) 

        bytesToSend = get_msg(key)
        n = 0
        unpacked = ''
        while n < 10:
            n += 1
            # Send to server using created UDP socket
            try:
                self.connection.sendto(bytesToSend, self.addr)
                msgFromServer = self.connection.recvfrom(BUFSIZE)
                success, _key2, unpacked = unpack_value(msgFromServer[0])

                if unpacked == KEY_ERR:
                    print(f"Error getting {key}")
                    return None
                # If we request too fast, things get out of order.
                # This allows caching the wrong reads for later
                if _key2 != _key:
                    n-=1
                    self.reads[_key2] = unpacked
                    continue
                if success:
                    return unpacked
                if unpacked == UNPACK_ERR:
                    print('resetting connection')
                    self.init_connection()
            except Exception as err:
                msg = f'Error getting value for {key}! {err}'
                if not 'timed out' in msg:
                    print(msg)
                pass
        print(f'failed to get! {key} {unpacked}')
        return None

    def get_bool(self, key, default=False):
        return self.get_var(key, default)
    
    def get_float(self, key, default=0):
        time, var = self.get_var(key, default)
        return time, float(var)
    
    def get_int(self, key, default=0):
        time, var = self.get_var(key, default)
        return time, int(var)

    def get_var(self, key, default=0):
        resp = self.get_value(key)
        if resp is None:
            return datetime.now(), default
        return resp[0], resp[1]

    def check_set(self, _, bytes):
        args = bytes.split(DALIM)
        data = args[0]
        if data == SUCCESS:
            return True
        # Otherwise might be a get value return
        _, _key2, unpacked = unpack_value(bytes[0])
        if _key2 in self.reads:
            print('error, duplate return!')
            return False
        self.reads[_key2] = unpacked
        return False

    def set_int(self, key, value, timestamp = None):
        return self.set_value(key, int(value), timestamp)

    def set_bool(self, key, value, timestamp = None):
        return self.set_value(key, bool(value), timestamp)
    
    def set_float(self, key, value, timestamp = None):
        return self.set_value(key, float(value), timestamp)

    def set_value(self, key, value, timestamp = None):
        if timestamp is None:
            timestamp = datetime.now()
        bytesToSend = set_msg(key, timestamp, value)
        if(len(bytesToSend) > 1024):
            print('too long!')
            return False
        try:
            self.connection.sendto(bytesToSend, self.addr)
            msgFromServer = self.connection.recvfrom(BUFSIZE)
            if self.check_set(key, msgFromServer[0]):
                return True
        except:
            pass
        return False

    def get_all(self):
        self.values = {}
        self.connection.sendto(all_request, self.addr)
        done = False
        while not done:
            try:
                msg = self.connection.recvfrom(BUFSIZE)
                sucess, key, unpacked = unpack_value(msg[0])
                if unpacked == UNPACK_ERR:
                    continue
                elif key == '':
                    continue
                elif sucess:
                    self.values[key] = unpacked
                elif unpacked == ALL:
                    # end of all send recieved
                    done = True
            except KeyboardInterrupt:
                pass
            except Exception as err:
                msg = f'Error getting value! {err}'
                print(msg)
                if 'timed out' in msg:
                    done = True
                    break
        return self.values