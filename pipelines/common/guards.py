import pandas as pd

PAN_RE = r'\b([2-6]\d{12,18})\b'

def luhn_ok(num: str) -> bool:
    d = [int(x) for x in num][::-1]

    return (sum(d[0::2]) + sum(sum(divmod(2*x, 10)) for x in d[1::2])) % 10 == 0

def assert_no_card_numbers(df: pd.DataFrame, file_name: str, skip_columns: tuple[str, ...] = ()) -> None:

    bad_columns = []

    for col in df.columns:
        if col in skip_columns:
            continue

        numbers = df[col].str.extractall(PAN_RE)[0]

        if any([luhn_ok(number) for number in numbers]):
            bad_columns.append(col)

    if bad_columns:
        raise ValueError(f'{file_name} possible full card number in column(s) {bad_columns}. Nothing was written.')