import pathlib
import sys
import csv
import dataclasses
from email import utils
from typing import Dict, Optional, List
from datetime import date, datetime, timedelta
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
import matplotlib.pyplot as plt


@dataclasses.dataclass
class Contagion:
    contagions: int
    tests: int
    report_date: date

    @property
    def percents(self) -> float:
        return 100 * self.contagions / self.tests


def datetime_format(value, format="%d-%m-%Y"):
    return value.strftime(format)


def datetime_rfc_2822_format(value):
    my_time = datetime.min.time()
    return utils.format_datetime(datetime.combine(value, my_time))


def format_currency(value):
    return "{:,.2f}".format(value).replace('.00', '').replace(',', '.')


def format_percent(value):
    return "{:,.2f}".format(value)


def is_same_day():
    return datetime.now().hour < 18


csv_dt_pattern = "%Y-%m-%dT17:00:00"


def _diff_data(ref_date: date = date.today()) -> Optional[Contagion]:
    delta = timedelta(days=1)
    before_date = ref_date - delta
    csv_url = "https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-andamento-nazionale/dpc-covid19-ita-andamento-nazionale.csv"

    resp = requests.get(csv_url)
    if resp.ok:
        decoded_content = resp.content.decode('utf-8')
        data = csv.reader(decoded_content.splitlines(),
                          delimiter=',')  # TODO cache

        rows = list(filter(lambda r:
                           r[0] == ref_date.strftime(csv_dt_pattern) or r[0] == before_date.strftime(csv_dt_pattern), data))

        #print(f"rows {list(rows)}")
        if len(rows) == 2:
            return Contagion(report_date=ref_date, contagions=int(rows[1][8]), tests=int(rows[1][14]) - int(rows[0][14]))
        else:
            print(rows)
            return None

    else:
        return None


def main(template_names: List[str] = ['index.html', 'rss.xml'], output_dir: str = 'build', render_image: bool = True) -> int:

    date_data = date.today()
    if is_same_day():
        date_data = date.today() - timedelta(days=1)
    latest_data = _diff_data(date_data)
    if latest_data:
        previous_data = [_diff_data(
            date.today() - timedelta(days=x)) for x in range(1, 7)]
        trend = previous_data.copy()
        trend.reverse()
        if not is_same_day():
            trend.append(latest_data)
        template_path = pathlib.Path().absolute()

        env = Environment(
            loader=FileSystemLoader(template_path),
            autoescape=select_autoescape(['html', 'xml'])
        )
        env.filters['datetimeformat'] = datetime_format
        env.filters['currencyformat'] = format_currency
        env.filters['percentformat'] = format_percent
        env.filters['rfcformat'] = datetime_rfc_2822_format
        for template_name in template_names:
            template = env.get_template(template_name)
            output_from_parsed_template = template.render(
                latest_data=latest_data, previous_data=previous_data, trend=trend)
            with open(output_dir + "/" + template_name, "w") as fh:
                fh.write(output_from_parsed_template)
        if render_image:
            with plt.xkcd():
                fig, ax = plt.subplots()
                labels = list(map(lambda d: datetime_format(
                    d.report_date, format="%d-%m"), previous_data))
                chart_data = list(map(lambda d: d.percents, previous_data))
                labels.reverse()
                chart_data.reverse()
                fig.text(
                    0.15, 0.8, f'{latest_data.report_date} : {format_percent(latest_data.percents)} %', fontsize=24)

                ax.plot(labels, chart_data)
                plt.savefig(f'{output_dir}/chart.png')

        return 0
    else:
        return -1


if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)
