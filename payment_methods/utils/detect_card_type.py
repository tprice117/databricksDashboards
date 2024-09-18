import re


def detect_card_type(number: str) -> str:
    patterns = {
        "electron": r"^(4026|417500|4405|4508|4844|4913|4917)\d+$",
        "maestro": r"^(5018|5020|5038|5612|5893|6304|6759|6761|6762|6763|0604|6390)\d+$",
        "dankort": r"^(5019)\d+$",
        "interpayment": r"^(636)\d+$",
        "unionpay": r"^(62|88)\d+$",
        "visa": r"^4[0-9]{12}(?:[0-9]{3})?$",
        "mastercard": r"^5[1-5][0-9]{14}$",
        "amex": r"^3[47][0-9]{13}$",
        "diners": r"^3(?:0[0-5]|[68][0-9])[0-9]{11}$",
        "discover": r"^6(?:011|5[0-9]{2})[0-9]{12}$",
        "jcb": r"^(?:2131|1800|35\d{3})\d{11}$",
    }

    for card_type, pattern in patterns.items():
        if re.match(pattern, number):
            return card_type
    return None
