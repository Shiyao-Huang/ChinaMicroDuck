---
原文路径: 01_official/microduck/docs/robot/cheatsheet.md
源仓库: https://github.com/pollen-robotics/microduck
许可证: Apache-2.0
翻译日期: 2026-09-02
---

# 速查表（Cheat sheet）

`robotctl`，运行在机器人上。这里的每一条命令都取自交付它的那条分支上的 `--help` 输出，而不是凭记忆写的。

只读命令不需要特权。任何**改动**机器人的操作都需要 `sudo`（对 `configd` 而言，是 `--allow-user`/`--allow-group` 里的用户；对 `updaterd` 而言，是 `updater.toml` 里的 `allow_uids`/`allow_gids`）。

分支构建、发布候选（release candidate）以及更新之后的重启陷阱，见 [`cheatsheet-dev.md`](cheatsheet-dev.md) —— 它们需要一块开发板。不用网络也不用 ssh、从笔记本通过蓝牙操作同一只机器人，则见 [`duckctl.md`](duckctl.md)。

## 在机器人上 —— `robotctl`

### 最先该跑的命令

```
robotctl version
```

每个守护进程*正在运行的*版本对照*已安装的*版本，两者不一致时给出警告。在相信任何其他诊断之前先跑这个 —— 更新之后还在服务旧代码的守护进程，看上去和你刚发布的修复里的 bug 一模一样。见下文"更新之后"。

```
robotctl health
```

硬件和软件汇成一份报告。机器人不健康或不可达时以非零值退出，因此可以拿它给脚本把关 —— 电机过热或组件被固定（pinned）这类情况只被报告、不被裁决，也不影响退出码。`--json` 用于生成支持包（support bundle）。

### 观察控制环

```
robotctl monitor
```

客户端请求的目标与实际施加的值并排显示，两者不一致时把原因写明 —— 安全层随时都在钳制（clamp），少了这一点，"摇杆推前进了、机器人却不动"就没法读。限位是把话完整说出来而不是只起个名字：`deadman — no intent arrived recently, velocity zeroed`（死人开关 —— 最近没有收到意图，速度已清零）。

画面上还有：每个关节的实测值对照指令值、IMU 的投影重力（projected gravity）以及由它得出的摔倒判定（fall verdict）、以及以轨迹（trace）形式呈现的实际控制环频率，这样一次已经恢复的卡顿仍看得见。投影重力是这条流上唯一的 IMU 量 —— 直立时约为 `[0, 0, -1]`，`fallen` 就是由它判定的。过期读取（stale read）计数器，以及让这些数字有意义的比率，在 `robotctl health` 里。

表头最后一行是机器人的状态（condition）而非行为：电池组的电压与电量百分比、最热的舵机和板子自身的温度。数据来自 `robot.health`，每两秒轮询一次，因为这些都不在状态流上 —— 而且任何异常都在这里被点名，无论是 `unhealthy: control loop at 43.9 Hz`、`degraded: no robot on the motor bus after 3 attempts` 还是 `orientation frozen — 25 stale reads`。最后那条只出现在这一行、画面其他任何地方都没有：一块停止融合（fusing）的板子仍会应答总线，所以什么都不报错，而上面的重力向量会无限期地保持一个貌似合理的姿态。

0% 对应 `BATTERY_EMPTY_V`，到了这一点 `robotd` 会让机器人坐下并断电，所以这个数字是倒计时而不是油量表 —— 30% 变黄，15% 变红。还没取到的读数会显示 `batt not read yet` 而不是 `0.00 V` —— 开机后的第一秒和一条无法应答的总线，看起来都是这个样子。即使完全没有任何状态，这一行也照画不误，而这恰恰是它最要紧的场景：一块舵机电源关闭的板子永远完不成一次控制 tick，所以流上什么都不到达，原因只存在于健康应答里。

底部边栏写明已加载的策略（policy）—— 那些 `.onnx` 文件，以及究竟有没有配置站立网络 —— 因为 `walk` 是两个步态（gait）不同的发布版本都会报告的模式。没有策略的机器人会直说，策略加载失败的机器人会说那件事，而这是状态流的 `held` 无法区分的。

沿右侧往下，是**按当前站姿绘制的机器人** —— 与策略训练时相同的可视化模型，由实测关节角度摆出姿势、按 IMU 的重力向量倾斜。一条折错方向的腿、一个扎进地板的头、一只侧躺的鸭子，在关节表里都只是数字；在这里每一个都一目了然。它默认开启，只要终端够宽（约 110 列 —— 表格优先，机器人占用剩余空间）就会出现。**`d`** 关闭它；**`[`** 和 **`]`**，或 `←`/`→`，旋转视角。

只要 ToF 在出帧，它看到的东西就会画进同一个场景 —— 命中为黄色、地面为绿色 —— 并对机器人自身做深度测试（depth test），所以喙后面的点会被喙挡住。正是这一点让"它看到的是我的手，还是它自己"变得可以回答。不需要任何按键：帧到来时点出现，帧停止时点消失。

在它下面，只要列够高，还有**一张机器人去过哪里的地图**：里程计（odometry）依据足部触地和 IMU 画出的轨迹，用盲文点阵（braille）渲染。面板永不变大 —— 轨迹变长时视野随之缩小，所以整条路径始终留在画面内。`+` 是起点，`●` 是机器人、带一条表示朝向的短线，屏幕上方对应开机时的朝向。没有磁力计（magnetometer），所以这是相对运动、会漂移；它回答"它是不是绕了一圈"，而不是"它在哪"。

`q` 退出；`↑`/`↓` 在放不下完整关节列表的短窗口里滚动列表；`u` 在角度与弧度之间切换；`t` 打开 [ToF 矩阵](#the-tof-sensor-tofd)；`d` 开关机器人视图，`[` / `]` 旋转视角；`p` 打开手柄的原始输入流 —— 手柄的每一份 evdev 报告，连同它们之间的间隔，这是无线链路卡住时唯一可见的地方（[配对手柄](pair-a-gamepad.md#when-it-drops-while-you-are-driving)）。屏幕上的角度一律是角度制 —— 关节、头部和偏航角速度。重定向或接管道时则改为每个 tick 打印一行，所以 `> run.log` 和 `| grep FALLEN` 都能正常工作，而且无论屏幕设置如何，这些数字始终保持弧度。关节向量在 `--json` 里，它携带完整状态，每行一个对象：

```
robotctl monitor --json --hz 50 > run.jsonl
```

### 配置机器人

```
sudo robotctl configure
```

一个作用于 `/etc/robot/robotd.toml` 的交互式编辑器：守护进程认识的每一个键，功能开关排在最前（策略开/关、walk/roller、跌倒瘫软、音频、宠物检测、电池关机、摄像头与视频画质……），当前值对照默认值，附一行说明。空格键（SPACE）切换，回车键（ENTER）输入值，`u` 把某个键恢复为默认值。黄色的值（标着 `•`）是这台机器人偏离了默认值的键；其余都是内置默认值，`unset` 的可选项会显示它们实际解析出的值 `(auto)`。

三个值得信赖的性质：

- **它不可能和守护进程不一致。** 模式（schema）、默认值和校验全部来自 `robotd` 解析该文件所用的同一个 crate，而且键清单由一个测试钉死为完整的 —— 守护进程里新增的 `[section]` 要么出现在这里，要么构建失败。
- **它不可能吃掉你的文件。** 注释、键的顺序和其他版本写入的键都原样保留；只有你改过的键才会被写入。把某个键恢复默认会把它（连同附着在它上面的注释）删掉，而不是把默认值写死，所以这个文件始终是一份*决策*清单，而不是默认值的副本。
- **它不可能写出一份 robotd 拒绝启动的文件。** 每次保存都先通过守护进程自己的加载器校验，原子完成（临时文件 + 改名），不通过则连同原因一起拒绝。

守护进程只在启动时读一次该文件，所以保存时会提议重启 —— 只重启读取了你所改内容的那几个：`[media]` 归 `mediad`，其余归 `robotd`。要 `sudo`，因为文件属主是 root —— 不加的话编辑器以只读打开，并在第一次写入时说明这一点。`--file` 可以把它指向别处，用于台架上的副本。随版本发布的 `deploy/robotd.toml` 仍然是每个旋钮*为什么存在*的参考；这个编辑器是用来拨动它们的。

#### 视频画质

```
sudo robotctl configure
```

设置 `media.quality` —— `1080p30`、`720p30`、`720p15` 或 `360p30` —— 然后接受它提议的重启。关掉 `media.camera` 会改为推流测试图（test pattern），这正是没装摄像头的板子想要的：WebRTC 的*控制*通道搭载在视频轨上，起不来的流水线会把两者一起赔掉。`media.bitrate` 若不手动设置会跟随画质；单位是比特每秒。

`media.congestion_control` 是该小节的另一个旋钮，也是真正影响 CPU 的那个：设为 `disabled` 会去掉带宽估计器（bandwidth estimator），它是 `mediad` 里最大的单项消耗（占一个核的 7.6%，采集只占 0.3%），并让 `media.bitrate` 成为固定码率而非起点。代价是自适应性 —— 链路劣化时，画面会卡住，而不是码率降下来。

720p30 是流水线实测过的档位；撑不住的档位会变慢而不是直接失败。`robotctl monitor` 在底部边栏报告实际达到的帧率，低于所要求的 90% 时以黄色显示并附上 `of <target>`。实际生效的配置：

```
journalctl -u mediad -b | grep streaming
```

#### 你自己的策略

试用一个网络不需要发布一个版本。在板子上的 `/etc/robot/robotd.toml` 里把 `robotd` 指向你自己的 `.onnx`：

```toml
[policy]
walk = "/home/radxa/my_walking.onnx"
stand = "/home/radxa/my_stand.onnx"
```

```
sudo systemctl restart robotd
```

你的路径在更新后依然保留 —— 发布版本替换的是二进制和它自带的策略，而不是那个指向别处的文件。删掉这几行就回到随版本发布的策略。

加载失败的策略会报告 **unhealthy**，`robotctl health` 和 `monitor` 的底部边栏都会点名原因。策略必须满足的形状（shape），以及加载时还会检查什么，见 [`../design/robotd-design.md`](../design/robotd-design.md) §2.3。

### 给关节上电（`robotd`）

```
sudo robotctl robot init
```

```
sudo robotctl robot relax --yes
```

`init` 给关节上电，并在约两秒内渐变到归位姿势（home pose）—— **它会动每一个关节**，所以先把机器人放回它的支架上。它不需要策略，手柄的 Start 键在进入驾驶之前做的就是这件事，所以手动执行属于台架操作。

`relax` 切断电源，若没有东西扶着，**机器人会瘫倒**，所以它要求 `--yes`。除了拔插头，这是回到瘫软（limp）状态的唯一途径：再按一次 Start 会停掉策略并让机器人保持站立，`robot.stop` 则在保持站立的同时把速度清零。

两者都经由 `robotd`，它独占电机总线。`robotd init` —— 这个子命令 —— 仍为守护进程没在运行的机器人保留，而且需要先把守护进程停掉，因为一条 UART 上两个写入方会互相破坏对方的应答：

```
sudo systemctl stop robotd && sudo /opt/robot/daemon/current/bin/robotd init && sudo systemctl start robotd
```

无论机器人有没有摔倒，`init` 都能用 —— 默认情况下摔倒只是一份*报告*（在 `robotctl monitor` 里可见），不是一道闸门，与原型一致。在 `robotd.toml` 里设置了 `[safety] fall_limp` 或 `fall_recover` 的板子会启用闸门：摔倒的机器人会瘫软，并拒绝 `init`/`enable`/技能，直到被扶起来。

### 手柄（`configd`）

```
robotctl pad status
```

```
sudo robotctl pad pair
```

```
sudo robotctl pad pair 78:86:2E:BB:13:28
```

```
sudo robotctl pad forget 78:86:2E:BB:13:28
```

配对每个手柄只做一次，且有专门的页面 ——
[`pair-a-gamepad.md`](pair-a-gamepad.md)：哪个按键让手柄进入配对模式、在不清除第一个的情况下添加第二个手柄、以及连不上时怎么办（多数时候答案是 `/etc/bluetooth/main.conf` 里的 `Privacy` 设置）。

`padd.service` 从开机就运行，并驱动任何连上的手柄，所以配对是唯一的步骤。映射沿用原型的，肌肉记忆可以直接迁移：

| control | does |
| --- | --- |
| left stick | drive: forward/back and strafe · head: head yaw and pitch · body pose: up and crouch |
| right stick | drive: turn · head: neck pitch and head roll · body pose: pitch and roll |
| **Start** | toggle the policy — nothing moves until it is on |
| **Y** / triangle | head mode: sticks pose the head (body holds still) |
| **B** / circle | body-pose mode: sticks lean and crouch the standing robot |
| **A** / cross | ground pick |
| **X** / square | roulade — one forward roll; hold to chain rolls |
| **LB / RB** | left / right kick |
| **DPad-Down** | sit ↔ stand |
| **RT / LT** | mouth (either trigger) — RT also quacks; LT rides the "wheee" while held |
| **DPad-Up**, held 3 s | switch drive mode, walk ⇄ roller |
| **Select**, held 2 s | sit down, then power off |

没有停止键：松开摇杆机器人就站住，`padd` 死掉时 `robotd` 的死人开关（deadman）会让它停下。在轮式机器人（`robotd.toml` 里 `mode = "roller"`）上，摇杆自动采用轮式整形 —— 非对称的推进/制动、无横移 —— A 键触发下蹲。其他技能照常可用：坐下、踢腿和侧滚（roulade）在轮子上也能做，与原型一致。

**长按十字键上（DPad-Up）可在两者之间切换**，用于刚给鸭子装上轮子或拆下轮子的时候：机器人嘎一声表示步行模式、嘎两声表示轮式模式，回到归位姿势，在那里加载该模式的策略并重新开始驾驶 —— 几秒钟，全程保持力矩，无需重启。`robotd.toml` 不会被改动，所以重启后仍回到配置中的模式；用 `robotctl configure`（或 `[policy] mode`）可以把改动固定下来。用长按而不是点按，是因为驾驶时十字键上很容易被误压。

`pad status` 把两个问题分开回答，因为"手柄已连接"和"驱动已死"从外面看一模一样：

```
pad     Xbox Wireless Controller 78:86:2E:BB:13:28  connected
padd    active — driving whatever pad connects
```

想用非默认限值驾驶，先停掉服务，否则两个进程会抢摇杆：

```
sudo systemctl stop padd
```

```
sudo -u padd /opt/robot/daemon/current/bin/padd --max-linear 0.25
```

当怀疑对象是链路本身时，实时看它 —— `robotctl monitor`，然后按 `p`。没有机器人也能用：在舵机未上电或 `robotd` 已停止的板子上，监视器会打开手柄区块而不是拒绝启动。想要一段时间窗口内的判定，则把这个仓库克隆里的测量脚本拷过去：

```
scp scripts/pad-link-test.sh radxa@<board>:/tmp/
```

已经落在 `padd` 日志里的掉线记录 —— 不需要手柄，立刻有答案：

```
sudo sh /tmp/pad-link-test.sh --history
```

或者现在就测，整整两分钟内让摇杆一直动：

```
sudo sh /tmp/pad-link-test.sh
```

它统计掉线并对照内核为每次给出的原因，还测量手柄各次输入报告之间的间隔 —— 那是 `padd` 看不见的故障：链路还在，机器人却按一条过期指令继续走。[`pair-a-gamepad.md`](pair-a-gamepad.md#when-it-drops-while-you-are-driving) 负责解读这些数字。

当两块板子对同一只手柄表现不同时，差异在它底下的协议栈：

```
scp scripts/pad-stack-report.sh radxa@<board>:/tmp/
```

```
sudo sh /tmp/pad-stack-report.sh
```

内核、BlueZ、控制器固件、LE 还是 BR/EDR、以及手柄自己的固件修订版 —— 打印出来并存到 `/tmp/pad-stack-<host>-<when>.log`。`--fingerprint` 只打印两块板子之间必须一致的值，供 `diff` 使用。
[`pair-a-gamepad.md`](pair-a-gamepad.md#is-this-board-running-the-same-stack-as-that-one) 有对比方法。

### 嗓音

```
robotctl quack
```

分辨鸭子最响亮的办法：每台机器人的音色库（voice bank）都由它的 SoC 序列号生成（`sounds ensure-bank`，每次安装发布版本时运行），所以用一副只属于它自己的嗓音应答的那台，就是你 SSH 进去的那台。没有嗓音的机器人 —— 音频关闭或没有音色库 —— 会说明情况，而不是打印代表叫声的鸭子图标，因此沉默永远意味着找错了鸭子。机器人还会在 `robotd` 起来时打招呼、断电前啄别致意，而且 —— 如果你要求 —— 在麦克风听到头顶被挠时咕咕叫。最后这个在两种模式下都默认关闭（`audio.pet_detect = true` 开启；分类器随发布版本附带）：常开的版本对每一次不经意的擦碰都咕咕叫，很快就让人腻烦。开机打招呼有自己的开关，给那些整天重启守护进程的人：

```
sudo robotctl configure
```

把 `audio.greet` 设为 `false`，保存时接受它提议的重启。这只会让那声嘎叫静音，不动触发器也不动麦克风 —— `audio.enabled = false` 做不到这一点。音频硬件的初始化 —— 编解码器（codec）驱动、overlay、混音器 —— 由 `setup-board.sh` 的音频小节完成，每块板子一次。

想试听某个嗓音或手动重新生成音色库，发布版本自带生成器：

```
/opt/robot/daemon/current/bin/sounds show
sudo /opt/robot/daemon/current/bin/sounds ensure-bank --force
```

`sounds theremin` 试听的是*实时*合成器 —— 特雷门琴（theremin）演奏所用的那个嗓音，由一段脚本化的手部扫动、按 ToF 自己的帧率驱动。`--out sweep.wav` 把它写成文件而不是播放，这样面前没有机器人也能听到嗓音的变化。

### 鸭子合唱团

```
robotctl chorale
```

房间里两只鸭子会一起唱一首四声部的曲子；后来的鸭子加入它们发现已经在进行的演唱。一直运行到 Ctrl-C。`--off` 停掉其中一只。

**默认关闭** —— `robotd.toml` 里的 `[chorale] accept`，而且必须给每一只应该参加的鸭子都设置。合唱会动嘴也会动头，所以一只因为别的鸭子走进来就开始表演的鸭子，做的动作没有人要求过。关闭还意味着*不可见*：未选择加入的鸭子不会在空口上发出任何东西，而不是礼貌地拒绝。

工作原理，按问题出现的顺序：

- **没有谁负责指挥。** 两只鸭子看到相同的信标（beacon），id 较小的那只担任指挥，所以不存在会输掉的选举，也没有必须送达的消息。
- **没有共享时钟。** 板子之间既无 NTP 也无 RTC 一致性，所以指挥的节拍计数器*就是*时间基准：它每拍在一条 BLE 广播里递增一个字节，新值的到达即是强拍。跟随者对约 25 拍的相位取平均，把无线链路的抖动收进合奏所需的 ±20 ms 之内。
- **声部是推算出来的，不是分配的。** 最低位的鸭子唱低音。指挥广播名册，所有人按同一份座次各就各位 —— 这正是当两只鸭子各自只能看到房间里不同的子集时，防止它们唱同一声部的机制。
- **加入不改变任何人的声部。** 新来的鸭子接空闲的声部。离开的鸭子保留自己的*座位* —— 它的声部只是没人唱了，正如合唱团里有人走出去一样 —— 因为曲子进行到一半时，唯一值得避免的就是给剩下的人重新排座。

输出在声部一确定时就点名，所以一只鸭子最终唱了什么会留在终端回滚区里：

```
listening for other ducks — Ctrl-C to stop
  singing tenor    with 3 voices
  tenor    bar   12  beat  45.2  3 voices
```

指挥在每次演出时挑曲子，而且一场演出*会结束* —— 最后一个音符之后大家回到监听状态，重新落座，喘一口气之后再唱别的。`robotctl chorale --piece 2` 固定这台机器人**担任指挥时**挑的曲子（跟随者唱的是信标点名的曲子，所以要保证曲目就得给每只鸭子都设置）；未知 id 会被拒绝，并附上机器人的曲目单。id：1 wistful（惆怅）、2 duck-strut（鸭步）、3 outer-wilds（测试素材，不随版本发布）。`robotd` 环境里的 `DUCK_CHORALE_PIECE=<id>` 是常备的回退 —— 注意它必须设在 **robotd** 上，而不是 `robotctl` 命令行上。

手边没有任何鸭子也想听编排，一台机器就能渲染整个合唱团：

```
sounds chorale --voices 4                 # or --seeds 100,7,42 for particular ducks
sounds chorale --score my-piece.mid       # anything a notation editor exported
sounds chorale --rolloff 0                # for a full-range speaker, not a duck's
```

乐谱要么来自 `sounds/scores/*.duckscore` —— 一种面向行的文本格式，文档见 `wistful.duckscore`，它也是随版本发布的曲目 —— 要么来自 MIDI 文件，后者才是值得走的路：**MuseScore 就是乐谱编辑器。** 每个声部一件乐器、而不是一条钢琴谱，给声部命名，然后导出 MIDI。声部按平均音高匹配，所以先写高音谱的曲子仍会把低音放进低音部；一条*命名为* "Soprano" 的轨道，其名字比它的音高更可信。

### 弹奏鸭子（ToF 特雷门琴）

```
robotctl theremin
```

头部的深度传感器变成一件乐器：喙前的一只手决定音高 —— 越近越高 —— 嘴巴随音符开合，到音域顶端时张到最大。运行到 Ctrl-C，退出时把乐器放下。`--off` 放下某个客户端忘了放下的。

一种直白模式，里面没有任何取巧：开启期间，可演奏频段内最近的回波就是那只手。把鸭子指向空旷处，它安静；指向 40 cm 外的墙，它奏出稳定的音符。坐着、站着、走着都能演奏 —— 嘴不属于任何策略。

输出的最后一列是**传感器对那一帧的说法**，也是所有"它为什么不响了"的答案：

```
  0.34 m    438.1 Hz   60% ██████    14 usable · 255:38 4*:9 5*:5 1:12
```

多少个 zone 的状态是机器人相信的，然后按 ST 状态码给出计数，被相信的带 `*`。音符前的 `~` 表示它是一声*保持*音（held note），用来跨过一次传感器掉帧，而不是当下实测到的东西。

这一列之所以存在，是因为有个 bug 它本可以一分钟内发现：ST 的文档把 5 和 9 标为"距离有效"，而只相信这两个状态的构建**在大约 30 cm 之后就看不见手了** —— 再往后，移动的手以 4 或 13（*一致性失败*，sigma 过高）返回，携带的距离对音高来说完全够用。够的距离短，就往 `robotd.toml` 的 `[theremin] statuses` 里加状态码；对着空气凭空吹出幻音，就去掉几个。`hold_ms` 是防断音的：它骑过一个闪烁的 zone。

注意 `robotctl monitor` 的 ToF 网格比特雷门更严格 —— 它把 5/9 之外的一切都标成 `x`，*无法测量*。满网格的 `x` 不代表传感器坏了；只代表它对自己其实拿到的数字持悲观态度。

### ToF 传感器（`tofd`）

来自头部传感器的一个 8×8 深度矩阵。`robotctl monitor`，然后按 **`t`**：

```
┌ tof VL53L8CX · 15 Hz · 8×8 · 48/64 ranged · 0.12–3.54 m ─────────────┐
│ 0.12 0.15    x 1.44 1.86    · 2.70 3.12                              │
└ · nothing in range · x could not measure · near→far ── seq 412 · 6 ms ┘
```

距离以米为单位，近暖远冷着色。两个记号各有含义：`·` 是*测到了，量程内无物* —— 空旷空间，这本身是信息 —— 而 `x` 是*无法测量*，对那里有什么完全不置一词。把两者都显示成空白的网格会掩盖这个差别。

这是传感器自己的坐标系，不是机器人的：在运动学（kinematics）就位之前没有重投影（reprojection），这也正是让这个区块成为检查安装角度的正确位置的原因。

`tofd` 独占该传感器，没有别的进程读这条总线。它是一个普通服务 —— `sudo systemctl stop tofd` 是安全的，没有任何东西依赖它，`monitor` 会说 "no depth stream" 然后继续。它区分三种情况，因为它们需要不同的修法：

| the block says | what it means |
| --- | --- |
| `connecting to tofd…` / `no depth stream` | the daemon is not running |
| `no sensor: …` | `tofd` is up; nothing answered on the bus (most ducks) |
| `waiting for the first frame…` | a sensor is ranging; its first scan is ~66 ms away |

想手动看总线上有什么，或在没有终端界面的情况下看帧：

```
sudo i2cdetect -y -r 3
journalctl -u tofd -b
```

传感器与音频编解码器共用 I²C 总线，所以 `setup-board.sh` 的音频小节已经把总线本身配置好了；ToF 这一步只是加上稳定的 `/dev/i2c-pihat` 名字。两代传感器都支持 —— VL53L5CX 和 VL53L8CX 在板子上可互换，守护进程通过读取 ID 来选择驱动。

### 无线网络（`configd`）

```
robotctl net status
```

```
robotctl net scan
```

```
sudo robotctl net connect <ssid> --psk <passphrase>
```

```
sudo robotctl net connect <ssid> --psk-stdin
```

```
sudo robotctl net forget <ssid>
```

`--psk-stdin` 让口令不经过 `ps` —— 后者会在命令存续期内把 `--psk` 参数显示给机器上的每个用户。在任何共享机器上都优先用它。

加入一个网络**会把机器人从当前网络断开**，所以走 wifi 的 ssh 会话会掉线。这正是操作在正常工作。扫描要花几秒 —— 它等无线电完成一次扫频，而不是返回上一次扫描的结果。

### 身份与电源（`configd`）

```
robotctl system info
```

```
robotctl system pin
```

```
sudo robotctl system set-name <name>
```

```
sudo robotctl system set-pin <six-digits>
```

```
sudo robotctl system reboot
```

开箱即用时，机器人用 `duck-` 加上由自身序列号派生的四个字符称呼自己，所以两块刷了同一镜像的板子在手机的蓝牙列表里仍然不同。改名几秒内就在蓝牙上生效 —— 无需重启 —— 但手机得重新扫描才能看到。

PIN 是手机通过蓝牙认证用的。出厂默认是 `000000`，它能认证任何读过本仓库的人。

### 更新（`updaterd`）

```
robotctl update status
```

```
robotctl update check daemon
```

```
sudo robotctl update apply daemon
```

```
sudo robotctl update rollback daemon
```

```
robotctl update log
```

```
robotctl update show
```

```
robotctl update watch
```

`log` 列出历次尝试，一行一次，最新的在前；第一列是运行编号。`show` 接受其中一个编号 —— 不带编号则取最近一次 —— 打印那次运行做过的一切，然后是同一时间窗内的日志：

```
run 42 · daemon · 2025-08-27 13:06:40 UTC
  applied 0.1.3 → 0.1.4
  asked for latest, from github.com/pollen-robotics/microduck, onto 0.1.3
  requested by uid=1000 gid=1000 pid=2317

  13:06:41      +1s  manifest     0.1.4 · 184.2 MB · sha256 3f9a1c2b… · signed by release.pub · rev 88efc03
  13:06:41           downloading
  13:07:58   +1m17s  note         downloaded 184.2 MB to /opt/robot/daemon/staging/0.1.4/dl/…
  13:08:02      +4s  note         hash matches; signature verifies against release.pub
  13:08:20     +18s  pre-hook
  13:10:12   +1m52s  hook         hooks/preinstall
                                 │ onnxruntime 1.20.1 already present
                                 │ gstreamer: h264 encode ok
  13:10:12           swapping     0.1.3 → 0.1.4
  13:10:14      +1s  unit         robotd: restart
  13:10:23      +8s  health       the robot reported healthy
  13:10:24           ended        applied 0.1.3 → 0.1.4

  ── journal · 2025-08-27 13:06:40 to 2025-08-27 13:11:24 UTC ──
```

时间是 UTC，其下的日志也是。`+` 列是距上一行的时间差，找那两分钟就靠它。

读日志需要 `robot` 组所没有的特权，所以除非你是 root，后半部分会是空的。那种情况下它会打印出那条 `journalctl` 命令；在它前面加 `sudo` 就是解决办法。`--no-journal` 直接打印那条命令而不去尝试，`--json` 只给过程记录。

这里的组件（component）是 `daemon` —— 一个覆盖所有二进制的组件。`apply daemon` 安装稳定通道提供的内容；分支构建和发布候选见 [`cheatsheet-dev.md`](cheatsheet-dev.md)。

### 不下载直接切换

切到板子上已经解包好的版本。不涉及网络：

```
sudo robotctl update select daemon 0.1.4
```

```
sudo robotctl update rollback daemon
```

```
sudo robotctl update reset-to-golden daemon
```

`select` 激活一个已安装的发布版本，`rollback` 回到上一个安装的版本，`reset-to-golden` 回到从不清理的已知良好版本（golden）。

以及完全拒绝移动：

```
sudo robotctl update pin daemon 0.1.4
```

```
sudo robotctl update pin daemon
```

第二种写法解除固定。

### 当 `updaterd` 自己起不来时

上面的一切都经由 `updaterd`，所以当挂掉的守护进程正是 `updaterd` 时，它们全都用不了。先确认是哪一个：

```
systemctl status updaterd robotd btd configd
```

然后不靠它回到 golden：

```
sudo robot-rescue --dry-run
```

```
sudo robot-rescue --reboot
```

`--dry-run` 只说它会做什么，不改动任何东西。不带 `--reboot` 时它切换发布版本并打印重启命令而不是执行：每个守护进程都通过 `current` 启动，不重启就没人拿到切换结果，而一只站着的机器人应该先被接住。

未配置 golden 或 `current` 已是 golden 时，它会拒绝并说明原因 —— 如果守护进程在 golden 本身上就起不来，回滚不是答案，答案在日志里：

```
journalctl -b -u robotd -u updaterd -u btd -u configd
```

### 机器人可能已经自己处理过了

每次开机三分钟后，一个定时器会检查发布版本有没有把它的守护进程带起来，没有就退回 golden。所以一只自己重启过、跑的版本比你装的旧的机器人，多半已经自救了。它做了什么：

```
robotctl update log
```

这条记录读起来像一次回滚，失败的那个守护进程会写在原因里。想看决策过程而不是结果：

```
journalctl -b -u robot-boot-check
```

```
sudo robot-boot-check --dry-run
```

它只行动一次。第一次自救仍在记录中时会拒绝第二次 —— `updaterd` 下次启动时清除该记录，所以被拒绝意味着守护进程在 golden 上也没起来，答案是日志而不是再重启一次。看过日志并拿定主意之后，可以越过它：

```
sudo robot-rescue --force --reboot
```

### 三件容易搞错的事

**`rollback` 需要一个前身，而更新会造出一个来。** 刚配好的板子恰好只有一个发布版本，此时 `rollback` 没有更旧的版本可回，它也会这么说。自动回滚*不受*影响：应用一个发布版本是先把它解包在当前版本旁边、然后才移动 `current`，所以健康闸门运行时已有两个版本，你来的那个就是目标。`rollback_target` 选 `current` 之下、日志尚未记为坏的最高已安装版本 —— 所以只有一个版本的板子，从接受第一次更新那一刻起就受到完整保护。

唯一真正不受保护的安装是引导（bootstrap）本身，按定义它之前什么都没有。`golden` 本可以覆盖它，但在 1.0.0 出现之前有意不设置 —— 所以 `reset-to-golden` 会如实报告未配置，而不是做出令人意外的事。

**`version` 按组件显示在用的发布版本，不是发布仓库。** 无论解包了多少个版本，它永远不会列出两个。直接问仓库：

```
ls -l /opt/robot/daemon/releases/ /opt/robot/daemon/current
```

**`apply --version` 要求发布版本仍在上游存在；`select` 不要求。** 带已知坏构建的发布版本会从 GitHub 删除，所以 `apply --version 0.1.3` 故意失败，而 `select 0.1.3` 在已解包它的板子上仍然可用。这种不对称是有意的：新板子拿不到坏版本，已经拿到的板子保留逃生口。

### 无网络安装

侧载（sideload）、出厂安装，或拯救一块 `updaterd` 太旧、旧到不接受"修复太旧"那个发布版本的板子。见 [`install-dev.md`](install-dev.md) —— 用的是 `updaterd install --from`，`--force` 变体的使用条件值得先读再用。

### 日志

```
journalctl -u configd -b --no-pager | tail -40
```

```
journalctl -u btd -f
```

换成 `robotd` 或 `updaterd` 即可。`-f` 跟随输出；`-b` 只看本次开机。

启动行带着版本、git 修订号和进程启动时所在的发布目录，级别为 `warn`，所以任何日志级别下都在。

更新历史有意与日志分开 —— 每条都在 `/var/lib/robot/updater/` 下做了 `fsync` —— 所以在一台日志易失的机器人上也能活下来：

```
robotctl update log
```

最近二十次运行在那里也留有完整过程记录，位于 `runs/` 下，边发生边写入：

```
robotctl update show 42
```

两者都比版本切换、回滚和断电活得久，而这块板子上的日志做不到 —— `/var/log` 是 zram。如果坏掉的正是 `robotctl`，这些文件是换行分隔的 JSON，用 `cat` 就能读：

```
sudo cat /var/lib/robot/updater/runs/000042.jsonl
```

### Tab 补全

`install.sh` 会在 `/etc/bash_completion.d/` 里装一个加载器，向二进制本身索要补全 —— 这样补全跟着已安装的发布版本走，不会因为更新加了命令而过时。它没覆盖到的 shell，或直接从 `target/` 跑的构建：

```
eval "$(robotctl completions bash)"
```

把 `bash` 换成 `zsh`、`fish`、`elvish` 或 `powershell` 均可。
