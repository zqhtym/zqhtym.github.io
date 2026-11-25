# IPTV 直播源检测工具

从本地和远程直播源中收集频道，依次做黑名单过滤、按分类模板筛选、去重、404 检测、测速、画面/声音检测，
最后按分类模板生成可直接订阅的播放列表（txt + m3u）。整个流程由 GitHub Actions 定时运行，结果自动提交回仓库。

## 检测流程

流程拆成三个脚本，由工作流驱动，通过 `output/` 下的步骤文件衔接：

| 脚本 | 步骤 | 输入 | 输出 |
| --- | --- | --- | --- |
| `first.py` | Step1 加载资源 | `resources.m3u`、`resources.txt`、`resources_remote.txt`（远程源地址列表） | `output/step1_all_resources.csv` |
| | Step2 拆开 `url1#url2` 多源写法 + 黑名单过滤 + 去掉 URL 中 `$` 之后的注释 | `black.txt` | `output/step2_deblack_deAnnotation.csv` |
| | Step3 只保留模板会收录的频道 + URL 去重（每个 URL 只留一个名称） | `name_filtering_rules.txt` | `output/step3_unique_resources.csv` |
| | Step4 可访问性检测（先 HEAD，出错或不是 2xx/3xx 时再用 GET 确认） | | `output/step4_valid_resources.csv` |
| | Step5 测速，保留 >= 0.2 MB/s | | `output/step5_speed_resources.csv` |
| `second.py` | Step6 画面变化与声音检测（OpenCV + ffprobe），分两部分运行；淘汰打不开的流，以及静止画面且没有声音的流 | `step5_speed_resources.csv` | `output/step6_part1.csv`、`output/step6_part2.csv` |
| `third.py` | Step7 合并 Step6 各部分，按模板分类，合并白名单 | `step6_part*.csv`、`name_filtering_rules.txt`、`white.txt` | `output/LE.txt`、`output/LU.txt` |
| | Step8 过滤成人内容（分类名以 🔞 开头的分类），转换成 m3u | | `output/LE.m3u`、`output/LU.m3u`；成人内容写到 `LX.txt`、`LX.m3u`，不提交到本仓库，推送到私有仓库 |

## 输出结果

最新结果都在 `output/` 目录下：

- `LE.txt` / `LE.m3u`：速度 >= 1.0 MB/s 的频道
- `LU.txt` / `LU.m3u`：速度 >= 0.2 MB/s 的频道

说明：

- 只收录频道名能匹配 `name_filtering_rules.txt` 中某个关键词的频道；分类顺序、分类内的频道顺序都按模板中关键词的顺序排列，CCTV 频道再按编号排序，同名频道按速度从快到慢排列。
- 英文关键词前面不能紧挨着字母，数字开头的关键词前面不能紧挨着数字（`HOT` 不会命中 `Schlosshotel`，`4k` 不会命中 `24KZ`）。
- 同一个 URL 只收录一次。
- 模板在 Step3 就生效：**新增关键词**要等下一次 `first.py` → `second.py` → `third.py` 跑完才会出现频道（推送模板会自动触发 `first.py`）；删除关键词在下一次 `third.py` 就生效。
- `white.txt` 中的白名单频道不做测速和画面检测，按 5 MB/s 计入，LE 和 LU 都会收录；只有确定失效的（两次都是 404/410，或域名无法解析）才不收录。
- 仓库根目录下的 `LE.*` / `LU.*` 是 2026 年 4 月的旧文件，已不再更新，请使用 `output/` 下的文件。
- 如果仓库开启了 GitHub Pages，可以直接订阅 `https://zqhtym.github.io/output/LE.m3u` 这样的地址。

## 配置文件

| 文件 | 作用 | 格式 |
| --- | --- | --- |
| `resources.m3u` / `resources.txt` | 本地直播源 | m3u，或每行 `名称,URL` |
| `resources_remote.txt` | 远程直播源列表，Step1 会逐个下载 | 每行一个 URL |
| `black.txt` | URL 黑名单，URL 包含其中任意一行即被过滤 | 每行一个关键字 |
| `white.txt` | 白名单频道，除非确定失效，否则直接收录 | 每行 `名称,URL` |
| `name_filtering_rules.txt` | 分类模板 | `分类名,#genre#` 行开始一个分类，下面每行一个频道名关键词；`url:xxx` 表示 URL 包含 xxx 的都归入该分类，优先于频道名关键词。分类名写成 `名称_密码` 时，影视（FongMi）、TVBox 等播放器会要求输入密码。分类名以 🔞 开头的是成人分类，它的关键词优先于其他分类，只进入 LX |

## 本地运行

```bash
pip install -r requirements.txt

python first.py          # Step1 ~ Step5（也可以用 --step1 ... --step5 单独运行某一步，--all 运行全部）
python second.py         # Step6，一次检测全部，写出 step6_part1.csv 和 step6_part2.csv
python second.py --part 1   # 只检测第 1 部分（GitHub Actions 上就是这样分开跑的）
python third.py          # Step7 ~ Step8
```

- Step6 的声音检测需要 `ffprobe`（FFmpeg 自带）：Windows 下可以把 `ffprobe.exe` 放在项目根目录（已在 `.gitignore` 中忽略），其他系统使用 PATH 里的 `ffprobe`。没有 `ffprobe` 时不判断声音。
- 在终端里运行 `first.py` 时，Step1 会逐个询问是否处理远程源（回车处理、`skip` 跳过、`auto` 自动处理剩余、`quit` 退出）；非交互环境下自动全部处理。

### 结果骤降保护

出现以下情况时脚本以非 0 状态退出（工作流显示失败），并保留上一次的结果不覆盖：

- Step1 加载的数量、Step7 的 LE / LU 条数不到上一次的一半
- Step4、Step5 通过率低于 20%，Step6 通过率低于 35% 或不到上一次的一半

确认是正常变化时，设置环境变量 `SKIP_DROP_CHECK=1` 再运行；在 GitHub Actions 上手动运行工作流并勾选“跳过结果骤降检查”。

`second.py` 支持以下环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VIDEO_CHECK_TIMEOUT` | 15 | 单个视频读帧检测时长（秒） |
| `VIDEO_TOTAL_TIMEOUT` | 180 | 单个 URL 检测总超时（秒） |
| `GITHUB_ACTIONS_WORKERS` | 3 | GitHub Actions 上的并发数（本地按 CPU 核数自动决定） |

## 成人内容（LX）

`third-only.yml` 会把 `LX.txt`、`LX.m3u` 推送到私有仓库 `zqhtym/translate`，需要在本仓库的 Actions secrets 里配置 `LX_DEPLOY_KEY`（`translate` 仓库里一个有写权限的 Deploy Key 的私钥）；没有配置时跳过推送。名称指向未成年人或非自愿内容的条目不会收录到任何列表。

## GitHub Actions

| 工作流 | 运行脚本 | 定时（UTC / 北京时间） | push 触发文件 |
| --- | --- | --- | --- |
| `first-only.yml` | `first.py` | 每周一 22:00 / 周二 06:00 | `first.py`、`utils/step_io.py`、`utils/name_rules.py`、`resources.*`、`resources_remote.txt`、`black.txt`、`name_filtering_rules.txt`、`requirements.txt` |
| `second-part1.yml` | `second.py --part 1` | 每天 15:00 / 23:00 | `second.py`、`iptv_checker.py`、`utils/video_check_worker.py`、`utils/step_io.py`、`utils/name_rules.py`、`requirements.txt` |
| `second-part2.yml` | `second.py --part 2` | 每天 21:00 / 次日 05:00 | 同上 |
| `third-only.yml` | `third.py` | 每天 04:00 / 12:00 | `third.py`、`utils/step_io.py`、`utils/name_rules.py`、`white.txt`、`requirements.txt` |

所有工作流都支持在 Actions 页面手动运行（workflow_dispatch），运行完会把结果文件提交回 `main` 分支；
推送前会先 `git pull --rebase`，失败时重试 3 次，仍失败则该次运行标记为失败。

**Step6 为什么分两部分**：GitHub Actions 单个 job 最长运行 6 小时。Step6 按 URL 的 CRC32 分成两半
（规则见 `utils/step_io.py` 的 `step6_part_of`，与 step5 文件中的顺序无关），两个工作流错开 6 小时启动，
各自只检测一半，各自写自己的部分文件；third.py 合并所有部分。某一部分某天没跑完，third.py 会用该部分上一次的结果。
如果以后一半也跑不完，把 `STEP6_PARTS` 改成 3，并照着 `second-part2.yml` 加一个 `second-part3.yml` 即可。

## 项目结构

```
├── first.py                    # Step1 ~ Step5
├── second.py                   # Step6（--part N 只检测第 N 部分）
├── third.py                    # Step7 ~ Step8
├── iptv_checker.py             # Step6 画面检测的调度（并发、分批、结果解析）
├── utils/
│   ├── step_io.py              # 步骤文件读写等公共函数
│   ├── video_check_worker.py   # 单个 URL 的画面/声音检测（每个 URL 一个独立进程）
│   └── txt_to_m3u8b.py         # txt 转 m3u
├── name_filtering_rules.txt    # 分类模板
├── black.txt / white.txt       # 黑名单 / 白名单
├── resources.m3u / resources.txt / resources_remote.txt   # 直播源
├── output/                     # 各步骤输出和最终播放列表
└── .github/workflows/          # 定时工作流（first / second-part1 / second-part2 / third）
```

## 许可证

本项目基于 MIT 许可证开源。

## 致谢

- [IPTV-API](https://github.com/Guovin/iptv-api) - 提供框架基础
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理工具
- [OpenCV](https://opencv.org/) - 计算机视觉库
