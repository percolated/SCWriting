# SCWriting
[English](README.md)

SCWriting 是一个用于生成 [ShinyColorsDB-EventViewer](https://github.com/ShinyColorsDB/ShinyColorsDB-EventViewer) JSON 的轻量脚本语言。

## 运行方式
```bash
python script.py your_script.sc
```

输出：
- `your_script.json`

## 语句类型
各行可以是：
- 注释（`// ...`）
- 块定义（`#...` + 缩进的 key-value）
- 流程控制（`label ...:`、`jump ...`、`choice ...`）
- 命令（`@...`）
- 对话

空行会被忽略。

## 解析顺序
`script.py` 按以下顺序解析：
1. 块：`#character`、`#anim`、`#stage`、`#positions`、`#template`、`#event`
2. `@speaker`
3. 选项块头：`@choice`（块语法）
4. 多行对话起始：`"""` 或 `<speaker> """`
5. 流程行：`label ...:`、`jump ...`、`choice ...`
6. 模板调用：`name(arg1, arg2)`
7. 命令：`@...`
8. 单行对话

## 块定义
### `#character <name>`
支持字段：
- `pos` / `position`：`x,y,order`
- `type`、`id`、`category`
- `textframe`
- `alias`
- `default_anim`（例如 `[wait1, face_wait, lip_wait]`）
- `voice`：`skip` / `none` / `off` / `mute`（该角色自动语音跳过）

### `#anim <preset>`
支持字段：
- `main` -> `charAnim1`
- `face` -> `charAnim2`
- `lip` -> `charLipAnim`
- `eye` -> `charAnim4`

### `#stage <name>`
定义命名站位：
```sc
#stage default
  left: 310,640,1
  center: 568,640,0
```

### `#positions`
定义角色默认站位：
```sc
#positions
  nichika: center
  mikoto: left
```

`@show <char>` 的站位解析顺序：
1. 命令中规定的站位
2. `#character` 的 `pos/position`
3. `#positions`

### `#template <name> {param1,param2}`
带占位符的命令模板：
```sc
#template enter_pair {left_char,right_char}
  @show {left_char} left
  @show {right_char} right
```

调用：
```sc
enter_pair(mikoto,nichika)
```

### `#event <event_id>`
定义自动语音的事件上下文。

## 流程控制
### 标签与跳转
支持两种写法：
```sc
label start:
jump scene_1
```

```sc
@label start
@jump scene_1
```

JSON 映射：
- label -> `{ "label": "..." }`
- jump -> `{ "nextLabel": "..." }`

### 选项
行内写法：
```sc
choice "A" -> 1 | "B" -> 2 | "C" -> 3
@choice "A" -> 1 | "B" -> 2 | "C" -> 3
```

块写法：
```sc
@choice
  "A" -> 1
  "B" -> 2
  "C" -> 3
```

每个选项输出：
- `{ "select": "...", "nextLabel": "..." }`
- 最后一项自动追加 `"textCtrl": "cm"`

## 命令
### 核心命令
- `@bg <name> [effect] [time]`
- `@fg <name> [effect] [time]`
- `@bgm <name>`
- `@se <name>`
- `@wait <ms>`
- `@voice <path_or_id_or_auto>`
- `@show <char> [position|(<x>,<y>,<order>)] [anims] [fade_ms]`
- `@hide <char> [anims] [fade_ms]`
- `@char <char> [anims]`
- `@cos <char> <type> <id> [category]`

说明：
- `@show` / `@hide` 默认淡入淡出时间为 `100ms`
- `@bg none` 与 `@fg none` 会被标准化为 `off`
- `@cos` 在可用时会复用角色运行时位置/缩放信息

## 语音系统
### 命令模式
```sc
@voice /produce_events/302502202/3025022020010
@voice 3025022020010
@voice id:3025022020010
```

### 自动模式
```sc
@voice auto
```
启用后，后续对话会自动分配 voice/id，直到被覆盖。

- id 格式：`<event_id><seq4>`
- 起始 `0010`，每次 +10
- JSON 会同时输出 `voice` 与数字 `id`

### 覆盖自动模式
```sc
@voice 3025022020100
```
该语音会作用于下一句对话，并关闭自动模式。

### 单句跳过语音
```sc
"line" @voice skip
"line" @voice none
"line" @voice off
```

### 角色级自动跳过
```sc
#character producer
  voice: skip
```

## 对话
### 单行对话
```sc
<speaker> "text" <frame?>
"text" <frame?>          // 需要先设置 @speaker
```

### 动画 + 对话
```sc
<speaker> [anim_or_preset] "text" <frame?>
[anim_or_preset] "text" <frame?>   // 需要 @speaker
```

### 群组对话
```sc
[A & B] "text" 001
```

### 旁白
```sc
:: "text" 001
```

### 多行对话（`"""` 标记）
```sc
<speaker> """
  line 1
  line 2
""" 001
```

```sc
"""
  line 1
  line 2
""" 001 @voice auto
```

规则：
- 第二种写法需要 `@speaker`
- 输出文本会用 `\r\n` 拼接
- 结束行可带 frame 和 inline voice

## speaker 与 charLabel
- `alias` 会把脚本中的 speaker 映射成输出 `speaker`
- 对话中的 `charLabel` 仅在以下情况下输出：
  - 该句有显式动画
  - 或该角色当前处于舞台激活状态

## 合并规则
编译器会合并连续的非中断对象，但以下情况不会合并：
- 等待/文本中断
- 流程对象（`label`、`nextLabel`、`select`）
- 角色特效切换（`charEffect`）