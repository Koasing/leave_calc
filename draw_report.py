import os, os.path
from collections.abc import Iterable

from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from leave_class import THIS_YEAR, Member, MonthlyReport, SYMBOL_TABLE


jinja2_env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape()
)


def build_symbols(member: Member, year=THIS_YEAR) -> list[list[str]]:
    table = [[]]
    for month in range(1, 13):
        table.append([''])
        current_month = table[-1]
        for days in range(1, 32):
            current_month.append('')

    for l in member.leaves:
        if l.date_.year != year:
            continue

        month = l.date_.month
        day = l.date_.day

        if l.type_ in SYMBOL_TABLE:
            symbol = SYMBOL_TABLE[l.type_]
        elif l.type_.endswith('취소'):
            symbol = ''
        else:
            symbol = '?'

        table[month][day] += symbol

    return table


def build_weekends(holidays: list[date], year=THIS_YEAR) -> list[list[str]]:
    table = [[]]
    for month in range(1, 13):
        table.append([''])
        current_month = table[-1]
        for day in range(1, 32):
            try:
                d = date(year, month, day)
                if d in holidays:
                    current_month.append('holiday')
                elif d.weekday() == 5:
                    current_month.append('saturday')
                elif d.weekday() == 6:
                    current_month.append('sunday')
                else:
                    current_month.append('')
            except ValueError:
                current_month.append('blank')

    return table


def draw_report(member: Member, holidays: list[date], year=THIS_YEAR, output_dir="."):
    symbols = build_symbols(member, year)
    weekends = build_weekends(holidays, year)

    template = jinja2_env.get_template('report.html')
    report = template.render(year=year, member=member, symbols=symbols, weekends=weekends)

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'{member.name}(잔여 {member.dayoff_left_count}).html')

    with open(output_file, mode='w', encoding='utf-8') as fd:
        fd.write(report)


def draw_monthly(members: Iterable[Member], holidays: list[date], year=THIS_YEAR, month=1, output_dir="."):
    monthly = MonthlyReport(year, month)
    monthly.apply_holidays(holidays)

    for member in members:
        monthly.append_member(member)

    template = jinja2_env.get_template('monthly.html')
    report = template.render(year=year, month=month, report=monthly, weeks=len(monthly.days))

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'{year}년 {month}월.html')

    with open(output_file, mode='w', encoding='utf-8') as fd:
        fd.write(report)

