# 觅爱智慧大屏 Android TV 壳

首版是 Android TV WebView 壳，核心用户墙 UI 和播放逻辑仍由 Web 大屏页提供。

## 调试

1. 用 Android Studio 打开 `android_tv/`。
2. 运行 `app` 到 Android TV 设备或模拟器。
3. 首次启动后长按遥控器 `OK`，或按 `MENU`，打开设置面板。
4. Android Studio 模拟器使用：

```text
http://10.0.2.2:5180/web#/screen/player
```

5. 真机或电视盒子将大屏地址改成电脑局域网地址，例如：

```text
http://192.168.1.10:5180/web#/screen/player
```

不要使用 `127.0.0.1` 连接电脑开发服务，模拟器或电视上的 `127.0.0.1` 指向设备自身。

## 遥控器

- `MENU` 或长按 `OK`：打开设置面板。
- 没有 `MENU` 键时，连续按 `上 上 下 下 左 右 左 右 OK` 打开设置面板。
- `Back`：播放页不退出，避免误操作；设置页内关闭设置页。
- 网络异常页按 `OK`：重试加载。

## 本地配置

- `screen_url`：Web 大屏地址。
- WebView localStorage 会保存 Web 端的 `screen_device_token`。
- 设置页支持清除绑定 token、清除 WebView 缓存。
