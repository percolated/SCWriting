// Rewritten with the new SCWriting grammar

#event 202401201

#stage default
  left: 310,640,1
  center: 568,640,0
  right: 796,640,2

#positions
  nichika: center

#character nichika
  pos: center
  type: characters
  id: 024
  category: stand_fix
  textframe: 001
  alias: にちか
  default_anim: [idle]

#character producer
  textframe: 002
  alias: プロデューサー
  voice: skip

#anim idle
  main: wait1
  face: face_wait
  lip: lip_wait

#anim tired
  main: wait4
  face: face_close2
  lip: lip_surp

#anim upset
  main: anger2
  face: face_anger2
  lip: lip_surp

@bg 00075
@bgm 0002
@wait 2500

@bg 00224 fade
@bgm fade_out
@wait 2500

@bgm 0082
@voice auto
nichika """
  あー……もう————
  終わらない……
"""

@se 1218
@wait 3800
@wait 500

にちか "めんどくさいなー"
"""
  全然、必要ないし
  こういう前ならえな感じとか……ほんと————
"""

@bg 00001 fade 1000
@wait 1500

にちか [tired] "はーあ……————"

@speaker producer
"…………"

@speaker にちか
[upset] """
  数学も古文も歴史もやって意味あるんですかねー
  全部、必要ないのになー
""" 001

@speaker producer
"にちか、手が止まってるぞ"

@speaker にちか
"""
  そういうこと言われると
  もっとやる気なくなるのわからないですかねー
"""

@speaker producer
"でも、始めないと終わらないだろ"

@speaker にちか
[sad2, face_close2, lip_surp_s, eye_right] "…………"
[wait2, face_anger2, lip_surp] "はいはい、わかってますー"
[wait3, face_serious, lip_surp, blank] """
  あの、使ってないなら会議室でやってもいいです？
  ここだと集中できないので
"""

@speaker producer
"""
  ああ、今は空いてるから
  構わないぞ
"""

@hide nichika [wait, face_close2]
@bg 00224 fade 500
@se 0454
@wait 1000

@speaker にちか
"それじゃ、お借りしますねー"

@bg 00000 fade 1000
@bgm fade_out
@se 0242
@wait 1000

@bg 00623 fade 1000
@bgm 0000
@wait 1500
