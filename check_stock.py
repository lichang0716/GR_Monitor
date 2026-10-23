from datetime import datetime
import json
import os
import sys
import requests


def notify(title, content):
    print(f">> 触发通知发送 <<\n标题: {title}\n内容: {content}")
    bark_token = os.environ.get("BARK_TOKEN")
    if bark_token:
        url = "https://api.day.app/push"
        payload = {
            "device_key": bark_token,
            "title": title,
            "body": content,
            "group": "AppleStore",
            "level": "active",
            "sound": "minuet"
        }
        try:
            r = requests.post(url, json=payload, timeout=5)
            print(f"Bark 返回状态: {r.status_code}")
            print(f"Bark 响应内容: {r.text}")
        except Exception as e:
            print(f"Bark 推送失败: {e}")
    else:
        print("⚠️ 未检测到环境变量 BARK_TOKEN，跳过推送")


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
    url = "https://secure8.www.apple.com.cn/shop/checkoutx/fulfillment?_a=search&_m=checkout.fulfillment.pickupTab.pickup.storeLocator"

    cookie_str = os.environ.get("APPLE_COOKIE", "")
    if not cookie_str:
        error_msg = "错误: 未检测到 APPLE_COOKIE 环境变量，请先配置！"
        print(error_msg)
        notify("❌ Apple 监控配置错误", error_msg)
        return

    headers = {
        "Referer": "https://secure8.www.apple.com.cn/shop/checkout?_s=Fulfillment-init",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0.1 Safari/605.1.15",
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
        "checkout.fulfillment.pickupTab.pickup.storeLocator.showAllStores": "false",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.selectStore": "",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.searchInput": "江苏 苏州 姑苏区",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.city": "苏州",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.state": "江苏",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.provinceCityDistrict": "江苏 苏州 姑苏区",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.countryCode": "CN",
        "checkout.fulfillment.pickupTab.pickup.storeLocator.address.stateCitySelectorForCheckout.district": "姑苏区"
    }

    try:
        print("正在请求 Apple Store 取货状态...")
        response = requests.post(url, headers=headers, data=data, timeout=15)

        print(f"HTTP 状态码: {response.status_code}")

        if response.status_code != 200:
            error_msg = f"请求失败，状态码: {response.status_code}\n请检查 Cookie 或 stk 是否已失效！"
            print(error_msg)
            notify("⚠️ Apple 监控异常：HTTP 错误", error_msg)
            return

        try:
            result = response.json()
        except Exception as json_err:
            error_msg = f"JSON 解析失败: {json_err}\n返回内容可能包含验证码或错误页面。"
            print(error_msg)
            notify("⚠️ Apple 监控异常：解析错误", error_msg)
            return

        stores = find_key_recursive(result, "retailStores")
