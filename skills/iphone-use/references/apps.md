# 查找真实 app bundle ID

已经知道且核验过的 bundle ID 可直接启动，不为每次 launch 重查安装清单。查常用 App 可先用 `pua_apps(source="catalog")` 离线检索本地目录；未知应用或需要区分用户实际安装的版本时用 source=auto，先查选定 iPhone 的已安装应用，再查本地目录，没有匹配时返回空结果。不要凭品牌名拼写 bundle ID，也不要连续试多个猜测值。

```json
{"query":"招商银行","source":"auto"}
```

本例应返回 `com.cmbchina.MPBBank`。检查名称、发布者和候选来源后，把 bundle_id 传给 `pua_launch_app`。正常启动乐观继续；下一步需要未知页面信息时在该次 launch 设置 observe，顺带查看实际前台和目标页，不另加默认启动验收。招商银行主应用与掌上生活信用卡应用是两个应用。

- `source=auto`：先读取已选设备的安装列表（本地缓存 300 秒），合并本地目录。精确名称/别名优先；精确匹配存在时不混入子串候选。所有查询均在本地完成。
- `source=installed`：只查已选 iPhone，缺少选定设备或读取失败时返回可执行的诊断。英文品牌别名可用本地目录映射到安装列表的 bundle ID。
- `source=catalog`：离线查本文件和 `apps.json` 中 36 个经过 Apple 查询核验的应用。完全不查询 iPhone 或网络。

`installed_verified=true` 表示选定设备安装列表确认了候选，`installation_checked` 表示本次查询是否成功获取过安装列表（最多缓存五分钟）；false 不能独立解释为未安装。候选中 `verified_at` 是来源核验时间。查询只返回匹配应用，不回传整份设备清单。设备安装清单和缓存保存在仓库外的私有状态目录，权限为 600；不会将设备信息或安装清单发送给 Apple。

## 无匹配时

核对应用名称或 bundle ID，再用已连接 iPhone 的安装列表确认。保留查询词在本地，只使用设备和包内目录。

若 MCP 查询本身不可用，可用固定的 Xcode 命令直接读取本地安装列表（`--include-all-apps` 必须保留：devicectl 默认仅显示开发应用），在本地过滤目标名称/bundle ID 后启动。下一步所需观察也可顺带判断启动状态。文件写到仓库外私有目录，不保存完整安装清单到项目：

```sh
xcrun devicectl device info apps --device "<已选设备 UDID>" --include-all-apps --json-output "<私有目录>/apps.json" --timeout 8
```

## 已核验目录

每条记录的实际 Apple API URL、商店名称、发布者、国家/地区与 UTC 核验时间见 [apps.json](apps.json)。下面只列品牌、bundle ID 和查询地区；商店记录不证明设备安装状态。

| 应用 | bundle ID | 核验商店 |
| --- | --- | --- |
| 微信 | `com.tencent.xin` | [CN](https://apps.apple.com/cn/app/id414478124) |
| 支付宝 | `com.alipay.iphoneclient` | [CN](https://apps.apple.com/cn/app/id333206289) |
| 淘宝 | `com.taobao.taobao4iphone` | [CN](https://apps.apple.com/cn/app/id387682726) |
| 京东 | `com.360buy.jdmobile` | [CN](https://apps.apple.com/cn/app/id414245413) |
| 拼多多 | `com.xunmeng.pinduoduo` | [CN](https://apps.apple.com/cn/app/id1044283059) |
| 小红书 | `com.xingin.discover` | [CN](https://apps.apple.com/cn/app/id741292507) |
| 抖音 | `com.ss.iphone.ugc.Aweme` | [CN](https://apps.apple.com/cn/app/id1142110895) |
| 快手 | `com.jiangjia.gif` | [CN](https://apps.apple.com/cn/app/id440948110) |
| 哔哩哔哩 | `tv.danmaku.bilianime` | [CN](https://apps.apple.com/cn/app/id736536022) |
| 微博 | `com.sina.weibo` | [CN](https://apps.apple.com/cn/app/id350962117) |
| QQ | `com.tencent.mqq` | [CN](https://apps.apple.com/cn/app/id444934666) |
| QQ音乐 | `com.tencent.QQMusic` | [CN](https://apps.apple.com/cn/app/id414603431) |
| 网易云音乐 | `com.netease.cloudmusic` | [CN](https://apps.apple.com/cn/app/id590338362) |
| 百度地图 | `com.baidu.map` | [CN](https://apps.apple.com/cn/app/id452186370) |
| 高德地图 | `com.autonavi.amap` | [CN](https://apps.apple.com/cn/app/id461703208) |
| 滴滴出行 | `com.xiaojukeji.didi` | [CN](https://apps.apple.com/cn/app/id554499054) |
| 美团 | `com.meituan.imeituan` | [CN](https://apps.apple.com/cn/app/id423084029) |
| 饿了么 | `me.ele.ios.eleme` | [CN](https://apps.apple.com/cn/app/id507161324) |
| 携程旅行 | `ctrip.com` | [CN](https://apps.apple.com/cn/app/id379395415) |
| 飞猪 | `com.taobao.travel` | [CN](https://apps.apple.com/cn/app/id453691481) |
| 铁路12306 | `cn.12306.rails12306` | [CN](https://apps.apple.com/cn/app/id564818797) |
| 百度网盘 | `com.baidu.netdisk` | [CN](https://apps.apple.com/cn/app/id547166701) |
| 腾讯会议 | `com.tencent.meeting` | [CN](https://apps.apple.com/cn/app/id1484048379) |
| 钉钉 | `com.laiwang.DingTalk` | [CN](https://apps.apple.com/cn/app/id930368978) |
| 飞书 | `com.bytedance.ee.lark` | [CN](https://apps.apple.com/cn/app/id1401729613) |
| 企业微信 | `com.tencent.ww` | [CN](https://apps.apple.com/cn/app/id1087897068) |
| 招商银行 | `com.cmbchina.MPBBank` | [CN](https://apps.apple.com/cn/app/id392899425) |
| 掌上生活 | `com.cmbchina.cmblife` | [CN](https://apps.apple.com/cn/app/id398453262) |
| 中国工商银行 | `com.icbc.iphoneclient` | [CN](https://apps.apple.com/cn/app/id423514795) |
| 中国建设银行 | `com.ccb.ccbDemo` | [CN](https://apps.apple.com/cn/app/id391965015) |
| 中国农业银行 | `com.bankabc.iphonerelease` | [CN](https://apps.apple.com/cn/app/id515651240) |
| 中国银行 | `com.boc.BOCMBCI` | [CN](https://apps.apple.com/cn/app/id399608199) |
| 雪球 | `com.xueqiu` | [CN](https://apps.apple.com/cn/app/id492180369) |
| 同花顺 | `cn.com.10jqka.IHexin` | [CN](https://apps.apple.com/cn/app/id303191318) |
| 东方财富 | `com.eastmoney.iphone` | [CN](https://apps.apple.com/cn/app/id423525686) |
| 富途牛牛 | `cn.futu.FutuTraderPhone` | [HK](https://apps.apple.com/hk/app/id592031984) |
