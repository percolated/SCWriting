from lib import func_gen

func_list = func_gen.func_list

# Module-level character frame cache for tracking speaker text frames
_char_frame = {}

def reset_char_frames():
    """Reset the character frame cache. Useful for testing or processing multiple files."""
    global _char_frame
    _char_frame = {}

def parse(tokens: list):
    """Parse a statement (function call or dialogue line)."""
    token_type, token_value = tokens.pop(0)
    statement = {}
    message = None

    if token_type == 'AT':
        statement, message = parse_func(tokens)
    elif token_type == 'PATH' and len(tokens) > 0 and tokens[0][0] == 'STRING':
        statement['speaker'] = token_value
        statement['text'] = tokens[0][1].replace('\\r', '\r').replace('\\n', '\n')
        statement['textCtrl'] = 'p'
        statement['textFrame'] = '001'

        # Check frame presets
        tokens.pop(0)
        if len(tokens) == 0:
            # Use previously stored frame for this speaker if available
            if statement['speaker'] in _char_frame:
                statement['textFrame'] = _char_frame[statement['speaker']]
        elif tokens[0][0] == 'NUMBER':
            statement['textFrame'] = str(tokens[0][1])
            _char_frame[statement['speaker']] = statement['textFrame']
        else:
            message = "invalid statement"
    else:
        message = "invalid statement"
    
    return statement, message

def parse_func(tokens):
    token_type, token_value = tokens.pop(0)
    if token_type != 'IDENT':
        return None, f"expected IDENT, got {token_type}"
    
    func_name = token_value
    count = 0
    statement = {}
    message = None

    while token_type:
        if not tokens:
            break
            
        token_type, token_value = tokens.pop(0)
        expect = func_list[func_name]['rule']

        # Handle both list (alternatives) and string (single option) rules
        if isinstance(expect[count], list):
            if token_type in expect[count]:
                statement[func_list[func_name]['label'][count]] = token_value
            else:
                exp_mess = ' or '.join(expect[count])
                message = f"expected {exp_mess}, got {token_type}"
                token_type = None
        else:
            if token_type == expect[count]:
                statement[func_list[func_name]['label'][count]] = token_value
            else:
                message = f"expected {expect[count]}, got {token_type}"
                token_type = None

        count += 1
        # stop if read all expected
        if count >= len(expect) or len(tokens) == 0:
            token_type = None

    
    if 'ph' in statement:
        if statement['ph'] not in [')', ']']:
            message = 'require end of arguments'
        statement.pop('ph')

    # clean pos and anim
    if 'charX' in statement:
        clean_pos(statement)
    if 'anim1' in statement:
        clean_anim(statement)

    # change type of some values to int
    if 'bgEffectTime' in statement:
        statement['bgEffectTime'] = int(statement['bgEffectTime'])
    if 'fgEffectTime' in statement:
        statement['fgEffectTime'] = int(statement['fgEffectTime'])

    # special functions
    if func_name == 'show':
        statement['charEffect'] = {"type": "from", "alpha": 0, "time": 100}
    elif func_name == 'hide':
        statement['charEffect'] = {"type": "to", "alpha": 0, "time": 100}
    elif func_name == 'wait':
        statement['waitType'] = 'time'
        statement['waitTime'] = int(statement['waitTime'])
    elif func_name == 'voice':
        # Normalize voice path - remove leading/trailing slashes
        voice_path = statement['voice']
        if voice_path.startswith('/'):
            voice_path = voice_path.lstrip('/')
        statement['voice'] = voice_path

    return statement, message

def clean_pos(statement):
    statement['charPosition']={}
    statement['charPosition']['x']=int(statement.pop('charX'))
    statement['charPosition']['y']=int(statement.pop('charY'))
    statement['charPosition']['order']=int(statement.pop('charZ'))

def clean_anim(statement):
    for item in ['anim1','anim2','anim3','anim4']:
        if item in statement:
            atype = get_anim_type(statement[item])
            statement[atype] = statement.pop(item)

def get_anim_type(anim: str):
    if anim.startswith('face_'):
        return 'charAnim2'
    elif anim.startswith('lip_'):
        return 'charLipAnim'
    elif anim.startswith('eye_'):
        return 'charAnim4'
    else:
        return 'charAnim1'

if __name__ == '__main__':
    from tokenizer import tokenize
    text = '@bg 0250 fade 1000'
    text2 = 'alice "I\'m loving it." 001'
    text3 = '@show nichika (568,640,0) [wait4, face_close2, lip_surp]'
    text4 = '@hide mamimi [wait, eye_left]'
    tokens = tokenize(text3)
    parse(tokens)