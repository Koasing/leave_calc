import pandas as pd

from leave_class import update_holidays
from leave_class import Member, Leave
from draw_report import build_symbols, draw_report


def main(fn: str, year=2023):
    leaves = pd.read_excel(fn, 0)
    compensations = pd.read_excel(fn, 1)
    holidays = pd.read_excel(fn, 2)

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
        draw_report(member, h, year)


if __name__ == "__main__":
    main('leaves.xlsx')
