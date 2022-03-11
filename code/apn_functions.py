import ast
import random

import requests
import re

import smtplib
from email.mime.text import MIMEText
from email.header import Header

import time
import datetime


class MyException(Exception):
    """自定义异常类"""
    pass


class LoginException(MyException):
    """登陆时的异常"""

    def __init__(self, err_info):
        self.err_info = err_info

    def __str__(self):
        return "登陆异常\n" + self.err_info


class UserInfoError(LoginException):
    """账号or密码错误"""

    def __init__(self, err_info):
        self.err_info = err_info

    def __str__(self):
        return '账号或密码错误' + self.err_info


def get_new_info(default_rep):
    """获取新信息"""
    pattern = re.compile(r'(?<=var def = ){.*}')
    new_infos = pattern.search(default_rep.text)
    return ast.literal_eval(new_infos[0])


def get_old_info(default_rep):
    """获取旧信息"""
    pattern = re.compile(r'(?<=oldInfo: ){.*}')
    old_infos = pattern.search(default_rep.text)
    return ast.literal_eval(old_infos[0])


class PostUser:
    """打卡成员类"""

    def __init__(self, username, password, mail='', authorized_code=''):
        self.username = username
        self.password = password

        self.post_data = dict()
        self.initialize_post_data()
        self.post_rep = ''
        self.post_header = ''
        self.login_url = "https://app.nwafu.edu.cn/uc/wap/login/check"
        self.default_url = 'https://app.nwafu.edu.cn/ncov/wap/default'
        self.post_url = "https://app.nwafu.edu.cn/ncov/wap/default/save"
        self.cookies = dict()
        self.school_geo_info = dict()
        self.initialize_school_geo_info()

        self.mail = mail
        self.authorized_code = authorized_code

        self.current_time = str(int(time.time()))

    # 获取cookies
    def get_cookies(self):
        """通过username和password获取cookies, 返回字典格式的cookies"""
        data = {'username': self.username, 'password': self.password}
        login_rep = requests.post(url=self.login_url, data=data)

        if login_rep.json()['e'] != 0:
            if login_rep.json()['m'] == '账号或密码错误':
                raise UserInfoError(login_rep.text)
            else:
                raise LoginException(login_rep.text)

        self.cookies = login_rep.cookies.get_dict()
        return self.cookies

    def _get_default_header(self):
        """从cookies中更新cookie并将header进行返回"""
        default_header = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8, application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': 'eai-sess=xxxxxx; UUkey=xxxxxx',
            'referer': "https://app.nwafu.edu.cn/uc/wap/login?redirect=https://app.nwafu.edu.cn/ncov/wap/default",
            'sec-ch-ua': '" Not;A Brand";v="99", "Microsoft Edge";v="97", "Chromium";v="97"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69'
        }
        default_cookies = 'eai-sess={}; UUkey={}'.format(self.cookies['eai-sess'],
                                                         self.cookies['UUkey'])
        default_header['cookie'] = default_cookies

        return default_header

    def get_default_rep(self):
        """获取default页面信息"""
        default_rep = requests.get(self.default_url,
                                   headers=self._get_default_header())
        return default_rep

    def initialize_school_geo_info(self):
        self.school_geo_info = {
            'address': '陕西省咸阳市杨陵区李台街道西北农林科技大学南校区',
            'geo_api_info': {
                "type": "complete", "info": "SUCCESS", "status": 1,
                "dEa": "jsonp_097852_",
                "position":
                    {"Q": 34.26386, "R": 108.07225, "lng": 108.07225, "lat": 34.26386},
                "message": "Get ipLocation success.Get address success.", "location_type": "ip",
                "accuracy": 'null', "isConverted": 'true',
                "addressComponent":
                    {"citycode": "0910", "adcode": "610403", "businessAreas": [],
                     "neighborhoodType": "", "neighborhood": "", "building": "",
                     "buildingType": "", "street": "后稷路", "streetNumber": "5号",
                     "country": "中国", "province": "陕西省", "city": "咸阳市",
                     "district": "杨陵区", "township": "李台街道"},
                "formattedAddress": "陕西省咸阳市杨陵区李台街道西北农林科技大学南校区",
                "roads": [], "crosses": [], "pois": []},
            'area': '陕西省 咸阳市 杨陵区',
            'province': '陕西省',
            'city': '咸阳市'
        }
        return self.school_geo_info

    def initialize_post_data(self):
        """
        初始化默认post_data
        zgfxdq: 0       # 是否中高风险地区 1-yes, 0-no  default:0
        mjry: 0         # 密接人员 1-yes, 0-no
        csmjry: 0       # 近14日内本人/共同居住者是否去过疫情发生场所（市场、单位、小区等）或与场所人员有过密切接触？，1-yes，0-no default:0
        tw: 2           # 体温  1:36°C以下,      2:36-36.5,  3:36.5-36.9,
                        #       4:36.9-37.3,    5:37.3-38,  6:38-38.5,
                        #       7:38.5-39,      8:39-40,    9:40以上
        sfcxtz: 0       # 今日是否出现发热、乏力、干咳、呼吸困难等症状？   1-yes, 0-no  default:0
        sfjcbh: 0       # 今日是否接触无症状感染/疑似/确诊人群？        1-yes, 0-no default:0
        sfcxzysx: 0     # 是否有任何与疫情相关的， 值得注意的情况？     1-yes, 0-no default:0
        qksm:           # （疫情）情况说明   字符串，default: (空，什么都不填)
        sfyyjc: 0       # 是否到相关医院或门诊检查？(出现症状后的选项<-> when sfcxtz=1)   1-yes, 0-no default:0
        jcjgqr: 0       # 检查结果属于以下哪种情况？(到医院检查后<-> when sfyyjc=1)      1-疑似感染, 2-确诊感染, 3-其他
        remark:         # 其他信息 字符串 default:(空，什么都不填)
        address: 陕西省咸阳市杨陵区李台街道西北农林科技大学南校区      # 当前地理位置format版(formattedAddress)
        geo_api_info:   # 地理位置信息（from高德api），dEa为调用的脚本号（随机生成即可，每次都不固定）
        {"type":"complete","info":"SUCCESS","status":1,"dEa":"jsonp_097852_",
        "position":{"Q":34.26386,"R":108.07225,"lng":108.07225,"lat":34.26386},
        "message":"Get ipLocation success.Get address success.",
        "location_type":"ip","accuracy":null,"isConverted":true,
        "addressComponent":{"citycode":"0910","adcode":"610403",
        "businessAreas":[],"neighborhoodType":"","neighborhood":"","building":"",
        "buildingType":"","street":"后稷路","streetNumber":"5号",
        "country":"中国","province":"陕西省","city":"咸阳市",
        "district":"杨陵区","township":"李台街道"},
        "formattedAddress":"陕西省咸阳市杨陵区李台街道西北农林科技大学南校区","roads":[],"crosses":[],"pois":[]
        }
        area: 陕西省 咸阳市 杨陵区   #province + ' ' + city + ' ' + district   , 如果在国外则 '国外 国外 国外''
        province: 陕西省
        city: 咸阳市
        sfzx: 1         # 是否在校 1-yes 0-no default:看情况吧
        sfjcwhry: 0     # 是否接触危害人员（猜测）（此处仅在之前的info中出现，不是单独获取的像前面一样的选项）      1-yes 0-no default:0
        sfjchbry: 0     # 是否接触患病人员（猜测）（此处仅在之前的info中出现，不是单独获取的像前面一样的选项）      1-yes 0-no default:0
        sfcyglq: 0      # 是否处于隔离期？      1-yes 0-no default:0
        gllx:           # 隔离场所 (处于隔离期时 <-> when sfcyglq=1)  字符串 '学校家属院'/'学校集中隔离点'/'陕西校外居住地'/'陕西外地区集中隔离点'    default:空
        glksrq:         # 隔离开始时间          日期类型      default:空
        jcbhlx:         # 接触人群类型（接触了危害人群 <-> when sfjcbh==1) 字符串 '疑似'/'确诊'  default:空
        jcbhrq:         # 接触人群事件（接触了危害人群 <-> when sfjcbh==1) 日期 default:空
        bztcyy:         # 当前地点与上次不在同一城市，原因如下(when isremoved = 1)   1-其他，2-探亲，3-旅游，4-回家
        sftjhb: 0       # 未知    default:0
        sftjwh: 0       # 未知    default:0
        jcjg:           # 检测结果 default:空
        date: 20201008  # 当前日期 fmt:'%YY%mm%dd'
        uid: 12345      # 个人uid
        created: 1536301606     #创建本页面时间 时间戳(from 1970)
        jcqzrq:         # 未知    default:空
        sfjcqz:         # 未知    default:空
        szsqsfybl: 0    # 未知    default:0
        sfsqhzjkk: 0    # 未知    default:0
        sqhzjkkys:      # 未知    default:空
        sfygtjzzfj: 0   # 未知    default:0
        gtjzzfjsj:      # 未知    default:空
        fxyy: 返校原因   #返校原因 字符串（textarea）
        id: 24633806    # 不知道哪弄的 可能是总打卡次数
        gwszdd:         # 未知    default:空
        sfyqjzgc:       # 未知    default:空
        jrsfqzys:       # 未知    default:空
        jrsfqzfy:       # 未知    default:空
        ismoved: 0      # 未知    default:0
        """
        self.post_data = {
            'zgfxdq': 0, 'mjry': 0, 'csmjry': 0, 'tw': 0, 'sfcxtz': 0, 'sfjcbh': 0, 'sfcxzysx': 0,
            'qksm': 0, 'sfyyjc': 0, 'jcjgqr': 0, 'remark': 0, 'address': 0, 'geo_api_info': 0, 'area': 0,
            'province': 0, 'city': 0, 'sfzx': 0, 'sfjcwhry': 0, 'sfjchbry': 0, 'sfcyglq': 0, 'gllx': 0,
            'glksrq': 0, 'jcbhlx': 0, 'jcbhrq': 0, 'bztcyy': 0, 'sftjhb': 0, 'sftjwh': 0, 'jcjg': 0, 'date': 0,
            'uid': 0, 'created': 0, 'jcqzrq': 0, 'sfjcqz': 0, 'szsqsfybl': 0, 'sfsqhzjkk': 0, 'sqhzjkkys': 0,
            'sfygtjzzfj': 0, 'gtjzzfjsj': 0, 'fxyy': 0, 'id': 0, 'gwszdd': 0, 'sfyqjzgc': 0, 'jrsfqzys': 0,
            'jrsfqzfy': 0, 'ismoved': 0
        }
        return self.post_data

    def construct_post_data(self, old_infos, new_infos, constant_in_school):
        """从old_info和new_info构造今天的打卡信息,
        constant_in_school 为是否固定打卡在学校 True/False"""
        old_keys = ['address', 'area', 'province', 'city']  # from old keys:['address','area','province',city']
        # update from old_infos
        for oldkey in old_keys:
            self.post_data[oldkey] = old_infos[oldkey]

        # update from new_infos
        for new_key in self.post_data.keys():
            if new_key not in old_keys:
                self.post_data[new_key] = new_infos.get(new_key)

        # 将ismoved显式补0
        self.post_data['ismoved'] = 0

        # 更改created
        self.post_data['created'] = self.current_time

        # 更改日期为当天日期
        self.post_data['date'] = datetime.datetime.now().strftime('%Y%m%d')

        # 固定在学校位置打卡（确认），将学校信息写入
        if constant_in_school:
            self.post_data.update(self.school_geo_info)

        return self.post_data

    def randomly_alter_post_data(self):
        """随机修改post_data
        具体: 经纬度度的第三位小数之后，定位的脚本号
        """
        # 先对self.post_data中的true和false进行处理，将其替换为字符串
        if (':true,' in self.post_data['geo_api_info']):
            self.post_data['geo_api_info'] = self.post_data['geo_api_info'].replace(':true,', ':"true",')
        elif (':false,' in self.post_data['geo_api_info']):
            self.post_data['geo_api_info'] = self.post_data['geo_api_info'].replace(':false,', ':"false",')

        # 再尝试对post_data进行转化为dict
        t_postd = ast.literal_eval(self.post_data['geo_api_info'])
        # 脚本号
        if 'dEa' in self.post_data.get('geo_api_info'):
            t_postd['dEa'] = 'jsonp_{0:06d}_'.format(random.randint(10000, 999999))
        # 经纬度
        bais = round((random.random() * 2 - 1) / 1000, random.randint(6, 8))  # [-1,1]
        rnd_int = random.randint(5, 8)

        t_postd['position']['Q'] = round(t_postd['position']['Q'] + bais, rnd_int)
        t_postd['position']['R'] = round(t_postd['position']['R'] - bais, rnd_int)
        t_postd['position']['lng'] = t_postd['position']['R']
        t_postd['position']['lat'] = t_postd['position']['Q']

        self.post_data['geo_api_info'] = str(t_postd)
        return self.post_data

    def _get_post_header(self):
        """构造post的header"""
        # 去掉zg_did和zg_
        # uukey和eai-sess可以通过login获得 eai-sess期限大概在一个月，uukey大概在1年
        header = {'Accept': 'application/json, text/javascript, */*q=0.01',
                  'Accept-Encoding': 'gzip, deflate, br',
                  'Accept-Language': 'zh-CN,zh;q=0.9',
                  'Connection': 'keep-alive',
                  'Content-Length': '2108',
                  'Content-Type': 'application/x-www-form-urlencoded charset=UTF-8',
                  'Cookie':
                      'eai-sess=xxxxxx;\
                      UUkey=xxxxxx;\
                      Hm_lvt_48b682d4885d22a90111e46b972e3268=xxxxxx;\
                      Hm_lpvt_48b682d4885d22a90111e46b972e3268=xxxxxxx',
                  'Host': 'app.nwafu.edu.cn',
                  'Origin': "https://app.nwafu.edu.cn",
                  'Referer': "https://app.nwafu.edu.cn/ncov/wap/default",
                  'sec-ch-ua': '"Chromium";v="97", "Microsoft Edge";v="97", ";Not A Brand";v="99"',
                  'sec-ch-ua-mobile': '?0',
                  'sec-ch-ua-platform': '"Windows"',
                  'Sec-Fetch-Dest': 'empty',
                  'Sec-Fetch-Mode': 'cors',
                  'Sec-Fetch-Site': 'same-origin',
                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69',
                  'X-Requested-With': 'XMLHttpRequest'
                  }
        # 更新header
        cookies_fmt = "eai-sess={}; UUkey={}; \
         Hm_lvt_48b682d4885d22a90111e46b972e3268={}; \
         Hm_lpvt_48b682d4885d22a90111e46b972e3268={}".format(
            self.cookies['eai-sess'],
            self.cookies['UUkey'],
            self.post_data['created'],
            self.post_data['created'])
        header['Cookie'] = cookies_fmt

        # 更新content-length, 1100是补足（也不知道哪里缺的）
        header['Content-Length'] = str(len(str(self.post_data).encode('utf8')) + 1100)

        self.post_header = header

        return header

    def post_infos(self):
        """将信息进行提交"""
        post_success = False
        self.post_rep = requests.post(url=self.post_url, data=self.post_data,
                                      headers=self._get_post_header())
        if self.post_rep.json()['e'] == 0:
            post_success = True
        return post_success

    def _send_email(self, send_str, mail_header):
        """将打卡信息发送到执行邮箱"""
        message = MIMEText(send_str)  # 邮件内容
        message['From'] = Header('post_robort')  # 邮件发送者名字
        message['To'] = Header('robort')  # 邮件接收者名字
        message['Subject'] = Header(mail_header)  # 邮件主题

        mail = smtplib.SMTP_SSL("imap.qq.com", 465)
        mail.connect("smtp.qq.com")  # 连接 qq 邮箱
        mail.login(self.mail, self.authorized_code)  # 账号和授权码
        mail.sendmail(self.mail, [self.mail], message.as_string())  # 发送账号、接收账号和邮件信息
        mail.quit()

    def login(self):
        """用户调用函数，登录并获取cookies"""
        self.get_cookies()

    def get_infos(self, random_alter=True, constant_in_school=False):
        """获取昨日与今日信息并构造今日打卡信息,
        random_alter: 是否随机修改post_data
        constant_in_school: 是否把信息写死在学校"""
        default_rep = self.get_default_rep()
        old_infos = get_old_info(default_rep)
        new_infos = get_new_info(default_rep)
        self.construct_post_data(old_infos, new_infos, constant_in_school)

        if random_alter:
            try:
                self.randomly_alter_post_data()
            except Exception:
                pass
                # random不了就算辽~ 问题不大

    def post(self):
        """将信息进行提交"""
        post_success = self.post_infos()
        return post_success

    def send_email(self, send_str, mail_header):
        """发送邮件"""
        self._send_email(send_str, mail_header)
