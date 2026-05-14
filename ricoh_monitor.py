import requests
import time
import json
import os
import sys

# ==================== 配置区 ====================
API_URL = "https://newsite.ricn-mall.com/api/pc/get_products?page=1"
# 保持你的精准监控关键词
TARGET_KEYWORDS = ["gr iii x", "gr iiix", "gr3x", "gr iv", "gr4", "官翻"]

# 30 秒探测一次
LOOP_INTERVAL = 30  
# 单次任务持续 4 小时 (245分钟)
RUN_DURATION = 245 

BARK_TOKEN = os.environ.get("BARK_TOKEN")
# ================================================

last_state = {}

def get_now():
    return time.strftime('%Y-%m-%d %H:%M:%S')

def check(is_first_run=False):
    global last_state
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Referer": "https://newsite.ricn-mall.com/"
    }
    try:
        # 加随机时间戳绕过 CDN 缓存
        url_with_ts = f"{API_URL}&t={int(time.time())}"
        response = requests.get(url_with_ts, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[{get_now()}] 警告：服务器返回状态码 {response.status_code}")
            return

        try:
            data = response.json()
        except Exception:
            print(f"[{get_now()}] 错误：接口返回的不是合法的 JSON 格式")
            return
        
        # 【精准解析】提取 data 下的 list 数组
        items = []
        if isinstance(data, dict) and 'data' in data:
            if isinstance(data['data'], dict):
                items = data['data'].get('list', [])
            elif isinstance(data['data'], list):
                items = data['data']

        current_items = {}
        for it in items:
            if not isinstance(it, dict): continue
            
            # 🚨 【核心修正】优先读取 store_name 作为商品名称
            name = it.get('store_name') or it.get('title') or it.get('name') or '未知商品'
            price = it.get('price', '未知')
            stock = it.get('stock_num', it.get('stock', '未知'))
            pid = it.get('id') or it.get('goods_id') or name
            
            state_mark = f"价格:{price} | 库存:{stock}"
            
            # 判断是否命中关键词
            if any(kw.lower() in name.lower() for kw in TARGET_KEYWORDS):
                current_items[pid] = (name, state_mark)

        # 变动侦测逻辑
        if not is_first_run and last_state:
            for pid, (name, mark) in current_items.items():
                if pid not in last_state:
                    notify("✨ 发现新商品上架", f"{name}\n{mark}")
                elif last_state[pid][1] != mark:
                    notify("⚡ 目标商品状态变更", f"{name}\n新状态: {mark}")
        
        if is_first_run:
            print(f"[{get_now()}] 成功初始化缓存池。当前在商城第 1 页抓到符合 GR 关键词的商品共 {len(current_items)} 个。")
            notify("📸 理光监控已成功对接", f"字段修正完毕！当前正以 {LOOP_INTERVAL}s 频率为您蹲守 GR IIIx / GR IV。")
            
        last_state = current_items
        print(f"[{get_now()}] 轮询正常，当前监控的目标商品数: {len(current_items)}")
        
    except Exception as e:
        print(f"[{get_now()}] 核心运行时捕获异常: {e}")

def notify(title, content):
    print(f">> 触发通知发送 <<\n标题: {title}\n内容: {content}")
    if BARK_TOKEN:
        # 对参数进行清理，防止特殊字符截断 URL
        clean_title = requests.utils.quote(title)
        clean_content = requests.utils.quote(content)
        url = f"https://api.day.app/{BARK_TOKEN}/{clean_title}/{clean_content}?group=Ricoh&level=active&sound=minuet"
        try:
            r = requests.get(url, timeout=5)
            print(f"Bark 返回状态: {r.status_code}")
        except Exception as e:
            print(f"Bark 推送失败: {e}")
    else:
        print("⚠️ 未检测到环境变量 BARK_TOKEN，跳过推送")

if __name__ == "__main__":
    print(f"🚀 理光全天候高频监控流正式拉起... (计划运行 {RUN_DURATION} 分钟)")
    # 强制在最顶层刷新标准输出缓冲区，确保 GitHub Actions 能实时显示 print 的内容
    sys.stdout.flush()
    
    # 首次启动运行初始化
    check(is_first_run=True)
    sys.stdout.flush()
    
    start_time = time.time()
    end_time = start_time + (RUN_DURATION * 60)
    
    while time.time() < end_time:
        time.sleep(LOOP_INTERVAL)
        check(is_first_run=False)
        sys.stdout.flush()
        
    print(f"[{get_now()}] 本班次工作时长已满，优雅退场，等待下一轮 cron 唤醒。")