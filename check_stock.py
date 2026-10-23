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

    # 使用递归函数智能查找所有门店信息
    stores = find_key_recursive(result, "retailStores")

    if not stores or not isinstance(stores, list):
      print("⚠️ 仍然未找到 retailStores，完整响应内容如下：")
      print(json.dumps(result, ensure_ascii=False))
      return

    print(f"\n--- 查询结果 (共找到 {len(stores)} 家门店) ---")
    in_stock_found = False
    stock_summary = []

    for store in stores:
      store_name = store.get("storeName", "未知门店")
      distance = store.get("distance", "未知距离")
      availability = store.get("availability", {})
      store_status = availability.get("storeAvailability", "未知状态")

      print(f"门店: {store_name} | 距离: {distance} | 状态: {store_status}")

      line_items = availability.get("lineItemAvailability", [])
      for item in line_items:
        part_name = item.get("partName", "iPhone Duo")
        quote = item.get("availabilityQuote", "未知")
        is_available = item.get("availableNowForLine", False)
        print(f"  -> 商品: {part_name} | 状态: {quote} (可买: {is_available})")

        if is_available or (
            quote and "不可取货" not in quote and "目前不可取货" not in quote
        ):
          in_stock_found = True
          stock_summary.append(f"门店: {store_name}\n商品: {part_name}\n状态: {quote}")

    if in_stock_found:
      content_str = "\n\n".join(stock_summary)
      notify("🚨 Apple Store 发现可取货！", content_str)
    else:
      print("当前周边门店均无货。")

  except Exception as e:
    print(f"请求发生异常: {e}")


if __name__ == "__main__":
  print("🚀 Apple Store 监控调试脚本启动...")
  sys.stdout.flush()
  check_apple_store_pickup()
  sys.stdout.flush()
