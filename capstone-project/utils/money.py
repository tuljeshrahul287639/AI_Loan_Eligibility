"""Amounts are shown in Indian rupees, grouped the Indian way: ₹1,500 / ₹2,50,000 / ₹1,23,45,678."""


def rupees(value, decimals: int = 0) -> str:
    number = round(float(value or 0), decimals)
    sign = "-" if number < 0 else ""
    whole, _, fraction = f"{abs(number):.{decimals}f}".partition(".")

    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])

    return f"{sign}₹{whole}" + (f".{fraction}" if fraction else "")
