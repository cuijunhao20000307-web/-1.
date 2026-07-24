# ldn_mitm 简体中文自动编译

这个仓库用于自动拉取官方 `ldn_mitm` 源码、应用简体中文补丁并通过 GitHub Actions 编译。

## 使用方法

1. 打开仓库顶部的 **Actions**。
2. 选择 **Build Chinese ldn_mitm**。
3. 点击 **Run workflow**。
4. 编译完成后，在运行页面底部下载：
   - `ldn_mitm-Chinese-SD`
   - `ldn_mitm-Chinese-binaries`
5. 将 SD 安装包里的 `atmosphere` 和 `switch` 文件夹复制到 Switch SD 卡根目录并覆盖。

## 汉化内容

- Tesla 浮层中的启用开关、日志开关和错误提示。
- `ldnmitm_config` 中的状态、按键和导出提示。

## 注意

- 本项目基于官方开源项目自动构建。
- 是否能正常运行取决于当前 Atmosphère、系统版本和官方源码兼容性。
- 某些 Switch 字体环境可能无法完整显示中文。
