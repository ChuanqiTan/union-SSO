#! /usr/bin/python
#-*- coding:utf-8 -*- 
# 注意 python-ldap 模块只接受str，所以如果是unicode都要转换成str

import sys, os
import ldap
import ldap.modlist


class LdapWrapper:
    def __init__(self, options):
        self.LDAP_HOST        = options['LDAP_HOST']
        self.LDAP_PORT        = options['LDAP_PORT']
        self.LDAP_BASE        = options['LDAP_BASE']
        self.LDAP_PEOPLE_BASE = options['LDAP_PEOPLE_BASE']
        self.LDAP_BIND        = options['LDAP_BIND']
        self.LDAP_PASS        = options['LDAP_PASS']
        self.MAIL_POSTFIX     = options['MAIL_POSTFIX']


    def _getAdminConn(self):
        conn = ldap.initialize('ldap://{0}:{1}'.format(self.LDAP_HOST, self.LDAP_PORT))
        conn.set_option(ldap.OPT_REFERRALS, 0)  
        conn.protocol_version = ldap.VERSION3 
        conn.simple_bind_s(self.LDAP_BIND, self.LDAP_PASS)

        return conn


    def _encodeUTF8toStr(self, string):
        if isinstance(string, unicode):
            return string.encode('utf-8')
        else:
            return string


    def retrieve(self, base, search_filter):
        def formatPeopleRecord(rs):
            rs = rs[0]
            rs[1]['dn'] = [rs[0],]
            return rs[1]

        try:
            conn = self._getAdminConn()
            searchScope = ldap.SCOPE_SUBTREE
            retrieveAttributes = None  

            ldap_result_id = conn.search(base, searchScope, search_filter, retrieveAttributes)  
            result_set = []  

            while 1:  
                result_type, result_data = conn.result(ldap_result_id, 0)  
                if(result_data == []):  
                    break  
                else:  
                    if result_type == ldap.RES_SEARCH_ENTRY:  
                        result_set.append(result_data)  

            return [formatPeopleRecord(r) for r in result_set]
        except ldap.LDAPError, e:
            print e

        return None


    ##################### END OF PRIVATE OPERATOR ########################


    def addPeople(self, eng_first_name, eng_last_name, cn_first_name, cn_last_name, pwd):
        # 注意 python-ldap 模块只接受str，所以如果是unicode都要转换成str
        eng_first_name  = self._encodeUTF8toStr(eng_first_name)
        eng_last_name   = self._encodeUTF8toStr(eng_last_name)
        cn_first_name   = self._encodeUTF8toStr(cn_first_name)
        cn_last_name    = self._encodeUTF8toStr(cn_last_name)
        if eng_first_name == '' or eng_last_name == '' or cn_first_name == '' or cn_last_name == '':
            return False

        cn = '{0} {1}'.format(eng_first_name, eng_last_name)
        dn = "cn={0},{1}".format(cn, self.LDAP_PEOPLE_BASE)
        uid = eng_first_name + eng_last_name
        mail = uid + self.MAIL_POSTFIX
        givenName = cn_first_name
        sn = cn_last_name
        userPassword = pwd
        objectClass = ['top', 'inetOrgPerson']

        try: 
            conn = self._getAdminConn()
            modlist = ldap.modlist.addModlist({ #格式化目录项，除对象类型要求必填项外， 
                'cn': [cn], #其它项可自由增减 
                'uid' : [uid],
                'mail': [mail], 
                'givenName' : [givenName],
                'sn' : [sn],
                'userPassword' : [userPassword],
                'objectClass': objectClass })
            #print modlist #显示格式化数据项，格式化后是一个元组列表 
            #print dn
            conn.add_s(dn, modlist) #调用add_s方法添加目录项
            return True
        except ldap.LDAPError, e: 
            print e 
            return False
        except Exception, e:
            print e
            return False


    def delPeople(self, email):
        try:
            dn = self.getDnByEmail(email)
            if dn:
                self._getAdminConn().delete_s(dn)
                return True
        except:
            pass

        return False


    def update(self, email, update_items):
        '''
        sometime you need to encode not-ascii char by "str(request.POST.get(item, "").encode('utf-8'))"
        '''
        try:
            dn = self.getDnByEmail(email)
            conn = self._getAdminConn()

            ops_list = []
            for k, v in update_items.items():
                if v == "":
                    ops_list.append((ldap.MOD_DELETE, k, None))
                else:
                    ops_list.append((ldap.MOD_REPLACE, k, v))
            print ops_list
            conn.modify_s(dn, ops_list)

            return True
        except ldap.LDAPError, e: 
            print "Update failed: ",
            print e
            return False


    def getAllPeople(self):
        search_filter = "(objectClass=inetOrgPerson)"
        people_list = self.retrieve(self.LDAP_PEOPLE_BASE, search_filter)
        return people_list


    def getPeopleByEmail(self, email):
        search_filter = "(mail={0})".format(email)
        result_set = self.retrieve(self.LDAP_PEOPLE_BASE, search_filter)
        if result_set != None and len(result_set) == 1: # because email are indentify
            return result_set[0]
        return None


    def getDnByEmail(self, email):
        people = self.getPeopleByEmail(email)
        if people:
            return people['dn'][0]
        else:
            return None


    def checkPassword(self, email, pwd):
        people = self.getPeopleByEmail(email)
        if people:
            return people['userPassword'][0] == pwd
        else:
            return False


    def changePassword(self, email, old_pwd, new_pwd):
        if self.checkPassword(email, old_pwd):
            if self.update(email, {'userPassword' : new_pwd}):
                return True
        return False


    def updatePeopleStatus(self, email, set_active):
        if self.update(email, {'st' : 'True' if set_active else 'False'}):
            return True
        else:
            return False
