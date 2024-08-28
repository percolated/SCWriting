## Introduction
SCWriting is a simple script language based on Python to generate json files that can be used by [ShinyColorsDB-EventViewer](https://github.com/ShinyColorsDB/ShinyColorsDB-EventViewer).

## Syntax
Three types of statements (comments, functions and speeches) plus blank lines are supported by this language and each statement should take up one line without merging, otherwise an error of "invalid statement" will be printed in the terminal.

### Comments
Comments start with "//" and will not be interpreted.

### Functions
Functions start with "@" and are defined in `lib/func_gen.py`. Here is a list of built-in functions:

| Name | Argument (*Italic* means optional) | Description | Example
|:---:|---|---|---|
| bg | \<name> \<*effect*> \<*effectTime*>| background | `@bg 00000`<br>`@bg 00000 fade 1000`|
| fg | \<name> \<*effect*> \<*effectTime*>| foreground | `@fg 000000`<br>`@fg 000000 fade 1000`|
| bgm | \<name> | bgm | `@bgm 0000`|
| se | \<name> | se | `@se 0000`|
| wait | \<time> | wait time |`@wait 1000`|
| voice | \<path> | voice<br>(*path must start with "/"*) | `@voice /events/000/000`|
| show | \<char> (\<posX>, \<posY>, \<order>) [*\<main_anim>, \<face_anim>, \<lip_anim>, \<eye_anim>*] | make character appear<br>(*anims can be arranged in any order*) | `@show mano (568, 640, 0) [face_smile, wait]` |
| hide | \<char> [*\<main_anim>, \<face_anim>, \<lip_anim>, \<eye_anim>*] |make character disappear | `@hide kaho [wait]` |
| char | \<char> [*\<main_anim>, \<face_anim>, \<lip_anim>, \<eye_anim>*] | control character's animation | `@char hana [surp, eye_left]` |
| cos | \<char> \<type> \<id> \<*category*>| spine costume<br>(*should be loaded before first animation*) | `@cos nichika characters 024 stand_fix` |

For flexibility, statements like `@bgm 0000 whatever`, which gives arguments more than configured, are allowed. The extra arguments will not be interpreted.

### Speeches
The syntax for speeches is as follows:
```bash
<speaker> "<text>" <text_frame>
// example: 智代子 "こんにちは、せかい！" 001
```
The optional *\<textFrame>* argument is set to "001" by default, so you can directly write `智代子 "こんにちは、せかい！"` instead. Besides, the frame value will be stored for each speaker separately and you only need to write it down at the first time the speaker appears, for instance,
```
プロデューサー "はじめまして" 002
プロデューサー　"あらためて"
```
For more details, please refer to the sample script in this directory.

## Execution
To run, simply input in the terminal `python script.py your_script.sc` and you will get a json file named `your_script.json`. Any syntax error that occurs will be printed in the form of line number plus error message.

### Reference
- [Building a Toy Programming Language in Python](https://blog.miguelgrinberg.com/post/building-a-toy-programming-language-in-python)