import inspect, re


def sanitize_string(input_str: str) -> str:
    # Define a mapping of symbols to their text representations
    symbol_mapping = {
        '.': 'DOT',
        ',': 'COMMA',
        ':': 'COLON',
        '/': 'SLASH',
        '\\': 'BACKSLASH',
        '|': 'PIPE',
        '?': 'QUESTIONMARK',
        '*': 'ASTERISK',
        '<': 'LESS',
        '>': 'GREATER',
        '"': 'QUOTE',
        '\x00-\x1F': 'CTRLCHAR'  # Control characters
    }

    # Create a regex pattern to match any of the symbols
    pattern = re.compile('|'.join(re.escape(key) for key in symbol_mapping.keys()))

    # Replace symbols with their text representations
    sanitized_str = pattern.sub(lambda x: symbol_mapping[x.group()], input_str)

    return sanitized_str



class SignatureProvidingInstance:

    def __str__(self):
        instance_str = type(self).__name__

        constructor_args = inspect.signature(self.__init__).parameters

        for constructor_arg in constructor_args:
            if constructor_arg in ["self", "args", "kwargs"]:
                continue
            instance_str += f"_{constructor_arg}_{getattr(self, constructor_arg)}"

        return sanitize_string(instance_str)

