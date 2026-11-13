import re

COLUMN_MAP = {
    'Felhasználónév': 'user_name',
    'Számlaszám': 'account_number',
    'Könyvelés dátuma': 'booking_date',
    'Összeg': 'amount',
    'Devizanem': 'currency',
    'Partner név': 'partner_name',
    'Partner IBAN száma': 'partner_iban',
    'Partner számlaszáma': 'partner_account',
    'Partner bankkódja': 'partner_bank_code',
    'Könyvelési információk': 'booking_info',
    'Tranzakcióazonosító': 'transaction_id',
    'Tranzakció dátuma és ideje': 'transaction_ts',
}

DROP_COLUMNS = [
    'user_name',
    'partner_bank_code',
    'partner_account',
    'booking_info',
]

KEY_COLS = [
    'account_number',
    'booking_date',
    'amount',
    'currency',
    'partner_name',
    'transaction_ts',
]

AMOUNT_RE = re.compile(r'^-?\d+(\.\d+)?$')

# Tail of booking_info on card payments in another currency, e.g.  "... vásár. 0.50 EUR 378.57"
# = original amount, original currency, rate (account currency per 1 unit of original currency)
FX_RE = (r"(?P<fx_orig_amount>\d+(?:\.\d+)?)\s+(?P<fx_orig_currency>[A-Z]{3})"
         r"\s+(?P<fx_rate>\d+(?:\.\d+)?)\s*$")

CARD_RE = r'^(?P<card_first6>\d{6})x+(?P<card_last4>\d{4})\b'

# Dates in export file names: YYYY-MM-DD.
FILE_DATE_RE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')

CARD_STATEMENT_NAME_RE =re.compile(r'^\d{6}_+\d{4}_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.csv$')

PAN_SKIP_COLUMNS = ('Tranzakcióazonosító',)