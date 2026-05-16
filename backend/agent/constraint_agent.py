"""
T5: 约束收集Agent — LLM驱动，带规则后备
"""
import json
import os
import re
import urllib.request

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
USE_LLM = bool(LLM_API_KEY)

# LLM输出的字段名可能不准确，做别名映射
FIELD_ALIASES = {
    "budget": "budget_per_day",
    "每日预算": "budget_per_day",
    "预算": "budget_per_day",
    "人数": "num_people",
    "到达": "arrival_info",
    "到达信息": "arrival_info",
    "离开": "departure_info",
    "离开信息": "departure_info",
    "住宿": "accommodation",
    "酒店": "accommodation",
    "交通": "transport_mode",
    "交通方式": "transport_mode",
    "节奏": "pace",
    "游玩节奏": "pace",
    "饮食": "food_preference",
    "美食偏好": "food_preference",
    "美食": "food_preference",
    "特殊": "special_requirements",
    "特殊需求": "special_requirements",
    "要求": "special_requirements",
    "到达地点": "arrival_info",
    "离开地点": "departure_info",
    "入住": "accommodation",
    "出行": "transport_mode",
    "偏好": "food_preference",
}

CONSTRAINT_FIELDS = [
    ("num_people", "人数", "几个人一起去呀？"),
    ("arrival_info", "到达信息", "第一天几点到大理？在哪里下车？（比如：早上七点到大理站）"),
    ("departure_info", "离开信息", "最后一天几点走？从哪里走？（比如：晚上九点从大理站走）"),
    ("accommodation", "住宿", "住哪个酒店或片区？（比如：全季酒店、古城）"),
    ("transport_mode", "交通方式", "在大理怎么出行？打车、租车还是公交？"),
    ("pace", "游玩节奏", "喜欢紧凑玩满一天，还是悠闲慢慢逛？"),
    ("food_preference", "美食偏好", "对吃有什么偏好？本地小吃还是网红餐厅？"),
    ("budget_per_day", "预算", "大概多少人均预算？（不含住宿和机票）"),
    ("special_requirements", "特殊需求", "有什么特别要求吗？比如不能爬山、要拍很多照片之类"),
]

_CN_NUM = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'两':2}

def _parse_cn_time(text: str) -> str | None:
    """从文本中解析出时间字符串 '7:00' 或 '21:00'"""
    m = re.search(r'([0-9一二三四五六七八九十两]+)[：:点时](\d{0,2})', text)
    if m:
        h_str = m.group(1)
        h = _CN_NUM.get(h_str, int(h_str) if h_str.isdigit() else -1)
        mi = int(m.group(2) or 0)
        if '下午' in text and h < 12: h += 12
        if '晚上' in text and h <= 6: h += 12
        if '中午' in text and h < 12: h = 12
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h}:{mi:02d}"
    return None

def _parse_station(text: str) -> str | None:
    """从文本中提取站名，如"大理站"、"大理机场" """
    m = re.search(r'(\S*[站机场])', text)
    return m.group(1) if m else None


INFERENCE_PATTERNS = [
    (r"(\d+)个?人", lambda m: {"num_people": int(m.group(1))}),
    (r"我和女朋友|我们俩|两个人|情侣", lambda m: {"num_people": 2}),
    (r"一个人|我自己|独自", lambda m: {"num_people": 1}),
    (r"一家(?:三|四|五)口", lambda m: {"num_people": {"三": 3, "四": 4, "五": 5}.get(m.group(1), 3)}),
    (r"带爸妈|带父母|和父母", lambda m: {"num_people": 3, "pace": "relaxed"}),
    (r"带小孩|带孩子|亲子", lambda m: {"pace": "relaxed"}),
    (r"不要(?:太|很)?赶|轻松|悠闲|慢慢|休闲", lambda m: {"pace": "relaxed"}),
    (r"紧凑|满一点|多去几个|效率|特种兵", lambda m: {"pace": "compact"}),
    (r"标准|正常|适中|一般", lambda m: {"pace": "standard"}),
    (r"打车|滴滴|出租车", lambda m: {"transport_mode": "taxi"}),
    (r"租车|自驾|开车|租车", lambda m: {"transport_mode": "self_drive"}),
    (r"公交|巴士|公共交通", lambda m: {"transport_mode": "bus"}),
    (r"骑车|自行车|电动|小电驴", lambda m: {"transport_mode": "bike"}),
    (r"步行|走路|散步", lambda m: {"transport_mode": "walk"}),
    (r"古城|大理古城", lambda m: {"accommodation": "古城"}),
    (r"双廊", lambda m: {"accommodation": "双廊"}),
    (r"喜洲", lambda m: {"accommodation": "喜洲"}),
    (r"海东", lambda m: {"accommodation": "海东"}),
    (r"才村", lambda m: {"accommodation": "才村"}),
    (r"苍山", lambda m: {"accommodation": "苍山"}),
    (r"本地小吃|路边摊|苍蝇馆|地道|小吃", lambda m: {"food_preference": "local"}),
    (r"网红|打卡|热门", lambda m: {"food_preference": "trendy"}),
    (r"高档|餐厅|环境|精致", lambda m: {"food_preference": "fine_dining"}),
    (r"(?:总)?(?:预算|大概|约)[：:]?\s*(\d{2,5})\s*(?:元|块)?(?:\s*[/每]?\s*(?:天|日|人)?)", lambda m: {"budget_per_day": int(m.group(1))}),
    (r"(?:每人|人均)?\s*(\d{2,5})\s*(?:元|块)", lambda m: {"budget_per_day": int(m.group(1))}),
    (r"(\d{3,5})\s*(?:元|块)", lambda m: {"budget_per_day": int(m.group(1))}),
    (r"不限|随便|都行|无所谓|没有|无|没什么", lambda m: {}),
]

ACCOMMODATION_COORDS = {
    "古城": (25.6814, 100.1647),
    "双廊": (25.9527, 100.1276),
    "喜洲": (25.8543, 100.0120),
    "海东": (25.5970, 100.2805),
    "才村": (25.6650, 100.1820),
    "苍山": (25.6667, 100.1000),
}


def _first_int(m):
    for g in m.groups():
        if g and g.isdigit():
            return {"budget_per_day": int(g)}
    return {}


# 无意义值过滤器，用于判断LLM输出是否有效
GARBAGE_VALUES = {"?", "无", "未收集", "", "None", "null", "不知道", "不确定",
                  "未提及", "暂无", "待定", "待确认", "none", "undefined"}


class ConstraintAgent:
    def __init__(self, session_id: str, days: int = 3, scored_count: int = 0):
        self.session_id = session_id
        self.days = days
        self.scored_count = scored_count
        self.constraints = {}
        self.collected_fields = set()
        self.conversation_history = []
        self.finished = False

    def _is_valid_value(self, field: str, value) -> bool:
        """检查LLM提取的值是否有效，防止垃圾值污染"""
        if value is None:
            return False
        v = str(value).strip()
        if v.lower() in GARBAGE_VALUES or v == "":
            return False
        if field == "num_people":
            try:
                return int(float(v)) > 0
            except (ValueError, TypeError):
                return False
        if field == "budget_per_day":
            try:
                return int(float(v)) > 0
            except (ValueError, TypeError):
                return False
        if field == "pace":
            return v.lower() in ("relaxed", "standard", "compact", "休闲", "标准", "紧凑")
        if field == "transport_mode":
            return v.lower() in ("taxi", "self_drive", "bus", "bike", "walk", "打车", "租车", "公交", "骑车", "步行")
        if field == "food_preference":
            return v.lower() in ("local", "trendy", "fine_dining", "mixed", "本地", "网红", "高档", "综合")
        if field in ("arrival_info", "departure_info"):
            return len(v) >= 3  # 至少包含时间或地点信息
        return len(v) >= 1

    def _current_field_index(self):
        for i, (field, _, _) in enumerate(CONSTRAINT_FIELDS):
            if field not in self.collected_fields:
                return i
        return len(CONSTRAINT_FIELDS)

    def get_next_question(self) -> str:
        idx = self._current_field_index()
        if idx >= len(CONSTRAINT_FIELDS):
            return ""
        _, _, question = CONSTRAINT_FIELDS[idx]
        return question

    def _infer_only_new(self, message: str) -> dict:
        """从消息中推断值，只返回尚未收集的字段"""
        inferred = {}
        for pattern, handler in INFERENCE_PATTERNS:
            match = re.search(pattern, message)
            if match:
                try:
                    result = handler(match)
                    if isinstance(result, dict):
                        filtered = {k: v for k, v in result.items() if k not in self.collected_fields}
                        inferred.update(filtered)
                except Exception:
                    continue
        return inferred

    def process_message(self, message: str) -> dict:
        self.conversation_history.append({"role": "user", "content": message})

        if USE_LLM:
            return self._process_with_llm(message)
        return self._process_with_rules(message)

    def _process_with_rules(self, message: str) -> dict:
        """规则引擎处理"""
        # 先清除无效值，让规则可重提取
        for field in list(self.collected_fields):
            if not self._is_valid_value(field, self.constraints.get(field)):
                self.constraints.pop(field, None)
                self.collected_fields.discard(field)

        inferred = self._infer_only_new(message)

        # 先处理推断出来的值
        if inferred:
            for key, value in inferred.items():
                self.constraints[key] = value
                self.collected_fields.add(key)

        # 如果当前字段还没被填充，用规则处理
        idx = self._current_field_index()
        if idx >= len(CONSTRAINT_FIELDS):
            pass  # 全部已收集
        else:
            field, _, _ = CONSTRAINT_FIELDS[idx]

            # 特殊处理到达/离开信息：提取"时间@地点"
            if field == "arrival_info" or field == "departure_info":
                t = _parse_cn_time(message)
                s = _parse_station(message)
                val = "@".join(filter(None, [t, s]))
                if val:
                    self.constraints[field] = val
                    self.collected_fields.add(field)
                elif field not in self.collected_fields:
                    self.constraints[field] = message
                    self.collected_fields.add(field)
            elif field not in self.collected_fields:
                self.constraints[field] = message
                self.collected_fields.add(field)

        conflicts = self._detect_conflicts()
        idx = self._current_field_index()

        if idx >= len(CONSTRAINT_FIELDS):
            self.finished = True
            response = {
                "intent": "complete",
                "next_question": "都记下了！开始帮你规划路线~稍等一下...",
                "constraints": self.constraints,
                "conflicts": conflicts,
                "is_complete": True,
            }
        else:
            confirm = self._build_confirm(inferred)
            next_q = self.get_next_question()
            response = {
                "intent": "next_question",
                "next_question": (confirm + " " + next_q).strip() if confirm else next_q,
                "constraints": self.constraints,
                "conflicts": conflicts,
                "is_complete": False,
            }

        self.conversation_history.append({"role": "assistant", "content": response["next_question"]})
        return response

    def _process_with_llm(self, message: str) -> dict:
        # 记录处理前的字段索引，用于后续判断是否推进
        idx_before = self._current_field_index()

        for attempt in range(2):
            try:
                prompt = self._build_llm_prompt()
                msgs = [{"role": "system", "content": prompt},
                        {"role": "user", "content": message}]
                req = urllib.request.Request(
                    LLM_API_URL,
                    data=json.dumps({
                        "model": LLM_MODEL, "messages": msgs,
                        "temperature": 0.01, "max_tokens": 250,
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {LLM_API_KEY}"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    content = json.loads(resp.read())["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```"):
                    blocks = content.split("```")
                    content = blocks[1] if len(blocks) > 2 else blocks[0]
                content = content.strip()
                if content.startswith("{"):
                    parsed = json.loads(content)
                else:
                    import re as _jj
                    m = _jj.search(r'(\{.*\})', content, re.DOTALL)
                    parsed = json.loads(m.group(1)) if m else None
                    if parsed is None:
                        raise ValueError("no json found")

                # ===== STEP 1: 提取LLM的constraints，去重+验证 =====
                if "constraints" in parsed:
                    for k, v in parsed["constraints"].items():
                        actual_key = FIELD_ALIASES.get(k, k)
                        if self._is_valid_value(actual_key, v):
                            # 允许覆盖已收集字段（解决DB预填值阻塞问题）
                            self.constraints[actual_key] = v
                            self.collected_fields.add(actual_key)

                # ===== STEP 2: 清除无效值 =====
                for field in list(self.collected_fields):
                    if not self._is_valid_value(field, self.constraints.get(field)):
                        self.constraints.pop(field, None)
                        self.collected_fields.discard(field)

                # ===== STEP 3: 规则引擎兜底（覆盖LLM的错误，如"特种兵"→compact） =====
                for pattern, handler in INFERENCE_PATTERNS:
                    match = re.search(pattern, message)
                    if match:
                        try:
                            result = handler(match)
                            if isinstance(result, dict):
                                for k, v in result.items():
                                    if v:  # 非空值直接覆盖
                                        self.constraints[k] = v
                                        self.collected_fields.add(k)
                        except Exception:
                            continue

                # ===== STEP 3.5: 到达/离开信息结构化后处理（从原始消息中提取时间@地点） =====
                for field in ("arrival_info", "departure_info"):
                    if field in self.collected_fields:
                        stored = str(self.constraints.get(field, ""))
                        if "@" not in stored and len(stored) >= 3:
                            t = _parse_cn_time(message)
                            s = _parse_station(message)
                            if t or s:
                                structured = "@".join(filter(None, [t, s]))
                                if structured:
                                    self.constraints[field] = structured

                # ===== STEP 3.6: 处理"随便/没有/都可以"跳过场景 =====
                if idx_before < len(CONSTRAINT_FIELDS):
                    field_before, _, _ = CONSTRAINT_FIELDS[idx_before]
                    if field_before not in self.collected_fields:
                        if re.search(r"不限|随便|都行|无所谓|没有|无|没什么|都可以|不用", message):
                            defaults = {
                                "food_preference": "mixed",
                                "special_requirements": "无",
                                "budget_per_day": 500,
                                "pace": "standard",
                                "transport_mode": "taxi",
                            }
                            default_val = defaults.get(field_before, "无")
                            self.constraints[field_before] = default_val
                            self.collected_fields.add(field_before)

                # ===== STEP 4: 判断是否完成（必须全部9个字段收集完） =====
                all_collected = len(self.collected_fields) >= len(CONSTRAINT_FIELDS)
                if parsed.get("is_complete") and all_collected:
                    self.finished = True
                if all_collected:
                    self.finished = True

                # ===== STEP 5: 组装响应，确保next_question与实际字段同步 =====
                idx_after = self._current_field_index()

                if self.finished or idx_after >= len(CONSTRAINT_FIELDS):
                    self.finished = True
                    next_q = "都记下了！开始帮你规划路线~稍等一下..."
                elif idx_after > idx_before:
                    # 字段成功推进，信任LLM的下一个问题
                    next_q = parsed.get("next_question", "")
                    if not next_q or len(next_q) < 3:
                        _, _, actual_q = CONSTRAINT_FIELDS[idx_after]
                        next_q = actual_q
                else:
                    # 字段卡住未推进（空constraints或提取失败），覆盖为规范问题
                    _, _, actual_q = CONSTRAINT_FIELDS[idx_after]
                    next_q = actual_q

                response = {
                    "intent": "complete" if self.finished else "next_question",
                    "next_question": next_q,
                    "constraints": self.constraints,
                    "conflicts": parsed.get("conflicts", []),
                    "is_complete": self.finished,
                }
                self.conversation_history.append({"role": "assistant", "content": next_q})
                return response
            except Exception:
                if attempt == 1:
                    break
                continue

        response = self._process_with_rules(message)
        response["llm_fallback"] = True
        # _process_with_rules 内部已追加assistant消息，这里不再重复追加
        return response

    def _build_llm_prompt(self) -> str:
        idx = self._current_field_index()
        current_field, current_label, current_question = CONSTRAINT_FIELDS[idx] if idx < len(CONSTRAINT_FIELDS) else ("", "", "")

        # 构建进度表
        progress_lines = []
        for field, label, _ in CONSTRAINT_FIELDS:
            if field in self.collected_fields:
                val = self.constraints.get(field, "✓")
                progress_lines.append(f"  ✅ {label}: {val}")
            elif field == current_field:
                progress_lines.append(f"  ⬅ {label}: （正在收集）")
            else:
                progress_lines.append(f"  ⬜ {label}: 待收集")
        progress_str = "\n".join(progress_lines)

        # 构建最近对话历史（最近3轮，帮助LLM记住上下文）
        history_lines = []
        # conversation_history最后一条是当前用户消息，排除它
        recent = self.conversation_history[:-1]  # 去掉刚追加的当前消息
        recent = recent[-6:] if len(recent) > 6 else recent  # 最多最近3轮(6条)
        for turn in recent:
            role = "用户" if turn["role"] == "user" else "助手"
            history_lines.append(f"  {role}: {turn['content']}")
        history_str = "\n".join(history_lines) if history_lines else "  （暂无）"

        return f"""你是一个旅行信息收集助手。从用户最新消息中提取结构化信息。

当前进度（{len(self.collected_fields)}/9）：
{progress_str}

最近对话：
{history_str}

当前任务：从用户最新一条消息中提取「{current_label}」。
字段名：{current_field}
提示：{current_question}

规则：
1. JSON的key必须用英文（{current_field}），不要用中文
2. 如用户信息充足可额外提取其他字段（用英文key）
3. 如果用户说"随便/都行/没有"，constraints={{}}，自动跳到下一项
4. 再次看到已收集过的信息不要重复存
5. 所有9个字段都收集完后is_complete=true
6. 不要生成"提取的值"、"值"等占位符，只放真实值
7. ⚠️ 到达/离开信息（arrival_info/departure_info）必须格式化为"时间@地点"，例如：
   - "早上七点到大理站" → "7:00@大理站"
   - "晚上九点从大理站走" → "21:00@大理站"
   - "中午到大理机场" → "12:00@大理机场"

只输出JSON（不要其他文字）：
{{"intent":"next_question","constraints":{{"{current_field}":"值"}},"next_question":"确认+下一个自然问题","conflicts":[],"is_complete":false}}"""

    def _build_confirm(self, inferred: dict) -> str:
        if not inferred:
            return ""
        labels = {
            "num_people": lambda v: f"{v}个人",
            "pace": {"relaxed": "休闲节奏", "standard": "标准节奏", "compact": "紧凑节奏"},
            "transport_mode": {"taxi": "打车", "self_drive": "租车", "bus": "公交", "bike": "骑车", "walk": "步行"},
            "accommodation": lambda v: f"住{v}",
            "food_preference": {"local": "本地小吃", "trendy": "网红餐厅", "fine_dining": "高档餐厅", "mixed": "综合"},
            "budget_per_day": lambda v: f"预算{v}元/天",
        }
        parts = []
        for k, v in inferred.items():
            label = labels.get(k, {})
            if callable(label):
                parts.append(label(v))
            elif isinstance(label, dict):
                parts.append(label.get(v, str(v)))
            else:
                parts.append(str(v))
        return ("好的，" + "，".join(parts) + "~") if parts else ""

    def _detect_conflicts(self) -> list[str]:
        conflicts = []
        pace = self.constraints.get("pace", "")
        if self.scored_count > 10 and self.days <= 2:
            conflicts.append(f"{self.scored_count}个想去的地方{self.days}天可能有点赶，我会按评分帮你挑最合适的")
        if self.constraints.get("num_people", 0) >= 4 and pace == "compact":
            conflicts.append("多人紧凑行程需要确认大家体力跟得上哦")
        return conflicts

    def get_constraints_preference(self) -> dict:
        pref = dict(self.constraints)
        acc = pref.get("accommodation", "")
        if acc in ACCOMMODATION_COORDS:
            pref["accommodation_lat"] = ACCOMMODATION_COORDS[acc][0]
            pref["accommodation_lon"] = ACCOMMODATION_COORDS[acc][1]
        return pref

    @property
    def is_ready_for_planning(self) -> bool:
        required = {"num_people", "pace"}
        return required.issubset(self.collected_fields) or self.finished
