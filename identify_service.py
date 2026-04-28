#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Copyright (c) [Zachary]
本代码受版权法保护，未经授权禁止任何形式的复制、分发、修改等使用行为。
Author:Zachary
'''
import rospy
import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import time
from sensor_msgs.msg import Image as ROSImage
from std_srvs.srv import Trigger, TriggerResponse
import json
import openai
from openai import OpenAI
import base64
import sys
import numpy as np
import os
import os.path, time


def imgmsg_to_cv2(img_msg):
    dtype = np.dtype("uint8")  # Hardcode to 8 bits...
    dtype = dtype.newbyteorder('>' if img_msg.is_bigendian else '<')
    image_opencv = np.ndarray(shape=(img_msg.height, img_msg.width, 3), dtype=dtype, buffer=img_msg.data)

    # If the byte order is different between the message and the system.
    if img_msg.is_bigendian == (sys.byteorder == 'little'):
        image_opencv = image_opencv.byteswap().newbyteorder()

    # Convert to BGR if the encoding is not already BGR
    if img_msg.encoding == "rgb8":
        image_opencv = cv2.cvtColor(image_opencv, cv2.COLOR_RGB2BGR)
    elif img_msg.encoding == "mono8":
        image_opencv = cv2.cvtColor(image_opencv, cv2.COLOR_GRAY2BGR)
    elif img_msg.encoding != "bgr8":
        rospy.logerr("Unsupported encoding: %s", img_msg.encoding)
        return None

    return image_opencv

def cv2_to_imgmsg(cv_image):
    img_msg = ROSImage()
    img_msg.height = cv_image.shape[0]
    img_msg.width = cv_image.shape[1]
    img_msg.encoding = "bgr8"
    img_msg.is_bigendian = 0
    img_msg.data = cv_image.tobytes()
    img_msg.step = len(img_msg.data) // img_msg.height  # That double line is actually integer division, not a comment
    return img_msg
# 豆包大模型客户端初始化
client = OpenAI(
    api_key="",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)
def top_view_shot(image_msg):
    global detect
    img_bgr = imgmsg_to_cv2(image_msg)
    detect = rospy.get_param('/detect', 255)
    
    if detect == 1:
        save_path = '/home/abot/FN5I30/src/abot_vlm/temp2/vl_now.jpg'
        cv2.imwrite(save_path, img_bgr)
        # 标记文件已写入完成
        rospy.set_param('/image_ready', True)  
        rospy.loginfo(f'图片已保存，可读取')
        
        rospy.set_param('/detect', 255)
        cv2.waitKey(1)

def doubao_vision_api(
PROMPT='''
图中可能有一种水果，水果种类包含：香蕉、苹果、梨、葡萄这四种，若存在这四种水果中的一种，请输出这个水果的名字；你只能输出这个水果的名字,而不能输出任何其他的文字;如果图中有大写的数字5或者6,请输出"5"或者"6",若数字都和水果不存在，请输出"无"
例如:图片中有"伍",你输出"5",图片里有葡萄,你输出"葡萄",如果都有,你优先输出水果名称.''', img_path='/home/abot/FN5I30/src/abot_vlm/temp2/vl_now.jpg'):
    '''
    豆包视觉语言多模态大模型API
    '''
    # 编码为base64数据
    with open(img_path, 'rb') as image_file:
        image = 'data:image/jpeg;base64,' + base64.b64encode(image_file.read()).decode('utf-8')
        rospy.loginfo(f'实际读取路径: {img_path}')

    valid_results = ["香蕉", "苹果", "梨", "葡萄", "无","5","6"]
    
    while True:
        # 向豆包大模型发起请求
        completion = client.chat.completions.create(
            model="ep-20250809144646-4tfsq",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image
                            }
                        }
                    ]
                },
            ],
            extra_body={
                "thinking": {
                    "type": "disabled"  # 关闭深度思考能力
                }
            }
        )

        # 解析大模型返回结果
        result_str = completion.choices[0].message.content.strip()
        
        rospy.loginfo('豆包大模型调用成功！')
        rospy.loginfo(result_str)

        # 检查结果是否为指定的汉字
        if result_str in valid_results:
            return result_str
        else:
            print('结果不符合要求，重新识别...')

# 在服务调用中：
def handle_fruit_detection(req):
    # 等待文件准备就绪（最多等2秒，避免无限阻塞）
    timeout = 2.0  # 超时时间
    start_time = time.time()
    while not rospy.get_param('/image_ready', False):
        if time.time() - start_time > timeout:
            rospy.logerr('等待图片超时，可能未正确保存')
            return TriggerResponse(success=False, message="超时")
        time.sleep(0.05)  # 短间隔轮询
    
    # 读取前先标记为"不可读取"，避免被覆盖
    rospy.set_param('/image_ready', False)
    result = doubao_vision_api()
    return TriggerResponse(success=True, message=result)

def main():
    global detect
    rospy.init_node('identify_node', anonymous=True)
    rospy.Subscriber('/usb_cam/image_raw', ROSImage, top_view_shot)
    rospy.loginfo('豆包视觉大模型模块导入成功！')
    rospy.loginfo('准备识别...')
    # 从参数服务器获取detect的值
    detect = rospy.set_param('/detect', 255)
    
    # 创建服务服务器
    s = rospy.Service('fruit_detection', Trigger, handle_fruit_detection)
    
    rospy.spin()

if __name__ == '__main__':
        # ... 其他初始化 ...
    rospy.set_param('/image_ready', False)  # 初始状态：未准备好
    main()