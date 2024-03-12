#!/usr/bin/env python3
"""
Copyright (c) 2024 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Trevor Maco <tmaco@cisco.com>"
__copyright__ = "Copyright (c) 2024 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

import csv
from collections import Counter
import os
import sys

import meraki
import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.table import Table

from dotenv import load_dotenv

# Absolute Paths
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load ENV Variable
load_dotenv()
MERAKI_API_KEY = os.getenv("MERAKI_API_KEY")
ORG_ID = os.getenv("ORG_ID")

# Meraki Dashboard Instance
dashboard = meraki.DashboardAPI(api_key=MERAKI_API_KEY, suppress_logging=True,
                                caller="Meraki API Usage Report CiscoGVEDevNet", maximum_retries=25)

# Rich console instance
console = Console()


def generate_summary_table(column_name: str, counter: Counter) -> Table:
    """
    Generate Summary Statistics tables: add a bit of insight to API call results
    :param column_name: Variable column name (2nd column "Count" is fixed)
    :param counter: Counter object tracking counts of various columns in output data
    :return: Table for display
    """
    table = Table(title=f"Summary Statistics for {column_name}")

    table.add_column(column_name, style="cyan")
    table.add_column("Count", style="magenta")

    for key, count in counter.items():
        table.add_row(str(key), str(count))

    return table


def main():
    """
    Main method, generate report of all Meraki API Calls in provided period
    """
    console.print(Panel.fit("Meraki API Usage Report"))

    # Prompt for Timespan (convert from days to seconds)
    valid_timestamps = [str(num) for num in range(1, 32)]
    timespan = IntPrompt.ask(f"Enter Timespan [b](in days)[/] to retrieve API Usage [blue][1-31][/]",
                             choices=valid_timestamps, default=1, show_choices=False)
    timespan *= (3600 * 24)

    # Get the current timestamp (for output file)
    current_time = datetime.datetime.now()
    timestamp_str = current_time.strftime("%Y-%m-%d_%H-%M-%S")

    # Get Admin ID's, build dict of admin id to name
    try:
        admins = dashboard.organizations.getOrganizationAdmins(
            ORG_ID
        )

        admin_id_to_name = {}
        for admin in admins:
            admin_id_to_name[admin['id']] = admin['name']

    except Exception as e:
        console.print(f"[red]Unable to get organization admins: {e}[/]")
        sys.exit(-1)

    # Get API Requests made during timestamp
    try:
        data = dashboard.organizations.getOrganizationApiRequests(
            ORG_ID, timespan=timespan, total_pages='all'
        )
    except Exception as e:
        console.print(f"[red]Unable to get organization api requests: {e}[/]")
        sys.exit(-1)

    # Output API Requests to CSV
    filename = f"meraki_api_requests_{timestamp_str}.csv"

    # Initialize counters
    request_types_counter = Counter()
    response_code_counter = Counter()
    operation_id_counter = Counter()

    # Write data to CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()

        for row in data:
            # Convert Admin ID to Name
            row['adminId'] = admin_id_to_name[row['adminId']]

            # Update Counters for summary stats
            request_types_counter[row['method']] += 1
            response_code_counter[row['responseCode']] += 1
            operation_id_counter[row['operationId']] += 1

            writer.writerow(row)

    console.print(f"[green]Successfully saved API requests to {filename}![/]")

    # Output Summary Tables
    type_table = generate_summary_table('Request Type', request_types_counter)
    code_table = generate_summary_table('Response Code', response_code_counter)
    api_table = generate_summary_table('API Call', operation_id_counter)

    console.print(type_table)
    console.print(code_table)
    console.print(api_table)


if __name__ == '__main__':
    main()
