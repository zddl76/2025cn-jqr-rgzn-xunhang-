#!/usr/bin/env python
'''
Copyright (c) [Zachary]
本代码受版权法保护，未经授权禁止任何形式的复制、分发、修改等使用行为。
Author:Zachary
'''
import rospy
from abot_vlm.srv import LLMQuery, LLMQueryResponse
import openai
from openai import OpenAI

pre_PROMPT = '根据提供的谜语信息猜数字,只输出最终的答案，例如"1","2"等等,不允许输出思考过程或者其他东西'

# 豆包大模型客户端初始化（与豆包文件保持一致）
client = OpenAI(
    api_key="",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

def handle_llm_query(req):
    '''
    处理LLM查询请求
    '''
    last_PROMPT = req.query
    
    # 使用豆包大模型
    MODEL = ""  # 豆包模型标识符
    
    while True:
        # 访问豆包大模型API
        PROMPT = pre_PROMPT + last_PROMPT
        completion = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": PROMPT}],
            extra_body={
                "thinking": {
                    "type": "disabled"  # 关闭深度思考能力
                }
            }
        )
        result = completion.choices[0].message.content.strip()
        rospy.loginfo(f"豆包大模型响应: {result}")
        
        # 检查结果是否为数字且是个位数
        if result.isdigit() and len(result) == 1:
            return LLMQueryResponse(result)

def llm_server():
    '''
    LLM服务端
    '''
    rospy.init_node('llm_server')
    s = rospy.Service('llm_query', LLMQuery, handle_llm_query)
    rospy.loginfo("豆包大模型服务端准备就绪，可以处理查询。")
    rospy.spin()

if __name__ == "__main__":
    llm_server()
