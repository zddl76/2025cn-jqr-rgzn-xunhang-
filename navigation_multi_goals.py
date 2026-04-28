#!/usr/bin/env python2
# -*- coding:utf-8 -*-
# Copyright(C)[WCXC] 本代码受版权法保护,未经授权禁止任何形式的复制、分发、修改等使用行为。
# Company:WCXC

# 导入ROS相关模块
import rospy
import actionlib
from actionlib_msgs.msg import GoalStatus
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg import PoseWithCovarianceStamped
from tf_conversions import transformations
from math import pi

# 导入标准消息类型
from std_msgs.msg import String
from ar_track_alvar_msgs.msg import AlvarMarkers
from geometry_msgs.msg import Twist
from geometry_msgs.msg import Point

# 导入其他标准库
import os
import time

# 导入服务相关模块
from std_srvs.srv import Trigger, TriggerRequest
from abot_vlm.srv import LLMQuery
from tts_audio.srv import TTS, TTSRequest

# 音频文件路径
calculate_result1_music = "/home/abot/FN5I30/mp3/计算结果为1线索为葡萄.mp3"
calculate_result2_music = "/home/abot/FN5I30/mp3/计算结果为2线索为数字5.mp3"
calculate_result3_music = "/home/abot/FN5I30/mp3/计算结果为3线索为香蕉.mp3"
calculate_result4_music = "/home/abot/FN5I30/mp3/计算结果为4线索为二维码7.mp3"
calculate_result5_music = "/home/abot/FN5I30/mp3/计算结果为5线索为苹果.mp3"
calculate_result6_music = "/home/abot/FN5I30/mp3/计算结果为6线索为二维码8.mp3"
calculate_result7_music = "/home/abot/FN5I30/mp3/计算结果为7线索为梨子.mp3"
calculate_result8_music = "/home/abot/FN5I30/mp3/计算结果为8线索为数字6.mp3"

music1_path = "/home/abot/FN5I30/mp3/已检索到第一条信息.mp3"
music2_path = "/home/abot/FN5I30/mp3/已检索到第二条信息.mp3"
music3_path = "/home/abot/FN5I30/mp3/已检索到第三条信息.mp3"
music4_path = "/home/abot/FN5I30/mp3/已检索到第四条信息.mp3"
music_end_path = "/home/abot/FN5I30/mp3/已到达终点,比赛结束.mp3"

# 全局变量
find_id = 0
id = 0
result_received = False
identification = None
ocr_text = ""
clue = 1
calculate_result = 0
points = [
    [2, 3, 3],
    [4, 5, 6],
    [7, 8, 9],
    [10, 11, 12]
]

class navigation_demo:
    """导航演示类"""

    def __init__(self):
        """初始化导航演示类"""
        # ROS节点初始化
        self.set_pose_pub = rospy.Publisher('/initialpose', PoseWithCovarianceStamped, queue_size=5)
        self.arrive_pub = rospy.Publisher('/voicewords', String, queue_size=10)
        self.find_sub = rospy.Subscriber("/object_position", Point, self.find_cb)
        self.ar_sub = rospy.Subscriber('/ar_pose_marker', AlvarMarkers, self.ar_cb)
        self.move_base = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.move_base.wait_for_server(rospy.Duration(60))
        self.pub = rospy.Publisher("/cmd_vel", Twist, queue_size=1000)
        rospy.Subscriber('result', String, self.math_calculate)

        # 服务客户端初始化
        self.fruit_detection_service = rospy.ServiceProxy('/fruit_detection', Trigger)
        self.ocr_detection_service = rospy.ServiceProxy('/ocr_detection', Trigger)
        self.llm_query = rospy.ServiceProxy('llm_query', LLMQuery)
        self.tts_service = rospy.ServiceProxy('tts_service', TTS)

    def tts_client(self, text):
        """TTS客户端"""
        if not text:
            return
            
        processed_text = text.strip()
        if len(processed_text) > 100:
            processed_text = processed_text[:100] + "…"

        rospy.wait_for_service("tts_service")
        try:
            request = TTSRequest(processed_text)
            # response = self.tts_service(request)
        except rospy.ServiceException as e:
            rospy.loginfo("Service call failed: %s", str(e))

    def llm_client(self, query):
        """LLM客户端"""
        if not query:
            return "No query"

        rospy.wait_for_service('llm_query')
        try:
            response = self.llm_query(str(query))
            return str(response.result)
        except rospy.ServiceException as e:
            rospy.logerr("Service call failed: %s", e)
            return "Error"

    def call_ocr_detection_service(self):
        """调用OCR检测服务"""
        rospy.wait_for_service('/ocr_detection')
        try:
            request = TriggerRequest()
            response = self.ocr_detection_service(request)
            rospy.loginfo("OCR识别结果: %s", response.message)
            return response.message
        except rospy.ServiceException as e:
            rospy.logerr("OCR服务调用失败: %s", e)
            return None

    def call_fruit_detection_service(self):
        """调用水果检测服务"""
        rospy.wait_for_service('/fruit_detection')
        try:
            request = TriggerRequest()
            response = self.fruit_detection_service(request)
            
            if response.message == "5" or response.message == "6":
                global find_id
                find_id = int(response.message)
                
            rospy.loginfo("水果识别结果: %s", response.message)
            return response.message
        except rospy.ServiceException as e:
            rospy.logerr("水果检测服务调用失败: %s", e)
            return "unknown"

    def rotate(self):
        """控制机器人旋转"""
        time1 = 0
        msg = Twist()
        msg.linear.x = 0
        msg.linear.y = 0
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = 1.0  # 旋转速度

        max_time = 8  # 旋转持续时间

        while time1 <= max_time:
            self.pub.publish(msg)
            rospy.sleep(0.1)
            time1 += 1

    def ar_cb(self, data):
        """AR标记回调函数"""
        global id
        for marker in data.markers:
            id = marker.id

    def math_calculate(self, msg):
        """数学计算回调函数"""
        global calculate_result, result_received, identification

        rospy.loginfo("接收到结果: %s", msg.data)
        calculate_result = int(msg.data)

        result_mapping = {
            1: ("葡萄", calculate_result1_music),
            2: ("5", calculate_result2_music),
            3: ("香蕉", calculate_result3_music),
            4: ("7", calculate_result4_music),
            5: ("苹果", calculate_result5_music),
            6: ("8", calculate_result6_music),
            7: ("梨", calculate_result7_music),
            8: ("6", calculate_result8_music)
        }

        if calculate_result in result_mapping:
            identification, music_path = result_mapping[calculate_result]
            if music_path and os.path.exists(music_path):
                os.system('mplayer %s' % music_path)
        else:
            identification = "unknown"
            rospy.logwarn("未知的计算结果: %s", calculate_result)

        result_received = True

    def find_cb(self, data):
        """目标位置回调函数"""
        pass

    def set_pose(self, p):
        """设置初始位姿"""
        if not p or len(p) < 3:
            return False

        x, y, th = p[0], p[1], p[2]
        pose = PoseWithCovarianceStamped()
        pose.header.stamp = rospy.Time.now()
        pose.header.frame_id = 'map'
        pose.pose.pose.position.x = x
        pose.pose.pose.position.y = y

        q = transformations.quaternion_from_euler(0.0, 0.0, th / 180.0 * pi)
        pose.pose.pose.orientation.x = q[0]
        pose.pose.pose.orientation.y = q[1]
        pose.pose.pose.orientation.z = q[2]
        pose.pose.pose.orientation.w = q[3]

        self.set_pose_pub.publish(pose)
        return True

    def _done_cb(self, status, result):
        """导航完成回调函数"""
        rospy.loginfo("导航完成! 状态: %d", status)
        arrive_str = "arrived to target point"
        self.arrive_pub.publish(arrive_str)

    def _active_cb(self):
        """导航激活回调函数"""
        rospy.loginfo("[导航] 导航已激活")

    def _feedback_cb(self, feedback):
        """导航反馈回调函数"""
        pass

    def goto(self, p):
        """导航到目标点"""
        if not p or len(p) < 3:
            return False

        rospy.loginfo("[导航] 前往 %s", p)
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = 'map'
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = p[0]
        goal.target_pose.pose.position.y = p[1]

        q = transformations.quaternion_from_euler(0.0, 0.0, p[2] / 180.0 * pi)
        goal.target_pose.pose.orientation.x = q[0]
        goal.target_pose.pose.orientation.y = q[1]
        goal.target_pose.pose.orientation.z = q[2]
        goal.target_pose.pose.orientation.w = q[3]

        self.move_base.send_goal(goal, self._done_cb, self._active_cb, self._feedback_cb)
        result = self.move_base.wait_for_result(rospy.Duration(60))

        if not result:
            rospy.loginfo("导航超时")
            self.move_base.cancel_goal()
            return False
        else:
            state = self.move_base.get_state()
            if state == GoalStatus.SUCCEEDED:
                rospy.loginfo("成功到达目标点 %s", p)
                return True
        return False

    def mission(self, point):
        """执行任务"""
        global ocr_text, clue, find_id, id

        self.goto(goals[point])
        find_id = 0
        id = 0
        rospy.set_param('/detect', 1)

        self.detect = self.call_fruit_detection_service()
        rospy.loginfo("线索识别结果: %s", self.detect)

        print("find_id=%d, id=%d" % (find_id, id))

        detection_success = (self.detect == identification or 
                           str(find_id) == str(identification) or 
                           str(id) == str(identification))

        if detection_success:
            rospy.set_param('/image_path', '/home/abot/FN5I30/src/abot_vlm/temp2/vl_now.jpg')
            ocr_detect = self.call_ocr_detection_service()
            rospy.loginfo("OCR识别结果: %s", ocr_detect)

            if ocr_detect:
                ocr_text += str(ocr_detect)

                ocr_music_mapping = {
                    "万物肇始混沌初开": "/home/abot/FN5I30/mp3/万物肇始混沌初开.mp3",
                    "独尊无对至高至纯": "/home/abot/FN5I30/mp3/独尊无对至高至纯.mp3",
                    "首出庶物群伦之先": "/home/abot/FN5I30/mp3/首出庶物群伦之先.mp3",
                    "元亨利贞乾德资始": "/home/abot/FN5I30/mp3/元亨利贞乾德资始.mp3",
                    "阴阳相生对立统一": "/home/abot/FN5I30/mp3/阴阳相生对立统一.mp3",
                    "偶数为双相辅相成": "/home/abot/FN5I30/mp3/偶数为双相辅相成.mp3",
                    "天地分仪乾坤并立": "/home/abot/FN5I30/mp3/天地分仪乾坤并立.mp3",
                    "雌雄有别万物化醇": "/home/abot/FN5I30/mp3/雌雄有别万物化醇.mp3",
                    "鼎足而立稳若泰山": "/home/abot/FN5I30/mp3/鼎足而立稳若泰山.mp3",
                    "声成宫商角音相随": "/home/abot/FN5I30/mp3/声成宫商角音相随.mp3",
                    "棋分三局胜负乃定": "/home/abot/FN5I30/mp3/棋分三局胜负乃定.mp3",
                    "道生一二三生万物": "/home/abot/FN5I30/mp3/道生一二三生万物.mp3",
                    "方位俱全东西南北": "/home/abot/FN5I30/mp3/方位俱全东西南北.mp3",
                    "时序更迭春夏秋冬": "/home/abot/FN5I30/mp3/时序更迭春夏秋冬.mp3",
                    "典籍流芳诗书礼易": "/home/abot/FN5I30/mp3/典籍流芳诗书礼易.mp3",
                    "德行维邦礼义廉耻": "/home/abot/FN5I30/mp3/德行维邦礼义廉耻.mp3",
                    "音阶初成宫商角徵": "/home/abot/FN5I30/mp3/音阶初成宫商角徵.mp3",
                    "味蕾所感酸甜苦辣": "/home/abot/FN5I30/mp3/味蕾所感酸甜苦辣.mp3",
                    "方位居中四方来朝": "/home/abot/FN5I30/mp3/方位居中四方来朝.mp3",
                    "经典流传诗书礼易": "/home/abot/FN5I30/mp3/经典流传诗书礼易.mp3",
                    "天地四方宇宙尽藏": "/home/abot/FN5I30/mp3/天地四方宇宙尽藏.mp3",
                    "阴阳各三律吕调阳": "/home/abot/FN5I30/mp3/阴阳各三律吕调阳.mp3",
                    "人体脏腑运转有常": "/home/abot/FN5I30/mp3/人体脏腑运转有常.mp3",
                    "文化六艺君子必修": "/home/abot/FN5I30/mp3/文化六艺君子必修.mp3",
                    "星辰北斗天枢指引": "/home/abot/FN5I30/mp3/星辰北斗天枢指引.mp3",
                    "音律七声韵律悠长": "/home/abot/FN5I30/mp3/音律七声韵律悠长.mp3",
                    "周天星宿四象三垣": "/home/abot/FN5I30/mp3/周天星宿四象三垣.mp3",
                    "彩虹色阶赤橙黄绿": "/home/abot/FN5I30/mp3/彩虹色阶赤橙黄绿.mp3",
                    "乾坤八卦变化无穷": "/home/abot/FN5I30/mp3/乾坤八卦变化无穷.mp3",
                    "方位俱全四正四隅": "/home/abot/FN5I30/mp3/方位俱全四正四隅.mp3",
                    "节令分野立春惊蛰": "/home/abot/FN5I30/mp3/节令分野立春惊蛰.mp3",
                    "乐器八音金石丝竹": "/home/abot/FN5I30/mp3/乐器八音金石丝竹.mp3"
                }

                for text, music_path in ocr_music_mapping.items():
                    if text in ocr_detect and os.path.exists(music_path):
                        rospy.loginfo("播放特定音频: %s", text)
                        os.system('mplayer %s' % music_path)
                        break

            self.play_clue_music(clue)
            self.tts_client(ocr_detect)
            clue += 1

    def play_clue_music(self, clue_number):
        """播放线索音乐"""
        music_mapping = {
            1: music1_path,
            2: music2_path,
            3: music3_path,
            4: music4_path
        }

        if clue_number in music_mapping:
            music_path = music_mapping[clue_number]
            if os.path.exists(music_path):
                os.system('mplayer %s' % music_path)

    def recognize(self, p):
        """执行识别任务"""
        global find_id, id

        for i in range(3):
            self.mission(p[i])
            rospy.loginfo("执行完成%d点", i)

            recognition_success = (self.detect == identification or 
                                 str(find_id) == str(identification) or 
                                 str(id) == str(identification))

            if recognition_success:
                rospy.loginfo("在位置%s识别到正确图像,跳过剩余图像", str(i + 1))
                return True

        return False

if __name__ == "__main__":
    """主函数"""
    rospy.init_node('navigation_demo', anonymous=True)

    # 从参数服务器获取目标点参数
    goalListx = rospy.get_param('~goalListx', "0,-0.138,-0.211,-0.135,-0.098,-1.344,-2.638,-2.665,-2.784,-2.818,-2.896,-1.499,-0.313,-0.945,-0.873,-2.080,-2.112,-1.514")
    goalListY = rospy.get_param('~goalListY', '0,-0.430,-1.616,-2.849,-2.813,-2.937,-3.060,-2.849,-1.679,-0.475,-0.541,-0.354,-0.236,-1.018,-2.274,-2.339,-1.092,-1.675')
    goalListYaw = rospy.get_param('~goalListYaw', "0,5.990,7.990,11.496,-86.832,-84.427,-80.095,-170.723,-179.002,-179.228,94.496,96.679,99.248,90.347,91.446,91.396,91.546,89.596")

    # 解析目标点列表
    goals = [(float(x), float(y), float(yaw)) for (x, y, yaw) in
             zip(goalListx.split(","), goalListY.split(","), goalListYaw.split(","))]

    print('Please input 1 to continue:')
    user_input = raw_input()
    print(goals)

    r = rospy.Rate(1)
    navi = navigation_demo()

    if user_input == '1':
        navi.goto(goals[1])
        rospy.set_param('/im_flag', 1)
        wait_counter = 0
        
        while True:
            wait_counter += 1
            if result_received and calculate_result != 0:
                rospy.loginfo("calculate_result有值,进行下一步操作")
                rospy.loginfo(identification)
                result_received = False
                break
            if wait_counter > 1000:
                rospy.logwarn("等待超时,继续执行")
                break
            rospy.sleep(0.01)

        # 遍历每个点进行识别
        for i, p in enumerate(points):
            rospy.loginfo("开始识别第%s面墙:", str(i + 1))
            navi.recognize(p)

        # LLM查询
        end_result = navi.llm_client(ocr_text)
        end_result = calculate_result
        rospy.loginfo("LLM response: %d", end_result)
        navi.tts_client("最终答案是%d" % end_result)
        
        end_result = int(end_result)
        if end_result == 1 or end_result == 5:
            end_result = 14
        if end_result == 2 or end_result == 6:
            end_result = 15
        if end_result == 3 or end_result == 7:
            end_result = 16
        if end_result == 4 or end_result == 8:
            end_result = 13

        # 最终导航
        rospy.set_param('/move_base/local_costmap/inflation_radius', 0)
        rospy.set_param('/move_base/global_costmap/inflation_radius', 0)
        navi.goto(goals[end_result])
        rospy.set_param('/move_base/local_costmap/inflation_radius', 0.2)
        rospy.set_param('/move_base/global_costmap/inflation_radius', 0.3)
        rospy.sleep(2)
        navi.goto(goals[17])

    while not rospy.is_shutdown():
        r.sleep()