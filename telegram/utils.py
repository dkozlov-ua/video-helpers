from typing import Literal


def escape(text: str, entity_type: Literal['link', 'code', 'text'] = 'text') -> str:
    if entity_type == 'link':
        escaped_symbols = '\\)'
    elif entity_type == 'code':
        escaped_symbols = '\\`'
    elif entity_type == 'text':
        escaped_symbols = '\\_*[]()~`>#+-=|{}.!'
    else:
        raise ValueError(f"Unknown entity_type: {entity_type}")

    for symbol in escaped_symbols:
        text = text.replace(symbol, f"\\{symbol}")
    return text
