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

      if not stores or not isinstance(stores, list):
        error_msg = "⚠️ 未能获取到门店列表数据，可能 Cookie 已完全失效或风控拦截。"
        print(error_msg)
        notify("⚠️ Apple 监控异常：数据为空", error_msg)
        return

      # ...（后续正常的门店查找与有货/无货报平安逻辑保持不变）...

  except Exception as e:
    error_msg = f"运行捕获异常: {e}"
    print(error_msg)
    notify("❌ Apple 监控脚本崩溃", error_msg)
