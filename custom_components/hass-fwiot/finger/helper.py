import socket
import binascii

from .log import finger_log
from .emp import finger_emp

def test_ping(ip):
    """
    Returns True if host responds to a ping request
    """
    import subprocess, platform
    # Ping parameters as function of OS
    ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1 -W 5"
    args = "ping " + " " + ping_str + " " + ip
    need_sh = False if  platform.system().lower()=="windows" else True
    # Ping
    return subprocess.call(args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=need_sh) == 0

def test_tcp(ip, port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(10) # fixed test
    res = client.connect_ex( (ip, port) )
    client.close()
    return res                        
        
class fk_class(object):
      def __init__(self, host, port, timeout=5, verbose=True):
          self.timeout = timeout
          '''connection timeout'''
          self.host = host
          ''' finger machine ip/address '''
          self.port = port
          '''finger machine port'''
          self.left = False
          ''' temporary: left bytes from previous read  '''
          self.count = 0
          self.log_count = 0
          ''' number of log read '''
          self.error = False
          ''' error message '''
          self.verbose = verbose
          ''' show debug info '''
          self.emps = finger_emp()
          ''' employee '''

      def send(self, exp, part1, num, part2):
          """
          send data to fk

          @exp expected size
          @part1 command part
          @num set number start from 0
          @part2 suffix part (session ?)
          """
          if self.verbose: print()
          # create connection...
          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          s.settimeout(self.timeout)
          s.connect_ex((self.host,self.port))

          # send request              
          req = part1 + bytearray([num]) + part2
          if self.verbose: print(binascii.hexlify(req))
          ss = s.send(req)
          if self.verbose: print("send size=%s" % ss)
          if self.verbose: print("expect size=%s" % exp)

          # receive response
          data0 = s.recv(exp)
          data = bytearray(data0)
          if self.verbose: print("receive size=%s" % len(data))
          
          return data

      def read_user(self, exp, part1, num, part2):
          '''
          read all user id

          @exp expected size
          @part1 command part
          @num set number start from 0
          @part2 suffix part (session ?)
          '''
          data = self.send(exp, part1, num, part2)
          # header part  
          # aa 55 01 01 00 00 00 00 06 00 55 aa
          i = 0; l = 12;  
          # h1 = data[i:l]

          i += l; l = 8  
          while (i+l) < len(data):   
               emp = int.from_bytes(data[i:i+3], byteorder='little')

               self.emps.idsk['%02d' % emp]=''
               i += l; l = 8            

      def read_username(self, exp, part1, num, part2):
          '''
          read user name

          @exp expected size
          @part1 command part
          @num set number start from 0
          @part2 suffix part (session ?)
          '''
          if num == 0: return
          
          data = self.send(exp, part1, num, part2)
          # header part  
          # aa 55 01 01 00 00 00 00 06 00 55 aa
          i = 0; l = 12;  
          h1 = data[i:l]
          if self.verbose: print(binascii.hexlify(h1))

          i += l; l = 10
          if self.verbose: print(binascii.hexlify(data[i:i+10]))
          self.emps.idsk['%02d' % num] = data[i:i+10].decode('utf-16').replace('\x00','')

      def read_log(self, exp, part1, num, part2):
          '''
          read log

          @exp expected size
          @part1 command part
          @num set number start from 0
          @part2 suffix part (session ?)
          '''
          data = self.send(exp, part1, num, part2)
          # header part  
          # aa 55 01 01 00 00 00 00 06 00 55 aa
          i = 0; l = 12;  
          h1 = data[i:l]

          # if has left from previous call  
          if self.left: 
             data = h1 + self.left + data[i+12:]  
             if self.verbose: print("head=%s" % binascii.hexlify(h1))
             if self.verbose: print("left=%s" % binascii.hexlify(self.left))
             if self.verbose: print("new data=%s" % binascii.hexlify(data[:20]))
             if self.verbose: print("data = h + left + new data")
             # reset previous left
             self.left = []

          # next field  
          i += l; l = 12

          # receive less than record              
          if len(data) < i+l:
             if self.verbose: print('uncomplete data..') 
             self.left = data[i:]
             if self.verbose: print(binascii.hexlify(h1))
             if self.verbose: print(binascii.hexlify(data[i:]))
             return

          log = finger_log()
          log.read(data[i:i+l])
          # no left, append log
          if not log.left:
             if self.verbose: print(log)
             self.log_count += 1
             self.emps.add(log)
          else:
             self.left = log.left   

          # still has record data 
          while (i+l) < len(data):                            
            #next record 
            i += l; l = 12  
            log = finger_log()
            log.read(data[i:i+l])
            if log.empty:
               break

            if not log.left:
               if self.verbose: print(log)
               self.log_count += 1
               self.emps.add(log)
            else:
               self.left = log.left 
               if self.verbose: print("found left=%s" % binascii.hexlify(self.left))
               break

          if self.verbose: print("count emp=%s" % self.emps.count)
          self.count += 1
          return
            
