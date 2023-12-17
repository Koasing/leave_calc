from __future__ import annotations

import numpy as np
import pandas as pd
import gspread

from leave_class import update_holidays
from leave_class import Member
from draw_report import draw_report, draw_monthly


def get_data_from_gsheet(credential_file: str, sheet_key: str):
    client = gspread.service_account(filename=credential_file)
    sheet = client.open_by_key(sheet_key)

    def get_dataframe(ws: gspread.Worksheet, filter_column: str | list[str]):
        if isinstance(filter_column, str):
            filter_column = [filter_column]
        df = pd.DataFrame(ws.get_all_records())
        # replace all empty strings to nan
        df.replace('', np.nan, inplace=True)
        df.dropna(subset=filter_column, inplace=True)

        return df

    leaves = get_dataframe(sheet.get_worksheet(0), "휴가일정시작")
    compensations = get_dataframe(sheet.get_worksheet(1), "지급일수")
    holidays = get_dataframe(sheet.get_worksheet(2), "종류")

    return leaves, compensations, holidays


def get_data_from_excel(fn: str):
    leaves = pd.read_excel(fn, 0)
    compensations = pd.read_excel(fn, 1)
    holidays = pd.read_excel(fn, 2)

    return leaves, compensations, holidays


def main(fn: str, year=2023):
    leaves, compensations, holidays = get_data_from_excel(fn)

    h = update_holidays(holidays)
    print('HOLIDAYS:')
    for d in h:
        print(d)
    print()

    names = set(leaves['기안자']).union(set(compensations['대상자']))
    members = dict(((name, Member(name)) for name in names))

    for idx, row in compensations.iterrows():
        member = members[row['대상자']]
        member.add_compensations(row)

    for idx, row in leaves.iterrows():
        member = members[row['기안자']]
        member.add_leaves(row, h)

    for member in members.values():
        draw_report(member, h, year, './output')

    for month in range(1, 13):
        draw_monthly(members.values(), h, year, month, './output')


if __name__ == "__main__":
    main('leaves.xlsx')
