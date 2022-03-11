#!/usr/bin/python
# -*- coding: UTF-8 -*-

import traceback
import sys

from apn_functions import *

# *********** 你的基本信息 **************
username = 'xxxxxxxxxx'
password = 'password'
mail = 'mail@mail.com'
authorized_code = "mailIMAPcode"
# *********** 你的基本信息 - 需要修改的到此为止 **************

# 使用命令行 只能用0/2/4个参数
args = sys.argv
args_length = len(args) - 1  # 第一个是文件名
if args_length == 0:
    # 使用默认参数
    pass
elif args_length == 1:
    print('参数数量不足, 至少为2')
    exit(0)
elif args_length == 2:
    username = args[1]
    password = args[2]

elif args_length == 3:
    print('参数数量异常')
    exit(0)
elif args_length == 4:
    username = args[1]
    password = args[2]
    mail = args[3]
    authorized_code = args[4]
elif args_length > 4:
    print('参数数量异常')
    exit(0)

is_random_alter = True          
is_constant_school = False      #是否固定在学校 False/True

user = PostUser(username, password, mail, authorized_code)

post_success = False
try:
    user.login()
    user.get_infos(random_alter=is_random_alter, constant_in_school=is_constant_school)
    post_success = user.post()

    send_str = '{}\n\nHeader:\n{}\n\nData:\n{}'.format(user.post_rep.text,
                                                       str(user.post_header),
                                                       str(user.post_data))
    # 如果今天已经填报过则不发送邮件, 退出
    if (user.post_rep.json()['e'] == 1) & (user.post_rep.json()['m'] == '今天已经填报了'):
        exit(0)

except Exception as e:
    send_str = traceback.format_exc()

# 构造邮件标题
today = datetime.datetime.now().strftime('%Y%m%d')
mail_header = '{} {}打卡情况 {}'.format(today,
                                    username + ' ',
                                    post_success)

user.send_email(send_str, mail_header)
