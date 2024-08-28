func_list = {}
func_keys = ['bg','fg','bgm','se','wait','voice','show','hide','char','cos']
for key in func_keys:
    func_list[key]={}

func_list['bg']['rule'] = [['NUMBER','IDENT','PATH'], 'IDENT', 'NUMBER']
func_list['bg']['label'] = ['bg', 'bgEffect', 'bgEffectTime']

func_list['fg']['rule'] = [['NUMBER','IDENT','PATH'], 'IDENT', 'NUMBER']
func_list['fg']['label'] = ['fg', 'fgEffect', 'fgEffectTime']

func_list['bgm']['rule'] = [['NUMBER','IDENT','PATH']]
func_list['bgm']['label'] = ['bgm']

func_list['se']['rule'] = [['NUMBER','IDENT','PATH']]
func_list['se']['label'] = ['se']

func_list['wait']['rule'] = ['NUMBER']
func_list['wait']['label'] = ['waitTime']

func_list['voice']['rule'] = [['NUMBER','IDENT','PATH']]
func_list['voice']['label'] = ['voice']

func_list['show']['rule'] = ['IDENT','LPAREN','NUMBER','COMMA','NUMBER','COMMA','NUMBER','RPAREN','LBRACK','IDENT',
                             ['COMMA','RBRACK'],'IDENT',['COMMA','RBRACK'],'IDENT',['COMMA','RBRACK'],'IDENT','RBRACK']
func_list['show']['label'] = ['charLabel','ph','charX','ph','charY','ph','charZ','ph','ph','anim1',
                               'ph','anim2','ph','anim3','ph','anim4','ph']

func_list['hide']['rule'] = ['IDENT','LBRACK','IDENT',['COMMA','RBRACK'],'IDENT',['COMMA','RBRACK'],'IDENT',['COMMA','RBRACK'],'IDENT','RBRACK']
func_list['hide']['label'] = ['charLabel','ph','anim1','ph','anim2','ph','anim3','ph','anim4','ph']

func_list['char']['rule'] = ['IDENT','LBRACK','IDENT',['COMMA','RBRACK'],'IDENT',['COMMA','RBRACK'],'IDENT',['COMMA','RBRACK'],'IDENT','RBRACK']
func_list['char']['label'] = ['charLabel','ph','anim1','ph','anim2','ph','anim3','ph','anim4','ph']

func_list['cos']['rule'] = ['IDENT','IDENT','NUMBER','IDENT']
func_list['cos']['label'] = ['charLabel','charType','charId','charCategory']

if __name__=='__main__':
    import json
    with open('func_list.json','w') as f:
        json.dump(func_list, f, indent=2)
