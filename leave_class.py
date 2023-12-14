from dataclasses import dataclass

from datetime import date, timedelta
import re

import pandas as pd


THIS_YEAR = date.today().year

DAYOFF_TABLE = {
    '연차': (1.0, '◎'),
    '오전반차': (0.5, '△'),
    '오후반차': (0.5, '▽'),
    '반반차09-11': (0.25, '↑↑'),
    '반반차11-13': (0.25, '↑↓'),
    '반반차14-16': (0.25, '↓↑'),
    '반반차16-18': (0.25, '↓↓'),
    '공가': (0.0, '●'),
    '병가': (0.0, '●'),
    '기타': (0.0, '※'),
}

COUNT_TABLE = dict(((k, v[0]) for k, v in DAYOFF_TABLE.items()))
SYMBOL_TABLE = dict(((k, v[1]) for k, v in DAYOFF_TABLE.items()))


def daterange(start_date, end_date):
    # end date inclusive
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def date_match(date_: str) -> date:
    if m := re.match(r'(\d{4})-?(\d{2})-?(\d{2})', date_):
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))

    elif m := re.match(r'(\d{2})-?(\d{2})', date_):
        year = int(THIS_YEAR)
        month = int(m.group(1))
        day = int(m.group(2))

    else:
        raise ValueError(f"Cannot parse date string ({date_})")

    return date(year, month, day)


@dataclass
class Leave:
    date_: date
    type_: str
    reason: str
    count: float

    def __repr__(self):
        return f'{self.date_} / {self.count} -> {self.type_} ({self.reason})'

    def __lt__(self, other):
        return self.date_ < other.date_

    def __le__(self, other):
        return self.date_ <= other.date_


@dataclass
class Compensation:
    reason: str
    count: float


class Member:
    name: str

    leaves: list[Leave]
    compensations: list[Compensation]

    consolidated_leaves: list[Leave]

    def __init__(self, name: str):
        self.name = name

        self.leaves = []
        self.compensations = []
        self.consolidated_leaves = []

    @property
    def dayoff_count(self):
        return sum((c.count for c in self.compensations))

    @property
    def dayoff_base_count(self):
        if len(self.compensations) == 0:
            return 0
        return self.compensations[0].count

    @property
    def dayoff_additional_count(self):
        return self.dayoff_count - self.dayoff_base_count

    @property
    def dayoff_used_count(self):
        return sum((l.count for l in self.leaves))

    @property
    def dayoff_left_count(self):
        return self.dayoff_count - self.dayoff_used_count

    def monthly_used_dayoffs(self, year=THIS_YEAR):
        table = [0.0] * 13

        for l in self.leaves:
            if l.date_.year != year:
                continue
            month = l.date_.month
            table[month] += l.count

        return table

    def __repr__(self):
        return f'<{self.name} : Total {self.dayoff_count} / Used {self.dayoff_used_count}>'

    def add_leaves(self, row: pd.Series, holidays: list[date]):
        if row['기안자'] != self.name:
            raise ValueError(f'Name mismatch! ({row["기안자"]} != {self.name})')

        date_begin = date_match(row['휴가일정시작'])
        if pd.isna(row['휴가일정종료']):
            date_end = date_begin
        else:
            date_end = date_match(row['휴가일정종료'])

        for d in daterange(date_begin, date_end):
            # 취소 처리
            if row['휴가종류'] == '취소':
                # 주말 처리. date.weekday() -> 0(월) ~ 5(토), 6(일)
                if row['휴가종류'] not in ['공가', '병가', '기타'] and d.weekday() in [5, 6]:
                    continue

                if row['휴가종류'] not in ['공가', '병가', '기타'] and d in holidays:
                    continue

                cancels = [l for l in self.leaves if l.date_ == d and l.type_ == row['사유']]

                if len(cancels) == 0:
                    raise ValueError(f'Cannot cancel non-existing leaves! ({d})')
                elif len(cancels) > 1:
                    raise ValueError(f'Duplicated leaves! ({d})')
                else:
                    cancels[0].type_ += '취소'
                    cancels[0].count = 0

            else:
                count = COUNT_TABLE[row['휴가종류']] if pd.isna(row['휴가일수']) else float(row['휴가일수'])

                reason = '' if pd.isna(row['사유']) else row['사유']

                # 주말 처리. date.weekday() -> 0(월) ~ 5(토), 6(일)
                if row['휴가종류'] not in ['공가', '병가', '기타'] and d.weekday() in [5, 6]:
                    continue

                if row['휴가종류'] not in ['공가', '병가', '기타'] and d in holidays:
                    continue

                l = Leave(d, row['휴가종류'], reason, count)
                self.leaves.append(l)

    def add_compensations(self, row: pd.Series):
        if row['대상자'] != self.name:
            raise ValueError(f'Name mismatch! ({row["대상자"]} != {self.name})')

        if pd.isna(row['지급일수']):
            raise ValueError('지급일수 cannot be empty!')
        count = float(row['지급일수'])

        if pd.isna(row['사유']):
            raise ValueError('Reason cannot be empty!')
        reason = row['사유']

        c = Compensation(reason, count)
        self.compensations.append(c)


def update_holidays(holidays: pd.DataFrame) -> list[date]:
    table = []

    for idx, row in holidays.iterrows():
        if pd.isna(row['연']) or pd.isna(row['월']) or pd.isna(row['일']):
            continue

        year = int(row['연'])
        month = int(row['월'])
        day = int(row['일'])

        table.append(date(year, month, day))

    return table


def main(fn: str):
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

    for name, member in members.items():
        print(member)
        for l in member.leaves:
            print(l)
        print()


if __name__ == "__main__":
    main('leaves_sample.xlsx')
