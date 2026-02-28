# SCWriting
SCWriting is a script language for generating JSON used by [ShinyColorsDB-EventViewer](https://github.com/ShinyColorsDB/ShinyColorsDB-EventViewer).

It supports:
- Compact SC grammar focused on reusable blocks and shorthand commands.
- Character/stage/animation presets, speaker context, templates, and auto voice/id generation.

## Run
```bash
python script.py your_script.sc
```

Output file:
- `your_script.json`

If syntax is invalid, the compiler reports `Line <n>, <error>`.

## Grammar Overview
Each statement is one of:
- comment
- block header
- function call
- flow control
- dialogue
- blank line

Comments:
```sc
// this is a comment
```

### Parsing Order (important)
`script.py` handles lines in this order:
1. block headers (`#character`, `#anim`, `#stage`, `#positions`, `#template`, `#event`)
2. `@speaker`
3. multi-line dialogue start (`"""` or `<speaker> """`)
4. flow lines (`label ...:` / `jump ...`)
5. template invocation (`template_name(arg1, arg2, ...)`)
6. enhanced `@` functions (`@show` shorthand, preset-aware `@char`, shorthand `@hide`, voice shorthand)
7. dialogue patterns

This means new syntax can be mixed with old syntax in the same file.

## Block Syntax
Blocks define reusable config and must use indented `key: value` lines.

### `#character`
Defines defaults for a character label.

```sc
#character nichika
  pos: 568,640,0
  type: characters
  id: 024
  category: stand_fix
  textframe: 001
  alias: にちか
  default_anim: [wait1, face_wait, lip_wait]
```

Supported keys:
- `pos` or `position`: `x,y,order`
- `type`, `id`, `category`: used by shorthand `@show`
- `textframe`: default text frame for this speaker
- `alias`: output speaker name mapping
- `default_anim`: used by shorthand `@show` when no animation list is passed
- `voice`: set to `skip` / `none` / `off` / `mute` to disable auto-voice assignment for this character

### `#anim`
Defines animation presets.

```sc
#anim smile_idle
  main: wait2
  face: face_wait
  lip: lip_smile1
```

Supported preset keys:
- `main` -> `charAnim1`
- `face` -> `charAnim2`
- `lip` -> `charLipAnim`
- `eye` -> `charAnim4`

### `#stage`
Defines named stage positions.

```sc
#stage default
  left: 310,640,1
  center: 568,640,0
  right: 796,640,2
```

Position names can then be used in shorthand `@show`.

### `#positions`
Defines per-character default symbolic positions.

```sc
#positions
  nichika: right
  mikoto: left
```

Resolution order for shorthand `@show <char>`:
- explicit `@show <char> <position>`
- `#character <char> pos/position`
- `#positions <char>: <position>`

### `#template`
Defines reusable command sequences.

```sc
#template surprised {char}
  @char {char} [wait4, face_surp, lip_surp]
  @wait 500
  @char {char} [wait1, face_wait, lip_wait]
```

Usage:
```sc
surprised(nichika)
```

Notes:
- Placeholder format is `{param}`.
- Header params are optional. If omitted and one argument is passed, it maps to `{char}` by default.

### `#event`
Defines event id for voice auto-path generation.

```sc
#event 302502202
```

With this, `@voice 3025022020010` becomes:
- `produce_events/302502202/3025022020010`
- output JSON will also include `id: 3025022020010`

## Function Syntax
### Core commands
- `@bg <name> [effect] [time]`
- `@fg <name> [effect] [time]`
- `@bgm <name>`
- `@se <name>`
- `@wait <ms>`
- `@voice <path_or_id_or_auto>`
- `@show <char> [position|(<x>,<y>,<order>)] [anims]`
- `@hide <char> [anims]`
- `@char <char> [anims]`
- `@cos <char> <type> <id> [category]`
- `@label <name>` or `@label <name>:`
- `@jump <name>`
- `@choice "text" -> label | "text2" -> label2 | ...`

Examples:
```sc
@bg 00018 fade 1000
@show nichika center [wait1, face_wait, lip_wait]
@cos nichika characters 024 stand_fix
```

### Shorthand and preset forms
#### Scene flow (`label` / `jump`)
Ren'Py-like style is supported:
```sc
label start:
jump scene_1
```

SC command style is also supported:
```sc
@label start
@jump scene_1
```

Output mapping:
- `label ...` -> `{ "label": "<name>" }`
- `jump ...` -> `{ "nextLabel": "<name>" }`

Flow statements are emitted as standalone JSON items (not merged with neighboring commands), which makes them safe to use as scene boundaries and future choice targets.

#### Choice flow (`choice` / `@choice`)
Inline forms:
```sc
choice "Option A" -> branch_a | "Option B" -> branch_b | "Option C" -> branch_c
@choice "Option A" -> branch_a | "Option B" -> branch_b | "Option C" -> branch_c
```

Block form:
```sc
@choice
  "Option A" -> branch_a
  "Option B" -> branch_b
  "Option C" -> branch_c
```

Output mapping:
- each option emits `{ "select": "<text>", "nextLabel": "<target>" }`
- the last option additionally emits `textCtrl: "cm"` (matching EventViewer choice format)
- options are emitted as standalone items (not merged)

Tips:
- Use scene labels as choice targets (`label branch_a:` etc.).
- Choice text supports escaped line breaks like `\\r\\n`.

#### `@show` shorthand
```sc
@show nichika
@show nichika center
@show nichika center [smile_idle]
```

Behavior:
- position comes from explicit stage label, then character `pos/position`.
- automatically adds fade-in charEffect.
- if character config has `type/id/category`, they are emitted too.

#### `@char` preset-aware
```sc
@char nichika [smile_idle]
@char nichika [wait2, face_wait, lip_smile1]
```

#### `@hide` shorthand
```sc
@hide nichika
@hide nichika [wait, face_wait, lip_wait]
```

Behavior:
- automatically adds fade-out charEffect.

#### `@speaker`
```sc
@speaker にちか
```

Sets default speaker for subsequent speaker-less dialogue lines.

#### `@voice` shorthand
```sc
@voice /produce_events/302502202/3025022020010
@voice 3025022020010
@voice auto
@voice id:auto
```

If `#event` exists and argument is numeric id, path is auto-generated.

`auto` behavior:
- `@voice auto` and `@voice id:auto` enable persistent auto-voice mode.
- while auto mode is active, each dialogue line without inline `@voice` gets an auto-generated voice id.
- generated ids use `<event_id><seq4>` where `seq4` starts at `0010` and increments by `10`.
- generated voice path is `produce_events/<event_id>/<voice_id>`.
- `id` is automatically emitted in output JSON when voice path matches `produce_events/<event>/<voice_id>`.
- writing a new explicit voice command (for example `@voice 3025022020100` or full path) disables auto mode and applies that voice to the next dialogue line.
- use inline `@voice skip` (or `@voice none` / `@voice off`) on a dialogue line to emit no voice for that line while keeping auto mode enabled for later lines.
- if a character has `voice: skip` in `#character`, auto mode skips voice/id generation for that character's dialogue lines by default.

## Dialogue Syntax
### Standard dialogue
```sc
<speaker> "text" <frame?>
```

Examples:
```sc
にちか "おはよう" 001
プロデューサー "ありがとう" 002
```

Frame rules:
- default is `001`.
- last used frame is cached per speaker.
- `#character ... textframe:` can define initial default.

### Default-speaker dialogue
After `@speaker`, these are valid:

```sc
"line 1" 001
"line 2"
```

### Combined animation + dialogue
```sc
<speaker> [anim_or_preset] "text" <frame?>
[anim_or_preset] "text" <frame?>    // requires @speaker
```

Examples:
```sc
にちか [smile_idle] "おはよう"
[wait1, face_wait, lip_wait] "はい"
```

### Group dialogue
```sc
[A & B] "text" <frame?>
```

Example:
```sc
[にちか & 美琴] "お疲れ様でした" 001
```

### Narration
```sc
:: "text" <frame?>
```

Example:
```sc
:: "新しい朝が始まった"
```

### Multi-line dialogue
Two forms:

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
""" 001
```

Rules:
- second form requires current speaker via `@speaker`.
- output text joins lines with `\r\n`.
- closing line can include frame and inline voice: `""" 001 @voice 3025...`.

### Inline voice on dialogue
You can attach voice to most dialogue lines:

```sc
にちか "text" 001 @voice 3025022020010
"text" @voice /produce_events/302502202/3025022020010
```

## Animation Resolution Rules
Animation token classification:
- starts with `face_` -> `charAnim2`
- starts with `lip_` -> `charLipAnim`
- starts with `eye_` -> `charAnim4`
- otherwise -> `charAnim1`

If a preset and raw tokens are mixed, later values overwrite earlier ones in the same expression.

## Compatibility Notes
- This compiler targets the new grammar in this document.
- Keep scripts aligned to these rules to avoid unsupported-command errors.

## Minimal Enhanced Example
```sc
#character nichika
  pos: center
  type: characters
  id: 024
  category: stand_fix

#anim idle
  main: wait1
  face: face_wait
  lip: lip_wait

#stage default
  center: 568,640,0

#event 302502202

@bg 00018
@show nichika [idle]
@speaker にちか
[idle] "おはようございます" 001 @voice 3025022020010
"""
  早速なんだけど
  まずは資料を渡すよ
""" 001
```

## Known Limits
- Dedicated sequence syntax names like `#sequence` are not implemented (`#template` is supported).

## Reference
- [Building a Toy Programming Language in Python](https://blog.miguelgrinberg.com/post/building-a-toy-programming-language-in-python)
