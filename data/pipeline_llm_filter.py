"""
POI智能过滤 + 摘要生成管道
用LLM对高德POI做分类：保留旅游类 + 生成40字摘要
"""
import sqlite3
import json
import os
import urllib.request
import time

LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-d3fc5923f07848d0ac6b28cb54fb6c64")
LLM_API_URL = "https://api.deepseek.com/chat/completions"
LLM_MODEL = "deepseek-chat"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "poi_cache.db")

BATCH_SIZE = 10
REQUEST_INTERVAL = 0.5


def load_all_pois():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT poi_id, name, type, tags, district, rating, rating_count, summary
        FROM poi WHERE status = 'active'
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def build_batch_prompt(pois_batch):
    """构造一批POI的LLM prompt"""
    items = []
    for poi_id, name, poi_type, tags, district, rating, rating_count, summary in pois_batch:
        try:
            tag_list = json.loads(tags) if isinstance(tags, str) and tags else []
        except:
            tag_list = []
        tag_str = "、".join(tag_list[:5]) if tag_list else "无标签"
        items.append(f'  {{"id": "{poi_id}", "name": "{name}", "type": "{poi_type}", "tags": "{tag_str}", "district": "{district}", "rating": {rating}, "reviews": {rating_count}}}')

    prompt = f"""你是一个大理旅游专家。判断以下每个POI是否值得推荐给自由行游客。

保留标准：
- ✅ 大理景点优先保留：自然风光（洱海、苍山）、古城、寺庙、观景台、公园
- ✅ 知名美食街/夜市/小吃街（如人民路、洋人街）
- ✅ 特色文化体验（扎染、品茶、庙会）
- ✅ 地标性步行街

排除标准（满足任意一条就排除）:
- ❌ 所有单个餐厅/私房菜/饭馆/小吃店
- ❌ 所有商铺/专卖店/特产店
- ❌ 所有住宅小区/楼盘/公寓/别墅
- ❌ 所有连锁品牌店/快递/手机店
- ❌ 所有诊所/医院/美容/医美/按摩/足浴
- ❌ 所有公司/企业/政府机构
- ❌ 所有便利店/超市/菜市场/农贸市场
- ❌ 所有酒店/宾馆/民宿/客栈

重要：宁愿少保留，也不要保留非景点内容。只保留真正值得游客去看的景点。

对每个POI，请严格按JSON格式回复（不要其他文字）:
```json
[
  {{
    "id": "DL_POI_xxx",
    "decision": "include",
    "summary": "40字以内特色描述，语气像朋友推荐，给出一个亮点+实用信息"
  }},
  ...
]
```

POI列表:
{chr(10).join(items)}"""
    return prompt


def call_llm(prompt):
    """调用LLM"""
    req = urllib.request.Request(
        LLM_API_URL,
        data=json.dumps({
            "model": LLM_MODEL,
            "messages": [{"role": "system", "content": "你是一个大理旅游专家。只输出JSON，不要多余文字。"},
                         {"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 2000,
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]

    # 提取JSON
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return json.loads(content)


def main():
    print("=" * 50)
    print("POI智能过滤+摘要管道")
    print(f"模型: {LLM_MODEL}")
    print("=" * 50)

    pois = load_all_pois()
    print(f"\n共{len(pois)}条POI等待处理\n")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 添加summary字段（如果不存在）
    try:
        cur.execute("ALTER TABLE poi ADD COLUMN llm_summary TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE poi ADD COLUMN llm_status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass

    included = 0
    excluded = 0
    errors = 0

    for i in range(0, len(pois), BATCH_SIZE):
        batch = pois[i:i + BATCH_SIZE]
        prompt = build_batch_prompt(batch)

        print(f"[{i + 1}-{min(i + BATCH_SIZE, len(pois))}/{len(pois)}] 调用LLM...", end=" ")

        try:
            results = call_llm(prompt)
            for r in results:
                pid = r["id"]
                decision = r.get("decision", "exclude")
                summary = r.get("summary", "")

                if decision == "include":
                    cur.execute("UPDATE poi SET llm_status='active', llm_summary=? WHERE poi_id=?", (summary, pid))
                    if cur.rowcount > 0:
                        included += 1
                else:
                    cur.execute("UPDATE poi SET llm_status='excluded' WHERE poi_id=?", (pid,))
                    excluded += 1

            conn.commit()
            print(f"✅ (累计: 保留{included}, 排除{excluded}, 错误{errors})")

        except Exception as e:
            errors += 1
            print(f"❌ {e}")
            # 失败时默认保留（防误杀）
            for row in batch:
                cur.execute("UPDATE poi SET llm_status='active' WHERE poi_id=?", (row[0],))
            conn.commit()

        time.sleep(REQUEST_INTERVAL)

    # 统计
    cur.execute("SELECT COUNT(*) FROM poi WHERE llm_status='active'")
    final_active = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM poi WHERE llm_status='excluded'")
    final_excluded = cur.fetchone()[0]

    print(f"\n{'=' * 50}")
    print(f"完成!")
    print(f"  保留(旅游类): {final_active}")
    print(f"  排除(非旅游类): {final_excluded}")
    print(f"  LLM调用错误: {errors}")

    # 展示保留的POI
    cur.execute("""
        SELECT poi_id, name, type, llm_summary FROM poi
        WHERE llm_status='active' ORDER BY rating DESC LIMIT 20
    """)
    print(f"\n  保留列表(top 20):")
    for r in cur.fetchall():
        print(f"    {r[0]} | {r[1]:25s} | {r[2]:6s} | {r[3][:30] if r[3] else '-'}")

    conn.close()


if __name__ == "__main__":
    main()
