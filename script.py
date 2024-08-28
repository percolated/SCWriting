from lib import parser, tokenizer

class Sc:
    def __init__(self, code):
        self.code = code
        self.line_nr = 0
        self.token_feed = self.tokens()
        self.log = None
    
    def raise_error(self, message):
        raise SyntaxError(f'Line {self.line_nr}, {message}')
    
    def tokens(self):
        for line in self.code.strip().split('\n'):
            self.line_nr += 1
            yield tokenizer.tokenize(line)
    
    def next_token(self):
        try:
            tokens = next(self.token_feed)
        except StopIteration:
            tokens = None
        return tokens

    def parse_program(self):
        tokens = self.next_token()
        program = []

        while tokens is not None:
            if len(tokens) == 0 or tokens[0][0] == 'SLASHES':
                pass
            else:
                statement, message = parser.parse(tokens)
                if message is None:
                    program.append(statement)
                else:
                    self.log = message
                    self.raise_error(message)

            tokens = self.next_token()
        return program
    
    def interpret(self):
        old_arr = self.parse_program()
        clean_arr = []

        # merge items
        for i in range(len(old_arr)):
            current = old_arr[i]
            if i == len(old_arr)-1:
                clean_arr.append(current)
            else:
                next = old_arr[i+1]
                if 'waitTime' in current or 'textFrame' in current:
                    clean_arr.append(current)
                else:
                    old_arr[i+1] = {**current, **next}
        
        # final check
        for i in range(len(clean_arr)):
            if 'textFrame' not in clean_arr[i]:
                clean_arr[i]['textFrame'] = 'off'
        
        clean_arr.append({'label': 'end', 'textFrame': 'off'})
        return clean_arr

if __name__=="__main__":
    import json, sys
    with open(sys.argv[1], 'rt', encoding='utf-8') as file:
        program = Sc(file.read())
        filename = sys.argv[1].split('.')[0]
        with open(filename+'.json', 'w', encoding='utf-8') as output:
            json.dump(program.interpret(), output, indent=2, ensure_ascii=False, sort_keys=True)
        