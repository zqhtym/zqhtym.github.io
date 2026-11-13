# IPTV 直播源检测工具

从本地和远程直播源中收集频道，依次做黑名单过滤、去重、404 检测、测速、画面/声音检测，
最后按分类模板生成可直接订阅的播放列表（txt + m3u）。整个流程由 GitHub Actions 定时运行，结果自动提交回仓库。

## 检测流程

流程拆成三个脚本，由工作流驱动，通过 `output/` 下的步骤文件衔接：

| 脚本 | 步骤 | 输入 | 输出 |
| --- | --- | --- | --- |
| `first.py` | Step1 加载资源 | `resources.m3u`、`resources.txt`、`resources_remote.txt`（远程源地址列表） | `output/step1_all_resources.csv` |
| | Step2 黑名单过滤 + 去掉 URL 中 `$` 之后的注释 | `black.txt` | `output/step2_deblack_deAnnotation.csv` |
| | Step3 URL 去重 | | `output/step3_unique_resources.csv` |
| | Step4 可访问性检测（先 HEAD，出错或不是 2xx/3xx 时再用 GET 确认） | | `output/step4_valid_resources.csv` |
| | Step5 测速，保留 >= 0.2 MB/s | | `output/step5_speed_resources.csv` |
| `second.py` | Step6 画面变化与声音检测（OpenCV + FFmpeg），分两部分运行 | `step5_speed_resources.csv` | `output/step6_part1.csv`、`output/step6_part2.csv` |
| `third.py` | Step7 合并 Step6 各部分，按模板分类，合并白名单 | `step6_part*.csv`、`name_filtering_rules.txt`、`white.txt` | `output/LE.txt`、`output/LU.txt` |
| | Step8 转换成 m3u | | `output/LE.m3u`、`output/LU.m3u` |

## 输出结果

最新结果都在 `output/` 目录下：

- `LE.txt` / `LE.m3u`：速度 >= 1.0 MB/s 的频道
- `LU.txt` / `LU.m3u`：速度 >= 0.2 MB/s 的频道

说明：

- 只收录频道名能匹配 `name_filtering_rules.txt` 中某个关键词的频道；分类顺序、分类内的频道顺序都按模板中关键词的顺序排列，CCTV 频道再按编号排序。
- `white.txt` 中的白名单频道不做检测，按 5 MB/s 计入，LE 和 LU 都会收录。
- 仓库根目录下的 `LE.*` / `LU.*` 是 2026 年 4 月的旧文件，已不再更新，请使用 `output/` 下的文件。
- 如果仓库开启了 GitHub Pages，可以直接订阅 `https://zqhtym.github.io/output/LE.m3u` 这样的地址。

## 配置文件

| 文件 | 作用 | 格式 |
| --- | --- | --- |
| `resources.m3u` / `resources.txt` | 本地直播源 | m3u，或每行 `名称,URL` |
| `resources_remote.txt` | 远程直播源列表，Step1 会逐个下载 | 每行一个 URL |
| `black.txt` | URL 黑名单，URL 包含其中任意一行即被过滤 | 每行一个关键字 |
| `white.txt` | 白名单频道，不检测直接收录 | 每行 `名称,URL` |
| `name_filtering_rules.txt` | 分类模板 | `分类名,#genre#` 行开始一个分类，下面每行一个频道名关键词 |

## 本地运行

```bash
pip install -r requirements.txt

python first.py          # Step1 ~ Step5（也可以用 --step1 ... --step5 单独运行某一步，--all 运行全部）
python second.py         # Step6，一次检测全部，写出 step6_part1.csv 和 step6_part2.csv
python second.py --part 1   # 只检测第 1 部分（GitHub Actions 上就是这样分开跑的）
python third.py          # Step7 ~ Step8
```

- Step6 需要 FFmpeg：Windows 下可以把 `ffmpeg.exe` 放在项目根目录（已在 `.gitignore` 中忽略），其他系统使用 PATH 里的 `ffmpeg`。
- 在终端里运行 `first.py` 时，Step1 会逐个询问是否处理远程源（回车处理、`skip` 跳过、`auto` 自动处理剩余、`quit` 退出）；非交互环境下自动全部处理。

`second.py` 支持以下环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VIDEO_CHECK_TIMEOUT` | 15 | 单个视频读帧检测时长（秒） |
| `VIDEO_TOTAL_TIMEOUT` | 180 | 单个 URL 检测总超时（秒） |
| `GITHUB_ACTIONS_WORKERS` | 3 | GitHub Actions 上的并发数（本地按 CPU 核数自动决定） |

## GitHub Actions

| 工作流 | 运行脚本 | 定时（UTC / 北京时间） | push 触发文件 |
| --- | --- | --- | --- |
| `first-only.yml` | `first.py` | 每周一 22:00 / 周二 06:00 | `first.py`、`utils/step_io.py`、`iptv_checker.py`、`resources.*`、`resources_remote.txt`、`white.txt`、`requirements.txt` |
| `second-part1.yml` | `second.py --part 1` | 每天 15:00 / 23:00 | `second.py`、`iptv_checker.py`、`utils/video_check_worker.py`、`utils/step_io.py`、`requirements.txt` |
| `second-part2.yml` | `second.py --part 2` | 每天 21:00 / 次日 05:00 | 同上 |
| `third-only.yml` | `third.py` | 每天 04:00 / 12:00 | `third.py`、`utils/step_io.py`、`iptv_checker.py`、`requirements.txt` |

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
