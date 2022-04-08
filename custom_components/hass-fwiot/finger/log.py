import binascii

class finger_log():
    unknown = ''
    ''' unknown '''
    id = ''
    ''' userid '''
    user = ''
    ''' user code'''
    second = 0
    ''' second'''
    #timeh = ''
    ''' time in hex'''
    time = ''
    ''' time (string)'''    
    empty = False
    ''' this record empty? '''
    left = []
    ''' remaining of read '''
    
    def __str__(self):
        #return '{unknow:%s,id:%s,sec:%02d,time:%s,time:%s:%02d' % (self.unknown,self.id,self.second,self.timeh,self.time,self.second)
        return 'id:%s,time:%s:%02d' % (self.id,self.time,self.second)

    def hex_to_user(self, h):
        '''
        convert hex to user number

        @h hex string
        '''
        bh = bin(h)[2:]
        return '%02d' % int(bh[:8], 2)

    def hex_to_time(self, h):
        '''
        convert hex to date + time string

        @h hex string
        '''
        ys = 1964
        bh = bin(h)[2:]
        yy = bh[:6]
        mm = bh[8:12]
        dd = bh[19:24]
        MM = bh[24:30]
        HH = bh[30:32] + bh[16:19]       
        return '%02d/%02d/%s %02d:%02d' % (int(dd,2),int(mm,2),int(yy,2) + ys,int(HH,2),int(MM,2))          

    def read(self, data):
        '''
        read hex string record
        
        @data data 

        example

        02000000 010141 17 e6a1397d

        0a000000 01010a 13 e6a1b935
        '''
        if len(data) < 12: 
           self.left = data 
           return
        if str(binascii.hexlify(data)) == 'b\'000000000000000000000000\'':
           self.empty = True
           return 

        #print(binascii.hexlify(data[:4]))
        #self.unknown = binascii.hexlify(data[:4])
        self.id = self.hex_to_user(int.from_bytes(data[:4], byteorder='little'))
        self.second = data[7:8][0]
        #self.timeh = binascii.hexlify(data[8:])
        self.time = self.hex_to_time(int.from_bytes(data[8:], byteorder='big'))
        return