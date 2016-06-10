#!/usr/bin/python
#-*- coding:utf-8 -*- 
# Author: chuanqi.tan # gmail # com ( http://chuanqi.name )

import requests
import json
import time
import sys


class ExmailWrapper:
    ''' 对QQ 企业邮箱openApi的包装 '''
    def __init__(self, client_id, client_secret):
        self.API_POINT = 'http://openapi.exmail.qq.com:12211/openapi'

        self.client_id = client_id
        self.client_secret = client_secret
        self._token = ''
        self._token_expire = 0
        self._token_usetime = 0


    def _callAPI(self, url, p):
        try:
            if not 'access_token' in p:
                p['access_token'] = self._getAccessToken()
                if p['access_token'] == '':
                    # cannot get valid access token
                    return False

            if 'alias' in p:
                p['alias'] = self._getActualEmail(p['alias'])
            #print url, p
            #print p['access_token']

            r = requests.post(self.API_POINT + url, params=p)
            #time.sleep(0.01)
            #print r
            #sys.stdout.flush()
            if r.ok:
                try: 
                    j = r.json() 
                    #print 'rtv: ', j
                    return j
                except Exception:
                    return True
            else:
                return False
        except Exception, ex:
            print 'EXCEPTION in _callAPI:', ex
            return False


    def _getActualEmail(self, user_email):
        ''' 
        处理别名 
        一些接口，如 getUserInfo 使用别名会提示找不到用户，在这里可以做个简单的映射
        不建议使用别名作为账号名
        '''
        alias = {
                'tanchuanqi@deepai.com' : 'tan@deepai.com'
                }
        return alias[user_email] if user_email in alias else user_email


    def _getAccessToken(self):
        ''' 获取访问key '''
        if self._token == '' or self._token_usetime >= 1 or self._token_expire <= time.time():
            # 不在有效期
            self._token = ''
            self._token_expire = 0
            self._token_usetime = 0

            p = { 
                    'grant_type' : 'client_credentials', 
                    'client_id' : self.client_id,
                    'client_secret' : self.client_secret
                }
            r = requests.post('https://exmail.qq.com/cgi-bin/token', params = p)

            if r.ok:
                r = r.json()
                self._token = r['access_token']
                self._token_expire = int(time.time()) + int(r['expires_in']) / 1000 / 2

        self._token_usetime += 1
        #print "TOKEN: ", self._token, ' EXPIRE: ', self._token_expire
        #sys.stdout.flush()
        return self._token


    def _getUserAuthkey(self, user_email):
        ''' 用access_token换取用户授权key '''
        j = self._callAPI('/mail/authkey', {'alias' : user_email})
        print '_getUserAuthkey:', j
        #sys.stdout.flush()
        if j and 'auth_key' in j:
            return j['auth_key']
        else:
            return False


    def getEmployeesListInGroup(self, group_name):
        j = self._callAPI('/partyuser/list', {'partypath' : group_name})
        print j
        if j and 'List' in j:
            return j['List']
        else:
            return []
        

    def getUserInfo(self, user_email):
        ''' 获取用户信息 '''
        return self._callAPI('/user/get', {'alias' : user_email} )


    def getOnekeyLoginUrl(self, user_email):
        ''' 一键登陆 '''
        authkey = self._getUserAuthkey(user_email)
        #print 'AUTHKEY: ', authkey
        #sys.stdout.flush()
        if authkey != "":
            onekey_login_url = "https://exmail.qq.com/cgi-bin/login?fun=bizopenssologin&method=bizauth\
&agent={0}&user={1}&ticket={2}".format(
                    self.client_id, user_email, authkey)
            return onekey_login_url
        else:
            return False


    def getUnreadEmailNumber(self, user_email):
        ''' 得到未读邮件数目 '''
        j = self._callAPI('/mail/newcount', {'alias' : user_email})
        if j and 'NewCount' in j:
            return j['NewCount']
        else:
            return ""


    def addUser(self, user_email, cn_name, pwd):
        ''' 添加用户 '''
        p = { 
                'alias' : user_email, 
                'name' : cn_name,
                'action' : 2, 
                'password' : pwd, 
                'md5' : 0,
                'opentype' : 1
            }
        return self._callAPI('/user/sync', p)


    def delUser(self, user_email):
        ''' 删除用户 '''
        p = { 
                'alias' : user_email, 
                'action' : 1
            }
        return self._callAPI('/user/sync', p)


    def updateUserStatus(self, user_email, set_active):
        ''' 更新用户状态，冻结、启用账号 ''' 
        p = { 
                'alias' : user_email, 
                'action' : 3,
                'opentype' : 1 if set_active else 2
            }
        return self._callAPI('/user/sync', p)


    def updateUserPassword(self, user_email, new_pwd):
        ''' 更新密码 '''
        p = { 
                'alias' : user_email, 
                'action' : 3, 
                'password' : new_pwd, 
                'md5' : 0 
            }
        return self._callAPI('/user/sync', p)

    def checkUser(self, email):
        ''' 检查账号是否可用
            Type: -1:帐号名无效, 0:帐号名没被占用, 1:主帐号名, 2:别名帐号, 3:邮件群组帐号。
        '''
        p = { 'email' : email }
        return self._callAPI('/user/check', p)

