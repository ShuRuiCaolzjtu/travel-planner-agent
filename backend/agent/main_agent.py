"""
T2: LangChain Agent壳
实现状态机 + 基础对话能力，T5/T6中逐渐填充
"""


class TravelAgent:
    """旅行规划Agent(带状态机)"""

    PHASES = ["city_input", "card_flow", "constraint", "planning", "result", "adjust"]

    def __init__(self):
        self.session_id = None
        self.phase = "city_input"
        self.context = {}

    def init_session(self, session_id: str, city_name: str, days: int):
        """初始化Agent会话"""
        self.session_id = session_id
        self.phase = "card_flow"
        self.context = {
            "city_name": city_name,
            "days": days,
            "scored_pois": [],
            "constraints": {},
            "route": None,
        }
        return self._greeting()

    def _greeting(self) -> str:
        """返回欢迎语"""
        city = self.context.get("city_name", "")
        days = self.context.get("days", 3)
        return f"{city}我来过好多次啦！{days}天可以玩得很舒服。先刷刷卡片，告诉我你喜欢什么样的去处~"

    def process_message(self, message: str) -> str:
        """处理用户消息（根据当前阶段路由）"""
        if self.phase == "card_flow":
            return self._handle_card_flow(message)
        elif self.phase == "constraint":
            return self._handle_constraint(message)
        elif self.phase in ("result", "adjust"):
            return self._handle_result(message)
        return "请先选择目的地~"

    def _handle_card_flow(self, message: str) -> str:
        """卡片流阶段的对话处理"""
        if "开始排程" in message or "够了" in message or "不刷了" in message:
            self.phase = "constraint"
            return "好嘞！来聊聊你的具体安排吧~几个人一起去呀？"
        return "看到喜欢的就往右滑，不感兴趣就往左滑~刷够了告诉我「开始排程」"

    def _handle_constraint(self, message: str) -> str:
        """约束收集阶段的对话处理"""
        # 简单规则引擎，T5用LLM替换
        if "人" in message or "个" in message:
            self.context["constraints"]["num_people"] = message
            return "好的~第一天几点到大理？最后一天几点走？"
        elif "时间" in message or "点" in message:
            self.context["constraints"]["time"] = message
            return "住哪个片区？古城、双廊还是喜洲？"
        elif "住" in message or "古城" in message or "双廊" in message:
            self.context["constraints"]["accommodation"] = message
            return "在大理准备怎么出行？打车、租车还是公交？"
        elif "车" in message or "公交" in message or "租" in message:
            self.context["constraints"]["transport"] = message
            return "喜欢紧凑玩满一天还是悠闲慢慢逛？"
        elif "紧凑" in message or "悠闲" in message or "休闲" in message:
            self.context["constraints"]["pace"] = message
            return "对吃有什么偏好？本地小吃还是网红餐厅？"
        elif "吃" in message or "本地" in message or "网红" in message:
            self.context["constraints"]["food"] = message
            return "大概多少人均预算？（不含住宿和机票）"
        elif "预算" in message or "钱" in message or "¥" in message or "元" in message:
            self.context["constraints"]["budget"] = message
            self.phase = "planning"
            return "都记下了！开始帮你规划路线~稍等一下..."
        else:
            return "嗯嗯，说详细点？比如「两个人去」「住古城」「休闲一点」"

    def _handle_result(self, message: str) -> str:
        """行程结果阶段的对话处理"""
        return "你觉得这个路线怎么样？可以删除不想去的、添加感兴趣的，或者直接告诉我调整。"
