# -- coding: utf-8 --
import sys
import subprocess
import os
import re
import json
import requests
import urllib
from urllib import parse
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
import time
import click
from utils import filter_name
sep = os.sep

headers = {
    'user-agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
}


class DouyinUser:
    def __init__(self,url, func=None):
        self.name = url
        self.func = func
        self.url = url

        self.total = 1
        self.index = 0

    def callback(self, title=None):
        if self.func:
            self.func({
                'type': 'data',
                'name': self.name,
                'total': self.total,
                'index': self.index,
                'title': title,
            })
    def callbackMsg(self, msg, color=None):
        if self.func:
            self.func({
                'type': 'msg',
                'msg': msg,
                'color': color,
            })

    def printMsg(self, msg, color=None):
        if self.func:
            self.callbackMsg(msg, color)
        else:
            print(msg)

    def done(self,msg):
        self.total = 1
        self.index = 1
        self.callback(msg)

    def getParams(self,url):

        signHtml = os.path.abspath('.') + sep + 'sign.html'

        rep = requests.get(url,headers=headers, allow_redirects=False,verify=False)
        location = rep.headers['Location']
        if '/share/user/' not in location:
            return None


        params = parse.parse_qs(parse.urlparse(location).query)
        sec_uid = params['sec_uid'][0]
        rep = requests.get(location,headers=headers)
        uid = re.findall('uid: "(.*)"', rep.text)[0]
        dytk = re.findall("dytk: '(.*)'", rep.text)[0]


        option = ChromeOptions()
        option.add_argument('headless') # 设置option
        option.add_experimental_option('excludeSwitches', ['enable-automation'])
        driver = Chrome(options=option)
        driver.get(signHtml)
        

        agent = driver.execute_script('return window.navigator.userAgent;') 
        _signature = driver.execute_script('return _bytedAcrawler.sign('+uid+')')
        code = _signature[-2:-1]
        if not code.isdigit():
            code = chr(ord(code) + 1)
        else:
            code = int(code) + 1
        _signature = _signature[:len(_signature) - 2] + str(code) + _signature[-1]

        driver.quit()

        return {
            'sec_uid':sec_uid,
            'uid':uid,
            'dytk':dytk,
            '_signature':_signature,
            'agent':agent
        }

    def cheDir(self,dir):
        if not os.path.exists(dir):
            os.makedirs(dir)


    def run(self) -> dict:

        data = {}

        self.callback('获取参数和签名.....')
        params = self.getParams(self.url)
        if params == None:
            self.printMsg("获取失败",color="err")
            return data
        #print(params)

        max_cursor = 0
        headers["user-agent"] = params["agent"]
        results = []

        self.callback('拉取视频列表')
        while(1):
            try:
                url = f'https://www.iesdouyin.com/web/api/v2/aweme/post/?sec_uid={params["sec_uid"]}&count=50&max_cursor={max_cursor}&aid=1128&_signature={params["_signature"]}&dytk={params["dytk"]}'
                rep = requests.get(url,headers=headers)
                jsons = json.loads(rep.text)
                if jsons["has_more"] == True:
                    _list = jsons["aweme_list"]
                    if _list:
                        max_cursor = jsons["max_cursor"]
                        for item in _list:
                            results.append({
                                'author':{
                                    'nickname':item['author']['nickname'],
                                    'custom_verify':item['author']['custom_verify'],
                                    'signature':item['author']['signature'],
                                    'uid':item['author']['uid'],
                                    'avatar':item['author']['avatar_larger']['url_list']
                                },
                                'desc':item['desc'],
                                'statistics':item['statistics'],
                                'video':{
                                    'duration':item['video']['duration'],
                                    'url':item['video']['download_addr']['url_list']
                                }
                            })
                        time.sleep(0.5)
                    else:
                        time.sleep(1)
                else:
                    break
            except BaseException:
                break
        
        videos = []
        for item in results:
            url = item["video"]["url"][0]
            videos.append({
                'url':url.replace('watermark=1','watermark=0'),
                'name':filter_name(item["desc"]),
                'headers':{
                    'Accept':'*/*',
                    'Accept-Encoding':'gzip, deflate, br',
                    'Connection':'keep-alive',
                    'User-Agent':'PostmanRuntime/7.24.1'
                }
            })
        
        return {
            'videos':videos
        }


def get(url: str,  func=None) -> dict:
    douyin =  DouyinUser(url,func)

    return douyin.run()
