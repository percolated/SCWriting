# SCWriting
[中文文档](README.zh-CN.md)

SCWriting is a lightweight script language that compiles to JSON for [ShinyColorsDB-EventViewer](https://github.com/ShinyColorsDB/ShinyColorsDB-EventViewer).

## Run
```bash
python script.py your_script.sc
```

Output:
- `your_script.json`

## Statements
A line can be one of:
- comment (`// ...`)
- block header (`#...` + indented key-value lines)
- flow control (`label ...:`, `jump ...`, `choice ...`)
- command (`@...`)
- dialogue

Blank lines are ignored.

## Parse Order
`script.py` parses in this order:
1. blocks: `#character`, `#anim`, `#stage`, `#positions`, `#template`, `#event`
2. `@speaker`
3. choice block header: `@choice` (block form)
4. multiline dialogue start: `"""` or `<speaker> """`
5. flow lines: `label ...:`, `jump ...`, `choice ...`
6. template invocation: `name(arg1, arg2)`
7. commands: `@...`
8. single-line dialogue

## Blocks
### `#character <name>`
Supported keys:
- `pos` / `position`: `x,y,order`
- `type`, `id`, `category`
- `textframe`
- `alias`
- `default_anim` (e.g. `[wait1, face_wait, lip_wait]`)
- `voice`: `skip` / `none` / `off` / `mute` (skip auto-voice for this character)

### `#anim <preset>`
Supported keys:
- `main` -> `charAnim1`
- `face` -> `charAnim2`
- `lip` -> `charLipAnim`
- `eye` -> `charAnim4`

### `#stage <name>`
Named positions:
```sc
#stage default
  left: 310,640,1
  center: 568,640,0
```

### `#positions`
Per-character symbolic defaults:
```sc
#positions
  nichika: center
  mikoto: left
```

`@show <char>` resolves position in this order:
1. explicit position in command
2. `#character` pos/position
3. `#positions`

### `#template <name> {param1,param2}`
Indented command body with placeholders:
```sc
#template enter_pair {left_char,right_char}
  @show {left_char} left
  @show {right_char} right
```

Invoke with:
```sc
enter_pair(mikoto,nichika)
```

### `#event <event_id>`
Defines auto-voice event context.

## Flow Control
### Labels and jumps
Both forms are supported:
```sc
label start:
jump scene_1
```

```sc
@label start
@jump scene_1
```

JSON mapping:
- label -> `{ "label": "..." }`
- jump -> `{ "nextLabel": "..." }`

### Choices
Inline:
```sc
choice "A" -> 1 | "B" -> 2 | "C" -> 3
@choice "A" -> 1 | "B" -> 2 | "C" -> 3
```

Block:
```sc
@choice
  "A" -> 1
  "B" -> 2
  "C" -> 3
```

JSON mapping per option:
- `{ "select": "...", "nextLabel": "..." }`
- last option also adds `"textCtrl": "cm"`

## Commands
### Core
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

Notes:
- `@show`/`@hide` default fade is `100ms`.
- `@bg none` and `@fg none` are normalized to `off`.
- `@cos` reuses runtime character position/scale when available.

## Voice System
### Explicit voice
```sc
@voice /produce_events/302502202/3025022020010
@voice 3025022020010
@voice id:3025022020010
```

### Auto mode (persistent)
```sc
@voice auto
```
After enabled, dialogue lines get auto-generated voice/id until changed.

- id format: `<event_id><seq4>`
- sequence starts at `0010`, step `10`
- JSON includes both `voice` and numeric `id`

### Break/override auto mode
```sc
@voice 3025022020100
```
This applies to the next dialogue line and disables auto mode.

### Skip voice on a line
```sc
"line" @voice skip
"line" @voice none
"line" @voice off
```

### Skip auto-voice for one character
```sc
#character producer
  voice: skip
```

## Dialogue
### Single line
```sc
<speaker> "text" <frame?>
"text" <frame?>          // requires @speaker
```

### Combined animation + dialogue
```sc
<speaker> [anim_or_preset] "text" <frame?>
[anim_or_preset] "text" <frame?>   // requires @speaker
```

### Group dialogue
```sc
[A & B] "text" 001
```

### Narration
```sc
:: "text" 001
```

### Multiline (`"""` markers)
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

Rules:
- second form requires `@speaker`
- output text joins lines with `\r\n`
- closing `"""` line may include frame and inline voice

## Speaker and charLabel behavior
- `alias` maps script speaker to output `speaker`
- `charLabel` is emitted on dialogue only when:
  - dialogue has explicit animation, or
  - character is currently active on stage

## Merge behavior
Compiler merges consecutive non-breaking objects, except around:
- waits / text breaks
- flow/choice objects (`label`, `nextLabel`, `select`)
- character effect transitions (`charEffect`)