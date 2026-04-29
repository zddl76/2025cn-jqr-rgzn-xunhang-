#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) [Zachary]
本代码受版权法保护，未经授权禁止任何形式的复制、分发、修改等使用行为。
Author:Zachary
'''
import rospy
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import os
import base64
# 新增服务相关导入
from std_srvs.srv import Trigger, TriggerResponse
from openai import OpenAI

dmt=0

# 豆包大模型客户端初始化
client = OpenAI(
    api_key="",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

def get_bbox(array):
    "将结果中的position信息的四个点的坐标信息转换"
    x1 = array[0][0]
    y1 = array[0][1]
    pt1 = (int(x1), int(y1))
    x2 = array[2][0]
    y2 = array[2][1]
    pt2 = (int(x2), int(y2))
    return pt1, pt2

def dealImg(img):
    b, g, r = cv2.split(img)
    img_rgb = cv2.merge([r, g, b])
    return img_rgb

def create_blank_img(img_w, img_h):
    # 将图像宽度调整为原来的1.5倍
    img_w = int(img_w * 1.5)
    blank_img = np.ones(shape=[img_h, img_w, 3], dtype=np.uint8) * 255
    blank_img = Image.fromarray(blank_img)
    return blank_img

def Draw_OCRResult(blank_img, pt1, pt2, text):
    # 确保 blank_img 是 PIL.Image 对象
    if isinstance(blank_img, np.ndarray):
        blank_img = Image.fromarray(blank_img)
    
    draw = ImageDraw.Draw(blank_img)
    draw.rectangle([pt1, pt2], outline=(255, 255, 0), width=3)
    # 注意：字体路径需根据实际环境修改
    fontStyle = ImageFont.truetype("/home/abot/FN5I30/src/ocr_detect/ChineseFonts/simsun.ttc", size=21, encoding="utf-8")
    (x, y) = pt1
    draw.text((x+5, y+5), text=text, fill=(0, 0, 0), font=fontStyle)
    blank_img = np.asarray(blank_img)
    return blank_img

def doubao_ocr_api(img_path):
    '''
    豆包视觉语言多模态大模型OCR API
    '''
    try:
        # 检查图片文件是否存在
        if not os.path.exists(img_path):
            rospy.logerr("图片文件不存在: %s", img_path)
            return None, None

        # 编码为base64数据
        with open(img_path, 'rb') as image_file:
            image = 'data:image/jpeg;base64,' + base64.b64encode(image_file.read()).decode('utf-8')

        # 使用严格的提示词
        PROMPT = '''请严格识别图片中的所有文字，按照以下要求输出：
1. 只输出图片中实际存在的文字内容
2. 不要任何标点符号
3. 保持文字原有的顺序和格式
4. 如果图片中没有文字，输出"无文字"
5. 不要对识别结果进行任何修饰或改写
6.不允许输出思考过程或者其他解释
7.如果在识别出文字的末尾有一个意义不明的大写汉字，请不要输出这个字。
8.如果图片上的文字是两行显示的,请把它改为一行显示
例如：图片上的汉字是“乾坤八卦，
变化无穷。
陆”，你输出“乾坤八卦变换无穷”'''

        # 向豆包大模型发起请求
        completion = client.chat.completions.create(
            model="",
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
                    "type": "disabled"
                }
            }
        )

        # 解析大模型返回结果
        result_str = completion.choices[0].message.content.strip()
        rospy.loginfo('豆包大模型OCR调用成功！')
        
        # 为了兼容原有的显示逻辑，我们创建一个模拟的结果结构
        # 这里将整个识别结果作为一个"区域"返回
        simulated_result = [{
            "text": result_str,
            "position": [[0, 0], [100, 0], [100, 30], [0, 30]]  # 模拟的位置信息
        }]
        
        return result_str, simulated_result
        
    except Exception as e:
        rospy.logerr("豆包大模型OCR调用失败: %s", str(e))
        return None, None

def process_ocr(img_path):
    print("调用process_ocr成功")
    im = cv2.imread(img_path)
    if im is None:
        rospy.logwarn("Failed to load image: %s", img_path)
        return None
    
    img_h, img_w, _ = im.shape
    blank_img = create_blank_img(img_w, img_h)
    
    # 使用豆包大模型进行OCR识别
    ocr_text, result = doubao_ocr_api(img_path)
    
    if ocr_text is None or result is None:
        return None
    
    # 保留原有的绘图和显示逻辑
    for temp in result:
        pt1, pt2 = get_bbox(temp["position"])
        blank_img = Draw_OCRResult(blank_img, pt1, pt2, temp["text"])
    images = np.concatenate((im, blank_img), axis=1)
    
    # 显示图片（改为非阻塞显示，避免卡住服务）
    rospy.loginfo("显示图片前")
    #cv2.imshow('OCR Result', images)
    rospy.loginfo("显示图片后")
    cv2.waitKey(1)  # 1ms非阻塞等待
    
    # 保存结果图片
    base_name = os.path.basename(img_path)
    file_name, _ = os.path.splitext(base_name)
    save_path = '/home/abot/FN5I30/src/ocr_detect/result/OCR_result_{}.jpg'.format(file_name)
    global dmt
    dmt=dmt+1
    print("dmt=%d"%dmt)
    cv2.imwrite(save_path, images)
    
    return ocr_text

# 新增服务回调函数
def handle_ocr_detection(req):
    # 从参数服务器获取图片路径（与原逻辑保持一致）
    img_path = rospy.get_param('/image_path', "/home/abot/FN5I30/src/ocr_detect/image/11.jpg")
    rospy.loginfo("Processing OCR for image: %s", img_path)
    print("正在调用process_ocr")
    
    # 调用OCR处理函数
    ocr_result = process_ocr(img_path)
    rospy.set_param('/image_path', "/home/abot/FN5I30/src/ocr_detect/image/11.jpg")
    
    if ocr_result is not None:
        return TriggerResponse(success=True, message=ocr_result)
    else:
        return TriggerResponse(success=False, message="OCR processing failed")

def ocr_detect():
    rospy.init_node('ocr_detect', anonymous=True)
    # 注册服务（核心修改：创建/ocr_detection服务）
    s = rospy.Service('ocr_detection', Trigger, handle_ocr_detection)
    rospy.loginfo("OCR detection service is ready.")
    
    # 保持节点运行
    rospy.spin()

if __name__ == '__main__':
    try:
        ocr_detect()
    except rospy.ROSInterruptException:
        cv2.destroyAllWindows()  # 退出时关闭窗口
