import re

def tokenize(code):
    """
    Tokenize a single line of SCWriting code.
    Returns a list of (token_type, token_value) tuples.
    """
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
        
        # Process token value
        if kind == 'WS':
            continue  # Skip whitespace
        elif kind == 'STRING':
            # Remove quotes from string values
            value = value.strip('"')
        
        tokens.append((kind, value))
    
    return tokens


if __name__ == "__main__":
    # Test tokenizer
    test_cases = [
        '@voice /produce_events/202401201/2024012010020',
        'にちか "こんにちは、世界！" 001',
        '@show nichika (568,640,0) [wait4, face_close2, lip_surp]',
    ]
    
    for test in test_cases:
        tokens = tokenize(test)
        print(f"{test}\n  -> {tokens}\n")
