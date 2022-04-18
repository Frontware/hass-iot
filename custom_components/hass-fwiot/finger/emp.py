class finger_emp():
      data = {}
      ''' keypair of userid:[finger_log] '''
      ids = []
      ''' list of all user '''
      idsk = {}
      ''' keypair of userid:user code '''

      def add(self, log):
          '''
          add log in employee
          @log finger_log object
          '''
          usid = str(log.id)
          if not usid in self.data:
             self.data[usid] = {'logs': []}
             self.ids.append(usid)

          log.user = self.idsk.get(usid, usid)  
          self.data[usid]['logs'].append(log)
      
      @property
      def count(self):
          '''
          number of user
          '''
          return len(self.data.keys())

      def __str__(self):          
          st = '''--------\nid : count\n--------\n'''
          stc = ''
          self.ids.sort()
          for each in self.ids:
              emplogs = self.data[each]['logs']
              lastrec = emplogs[-1:][0]
              st += stc + '%s : %s, last log = %s' % (lastrec.user or '000', len(emplogs), lastrec.time)
              stc = '\n'
          return st    
      
      def tojson(self):
          ret = {}
          self.ids.sort()
          for each in self.ids:
              emplogs = self.data[each]['logs']
              lastrec = emplogs[-1:][0]
              ret[lastrec.user or '000'] = '%s:%s' % (lastrec.time, lastrec.second)
          return ret  
