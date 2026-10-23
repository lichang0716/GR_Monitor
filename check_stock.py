import json
import os
import sys
import requests


def notify(title, content):
  print(f">> 触发通知发送 <<\n标题: {title}\n内容: {content}")
  bark_token = os.environ.get("BARK_TOKEN")
  if bark_token:
    clean_title = requests.utils.quote(title)
    clean_content = requests.utils.quote(content)
    url = f"https://api.day.app/{bark_token}/{clean_title}/{clean_content}?group=AppleStore&level=active&sound=minuet"
    try:
      r = requests.get(url, timeout=5)
      print(f"Bark 返回状态: {r.status_code}")
    except Exception as e:
      print(f"Bark 推送失败: {e}")
  else:
    print("⚠️ 未检测到环境变量 BARK_TOKEN，跳过推送")


def check_apple_store_pickup():
  url = "https://secure8.www.apple.com.cn/shop/checkoutx/fulfillment?_a=search&_m=checkout.fulfillment.pickupTab.pickup.storeLocator"

  cookie_str = os.environ.get("APPLE_COOKIE", "")
  if not cookie_str:
    print("错误: 未检测到 APPLE_COOKIE 环境变量，请先配置！")
    return

  headers = {
      "Referer": (
          "https://secure8.www.apple.com.cn/shop/checkout?_s=Fulfillment-init"
      ),
      "User-Agent": (
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
          " (KHTML, like Gecko) Version/27.0.1 Safari/605.1.15"
      ),
      "Origin": "https://secure8.www.apple.com.cn",
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Requested-With": "Fetch",
      "x-aos-model-page": "checkoutPage",
      "x-aos-stk": "KTVu9cALz4gEm8GiScQzqfacUaI",
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
    print("正在请求 Apple Store 取货状态...")
    response = requests.post(url, headers=headers, data=data, timeout=15)

    print(f"HTTP 状态码: {response.status_code}")

    if response.status_code != 200:
      print(f"请求失败，完整返回: {response.text[:1000]}")
      return

    try:
      result = response.json()
    except Exception as json_err:
      print(f"JSON 解析失败: {json_err}")
      print(f"服务器返回的原始内容（前 1000 字符）:\n{response.text[:1000]}")
      return

    # 解析返回的 JSON 结构，提取各门店库存
    stores = (
        result.get("body", {})
        .get("checkout", {})
        .get("fulfillment", {})
        .get("pickupTab", {})
        .get("pickup", {})
        .get("storeLocator", {})
        .get("searchResults", {})
        .get("retailStores", [])
    )

    if not stores:
      print("⚠️ 未在标准路径解析到门店信息。打印部分响应结构以供排查：")
      print(json.dumps(result, ensure_ascii=False)[:1500])
      return

    print(f"\n--- 查询结果 (共找到 {len(stores)} 家门店) ---")
    for store in stores:
      store_name = store.get("storeName")
      distance = store.get("distance")
      availability = store.get("availability", {})
      store_status = availability.get("storeAvailability", "未知状态")

      print(f"门店: {store_name} | 距离: {distance} | 状态: {store_status}")

  except Exception as e:
    print(f"请求发生异常: {e}")


if __name__ == "__main__":
  print("🚀 Apple Store 监控调试脚本启动...")
  sys.stdout.flush()
  check_apple_store_pickup()
  sys.stdout.flush()
