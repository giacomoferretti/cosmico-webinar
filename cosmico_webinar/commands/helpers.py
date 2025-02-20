# Copyright 2025 Giacomo Ferretti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
from typing import TextIO

import click
import requests

from ..eventbrite import EventBrite

logger = logging.getLogger(__name__)


@click.group(name="helpers", help="Helper commands")
def cli():
    pass


@cli.command()
@click.argument("org-id")
@click.option("--pagesize", default=20, help="Number of events to fetch per page")
@click.pass_context
def get_events(ctx: click.Context, org_id: str, pagesize: int):
    eventbrite: EventBrite = ctx.obj["client"]
    events = eventbrite.get_all_events(org_id, pagesize)

    print(json.dumps(events, indent=2))


@cli.command()
@click.argument("events-file", type=click.File("r"))
@click.pass_context
def get_streamyard_links(ctx: click.Context, events_file: TextIO):
    eventbrite: EventBrite = ctx.obj["client"]
    data = json.load(events_file)

    # TODO: multithreading to speed up the process
    urls = []
    for event in data:
        logger.info(f"Fetching event {event['id']} - {event['name']['text']}")

        try:
            event_data = eventbrite.get_structured_content(event["id"])
            for x in event_data["modules"]:
                if x["type"] == "webinar":
                    urls.append(x["data"]["webinar_url"]["url"])
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error while fetching event {event['id']}: {e}")
        except KeyError:
            logger.error(f"Error while fetching event {event['id']}: No webinar URL")

    print(json.dumps(urls, indent=2))
