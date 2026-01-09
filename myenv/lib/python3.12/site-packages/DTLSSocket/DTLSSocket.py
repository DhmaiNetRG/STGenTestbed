import socket, time
from . import dtls

DTLS_CLIENT = dtls.DTLS_CLIENT
DTLS_SERVER = dtls.DTLS_SERVER

class DTLSSocket():
  app_data = None
  connected = dict()
  lastEvent = None
  inbuffer = None
  outancbuff = None
  _sock = None
  
  def __init__(self, pskId=b"Client_identity", pskStore={b"Client_identity": b"secretPSK"}, logLevel = dtls.DTLS_LOG_EMERG):
    self._sock = socket.socket(family=socket.AF_INET6, type=socket.SOCK_DGRAM)
    self._sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_RECVPKTINFO, 1)
    self.d = dtls.DTLS(read=self._read, write=self._write, event=self._event, pskId=pskId, pskStore=pskStore)
    dtls.setLogLevel(logLevel)
    #print("Init done:", self._sock, self.d)
  
  def __del__(self):
    self.connected.clear()
    self._sock.close()
    del self.d
    del self._sock
  
  def _read(self, x, y):
    if self.app_data:
      print("_read: lost", x, y)
    self.app_data = (y, x)
    return len(y)

  def _write(self, x, y):
    try:
      if self.outancbuff:
        ret = self._sock.sendmsg([y,], self.outancbuff[0], self.outancbuff[1], x)
        self.outancbuff = None
        return ret
      else:
        return self._sock.sendto(y, x)
    except OSError:
      print("_sock already dead...\ncan't send", x, y)
      return -1
  
  def _event(self, level, code):
    #print("-- Event:", hex(code), "--")
    self.lastEvent = code
  
  def _isMC(self, addr):
    if isinstance(addr, str):
      addr = socket.inet_pton(socket.AF_INET6, addr)
    return addr[0] == 0xFF
  
  def sendmsg(self, data, ancdata=[], flags=0, address=None, cnt=10):
    #print("sendmsg:", address, data, ancdata)
    data = b''.join(data)
    
    if len(address) == 2:
      address = (address[0], address[1], 0, 0)
    
    if address and address not in self.connected:
      addr, port, flowinfo, scope_id = address
      
      if self._isMC(addr):
        print("unknown MC", address, "not in", self.connected)
        return 0 #Not Client in MC-Group, aiocoap wantes to answer MC-PUT?
      
      #print("connecting...", address)
      timeout = self.gettimeout()
      self.settimeout(1.0)
      
      self.lastEvent = None
      s = self.d.connect(addr, port, flowinfo, scope_id)
      if not s:
        raise Exception("can't connect")
      while self.lastEvent != 0x1de and cnt>0:
        try:
          indata = self.recvmsg(1200, cnt=1)
        except (BlockingIOError, InterruptedError, socket.timeout):
          pass
        else:
          self.inbuffer = indata
          cnt = 0
        cnt -= 1
      
      self.settimeout(timeout)
      
      if self.lastEvent == 0x1de:
        if address not in self.connected:
          self.connected[address] = s
        #else:
          #print("sendmsg, client already connected", s, self.connected[address])
        self.lastEvent = 0
      else:
        raise BlockingIOError
    
    if self.outancbuff:
      print("ERROR: self.outancbuff is not None!")
    self.outancbuff = (ancdata, flags)
    return self.d.write(self.connected[address], data)
    
  def recvmsg(self, buffsize, ancbufsize=100, flags=0, cnt=3):
    data = None
    ancdata = None
    src = None
    #timeout = self.gettimeout()
    while not self.app_data and cnt > 0:
      if self.inbuffer:
        #print("Data from buffer")
        data, ancdata, flags, src = self.inbuffer
        self.inbuffer = None
      else:
        #print("Buffer empty, call _sock.recvmsg")
        data, ancdata, flags, src = self._sock.recvmsg(buffsize, ancbufsize, flags)
      
      dst = 0
      mc = False
      for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if (cmsg_level == socket.IPPROTO_IPV6 and cmsg_type == socket.IPV6_PKTINFO):
              if cmsg_data[0] == 0xFF:
                dst = (socket.inet_ntop(socket.AF_INET6, cmsg_data[:16]), self._sock.getsockname()[1])
                print("Debug: dst =", dst)
                mc = True
      if mc:
        ret = self.d.handleMessageAddr(dst[0], dst[1], data)
        if ret != 0:
          print("handleMessageAddr returned", ret)
          raise BlockingIOError
      else:
        addr, port = src[:2]
        addr = addr.split("%")[0]
        #print("recvmsg call handleMessageAddr with:", addr, port)
        ret = self.d.handleMessageAddr(addr, port, data)
        if ret != 0:
          print("handleMessageAddr returned", ret)
          raise BlockingIOError
        if self.lastEvent == 0x1de:
          if (addr, port, 0, 0) not in self.connected:
            self.connected[(addr, port, 0, 0)] = dtls.Session(addr, port, 0, 0)
          #else:
            #print("recvmsg, client already connected")
      cnt -= 1
    
    #self.settimeout(timeout)
    if self.app_data:
      data, addr = self.app_data
      self.app_data = None
      return data, ancdata, flags, addr
    else:
      raise BlockingIOError
  
  def __getattr__(self, attr):
    #print(attr)
    return getattr(self._sock, attr)
  
  def close(self):
    pass
