from .helper import fk_class

class finger_reader():
    host = '192.168.1.67'
    ''' default = 192.168.1.67 '''
    port = 5005
    ''' default = 5005 '''
    timeout = 5
    ''' default = 5 '''
    mode = 'all' 
    ''' all/new default = all'''
    verbose = False
    ''' show debug info'''

    def read_log(self):
        '''
        read log data from finger print
        '''
        # a4
        d6mode = 0xa4 #all
        if self.mode == 'new':
           d6mode = 0xa1 #new

        # command
        d61 = bytes([0x55,0xaa,0x00,d6mode,0x00,0x00,0x00,0x00,0x62,0x08])
        # suffix
        d63 = bytes([0x00,0x00,0x04,0x05,0x00])

        v6 = fk_class(self.host, self.port, timeout=self.timeout, verbose=self.verbose)

        i = 0
        c = 0
        v6.read_log(1024, d61, i, d63)

        while c < v6.log_count:
            c = v6.log_count
            if self.verbose: print('reading set %s' % (i+1))
            i += 1
            v6.read_log(1024, d61, i, d63)
        
        return v6.emps.tojson()


    def read_user(self):
        '''
        read user data from finger print
        '''
        # command
        # 97b8
        d61 = bytes([0x55,0xaa,0x00,0x97,0xb8,0x00,0x00,0x00,0x03,0x00])
        # suffix
        d63 = bytes([0x00,0xb8,0x00,0x06,0x00])

        v6 = fk_class(self.host, self.port, timeout=self.timeout, verbose=self.verbose)
        i = 0
        c = 0
        d = v6.read_user(1024, d61, i, d63)
        
        d71 = bytes([0x55,0xaa,0x00,0xc7])
        # suffix
        d73 = bytes([0x00,0x00,0x00,0x00,0x0e,0x00,0x05,0x00])

        for each in v6.emps.idsk:
            bno = int(each).to_bytes(4,byteorder='little')
            v6.read_username(1024, d71, int(bno[0]), bno[1:] + d73)

        return v6.emps.idsk  