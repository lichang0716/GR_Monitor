from datetime import datetime
import json
import os
import sys
import pytz
import requests


def get_shanghai_time():
    """获取当前上海时区的时间对象和格式化字符串"""
    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now_shanghai = datetime.now(shanghai_tz)
    return now_shanghai


def notify(title, content):
    print(f">> 触发通知发送 <<\n标题: {title}\n内容: {content}")
    sys.stdout.flush()
    bark_token = os.environ.get("BARK_TOKEN")
    if bark_token:
        url = "https://api.day.app/push"
        payload = {
            "device_key": bark_token,
            "title": title,
            "body": content,
            "group": "AppleStore",
            "level": "active",
            "sound": "minuet",
        }
        try:
            r = requests.post(url, json=payload, timeout=5)
            print(f"Bark 返回状态: {r.status_code}")
            print(f"Bark 响应内容: {r.text}")
            sys.stdout.flush()
        except Exception as e:
            print(f"Bark 推送失败: {e}")
            sys.stdout.flush()
    else:
        print("⚠️ 未检测到环境变量 BARK_TOKEN，跳过推送")
        sys.stdout.flush()


def find_key_recursive(data, target_key):
    """递归遍历 JSON，寻找指定的 key（如 retailStores）"""
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for k, v in data.items():
            result = find_key_recursive(v, target_key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_key_recursive(item, target_key)
            if result is not None:
                return result
    return None


def check_apple_store_pickup():
    print("1. 准备构建请求参数...")
    sys.stdout.flush()

    url = "https://secure8.www.apple.com.cn/shop/checkoutx/fulfillment?_a=search&_m=checkout.fulfillment.pickupTab.pickup.storeLocator"

    cookie_str = os.environ.get("APPLE_COOKIE", "")
    if not cookie_str:
        error_msg = "错误: 未检测到 APPLE_COOKIE 环境变量，请先配置！"
        print(error_msg)
        sys.stdout.flush()
        notify("❌ Apple 监控配置错误", error_msg)
        return

    headers = {
        "Referer": (
            "https://secure8.www.apple.com.cn/shop/checkout?_s=Fulfillment-init"
        ),
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0.1"
            " Safari/605.1.15"
        ),
        "Origin": "https://secure8.www.apple.com.cn",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "Fetch",
        "x-aos-model-page": "checkoutPage",
        "x-aos-stk": "VVTUPxBBUhrEKoTyJj29bQmlHKA",
        "syntax": "graviton",
        "modelVersion": "v2",
        "Cookie": cookie_str,
    }

    data = {
        "checkout.fulfillment.pickupTab.pickup.storeLocator.showAllStores": (
            "false"
        ),
        "checkout.fulfillment.pickupTab.pickup.storeLocator.selectStore": "",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.searchInput": (
            "江苏 苏州 姑苏区"
        ),
        (
            "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.city"
        ): "苏州",
        (
            "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.state"
        ): "江苏",
        (
            "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.provinceCityDistrict"
        ): "江苏 苏州 姑苏区",
        (
            "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.countryCode"
        ): "CN",
        (
            "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.district"
        ): "姑苏区",
    }

    try:
        print("2. 正在向 Apple 发起 HTTP POST 请求...")
        sys.stdout.flush()

        response = requests.post(url, headers=headers, data=data, timeout=10)

        print(f"3. 请求完成，HTTP 状态码: {response.status_code}")
        sys.stdout.flush()

        if response.status_code != 200:
            error_msg = f"请求失败，状态码: {response.status_code}\n请检查 Cookie 或 stk 是否已失效！"
            print(error_msg)
            sys.stdout.flush()
            notify("⚠️ Apple 监控异常：HTTP 错误", error_msg)
            return

        try:
            result = response.json()
        except Exception as json_err:
            error_msg = f"JSON 解析失败: {json_err}\n返回内容可能包含验证码或错误页面。"
            print(error_msg)
            sys.stdout.flush()
            notify("⚠️ Apple 监控异常：解析错误", error_msg)
            return

        stores = find_key_recursive(result, "retailStores")

        if not stores or not isinstance(stores, list):
            error_msg = (
                "⚠️ 未能获取到门店列表数据，可能 Cookie"
                " 已完全失效或风控拦截。"
            )
            print(error_msg)
            sys.stdout.flush()
            notify("⚠️ Apple 监控异常：数据为空", error_msg)
            return

        # 精准锁定：Apple 苏州
        target_store = None
        for store in stores:
            if store.get("storeName") == "Apple 苏州":
                target_store = store
                break

        if not target_store:
            print("⚠️ 未在返回结果中找到 [Apple 苏州] 门店。")
            sys.stdout.flush()
            return

        store_name = target_store.get("storeName")
        distance = target_store.get("distance", "未知")
        availability = target_store.get("availability", {})
        store_status = availability.get("storeAvailability", "未知状态")

        print(f"\n--- 🎯 目标门店锁定 ---")
        print(f"门店: {store_name} | 距离: {distance} | 状态: {store_status}")
        sys.stdout.flush()

        in_stock_found = False
        stock_details = []

        line_items = availability.get("lineItemAvailability", [])
        for item in line_items:
            part_name = item.get("partName", "iPhone Duo")
            quote = item.get("availabilityQuote", "未知")
            is_available = item.get("availableNowForLine", False)
            print(
                f"  -> 商品: {part_name} | 状态: {quote} (可买: {is_available})"
            )
            sys.stdout.flush()

            if is_available or (
                quote and "不可取货" not in quote and "目前不可取货" not in quote
            ):
                in_stock_found = True
                stock_details.append(f"商品: {part_name}\n状态: {quote}")

        # 判定通知逻辑
        if in_stock_found:
            content_str = "\n".join(stock_details)
            notify("🚨 Apple 苏州 发现可取货！", content_str)
        else:
            print("🌱 Apple 苏州当前暂无货可取。")
            sys.stdout.flush()

            # 使用上海时区获取当前分钟
            now_shanghai = get_shanghai_time()
            current_minute = now_shanghai.minute
            current_time_str = now_shanghai.strftime("%H:%M")

            # 仅在整点 (0分) 或半点 (30分) 时发送无货报平安推送
            if current_minute in (0, 30):
                notify(
                    f"⏳ Apple 苏州巡检报平安 ({current_time_str})",
                    "当前暂无货可取，脚本正在持续为您蹲守中...",
                )
            else:
                print(
                    f"当前分钟为 {current_minute}分，非整点/半点，跳过无货推送。"
                )
                sys.stdout.flush()

    except requests.exceptions.Timeout:
        error_msg = (
            "❌ 请求 Apple 接口超时（超过 10 秒无响应），可能被苹果防火墙限制。"
        )
        print(error_msg)
        sys.stdout.flush()
        notify("⚠️ Apple 监控异常：请求超时", error_msg)
    except Exception as e:
        error_msg = f"❌ 运行捕获异常: {e}"
        print(error_msg)
        sys.stdout.flush()
        notify("❌ Apple 监控脚本崩溃", error_msg)


if __name__ == "__main__":
    print("🚀 Apple 苏州监控脚本启动...")
    sys.stdout.flush()
    check_apple_store_pickup()
    print("🏁 脚本运行结束。")
    sys.stdout.flush()
