import re

def tokenize(code):
    token_specification = [
        ('AT',        r'@'),                              # Function symbol
        ('HEADER',    r'#\w+'),                           # Block symbol
        ('SLASHES',   r'//'),                             # Comment symbol
        ('COLON',     r':'),                              # Colon
        ('DASH',      r'-'),                              # Dash (for user function arguments)
        ('IDENT',     r'[a-zA-Z_]\w*'),                   # Identifiers
        ('NUMBER',    r'\d+'),                            # Integer numbers
        ('COMMA',     r','),                              # Comma
        ('LPAREN',    r'\('),                             # Left Parenthesis
        ('RPAREN',    r'\)'),                             # Right Parenthesis
        ('LBRACK',    r'\['),                             # Left Bracket
        ('RBRACK',    r'\]'),                             # Right Bracket
        ('STRING',    r'"[^"]*"'),                        # String literals
        ('PATH',      r'[\w/]+(?:\.\w+)?'),               # File paths with optional extension
        ('WS',        r'\s+'),                            # Whitespace
    ]
    token_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_specification)
    tokens = []
    for mo in re.finditer(token_regex, code):
        kind = mo.lastgroup
        value = mo.group(kind)
        if kind == 'WS':
            continue  # skip whitespace
        elif kind == 'NUMBER':
            pass
        elif kind == 'STRING':
            value = value.strip('"')
        tokens.append((kind, value))
    return tokens

if __name__=="__main__":
    text  = """
    @voice /produce_events/202401201/2024012010020
    """
    tokens = tokenize(text)
    print(tokens)