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

from typing import Literal

import requests

from . import __version__


class EventBrite:
    def __init__(self, proxies: dict[str, str] = {}, verify: bool = True):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"cosmico-webinar/{__version__}",
            }
        )
        self.session.proxies = proxies
        self.session.verify = verify

        if not verify:
            __import__("urllib3").disable_warnings()

    def get_showmore(
        self,
        org_id: str,
        page: int = 1,
        pagesize: int = 12,
        type: Literal["past", "future"] = "past",
    ) -> tuple[list[dict], bool]:
        r = self.session.get(
            f"https://www.eventbrite.it/org/{org_id}/showmore/",
            params={
                "page_size": pagesize,
                "type": type,
                "page": page,
            },
        )
        r.raise_for_status()
        data = r.json()
        return (data["data"]["events"], data["data"]["has_next_page"])

    def get_structured_content(self, event_id: int) -> dict:
        r = self.session.get(
            f"https://www.eventbrite.it/api/v3/events/{event_id}/structured_content/",
            params={
                "purpose": "digital_content",
            },
        )
        r.raise_for_status()
        return r.json()

    def get_events(self, org_id: str, type: Literal["past", "future"], pagesize: int = 5):
        events = []

        # Get all events
        page = 1
        has_next_page = True
        while has_next_page:
            data, has_next_page = self.get_showmore(org_id, page, pagesize, type)
            events.extend(data)
            page += 1

        return events

    def get_past_events(self, org_id: str, pagesize: int = 12):
        return self.get_events(org_id, "past", pagesize)

    def get_future_events(self, org_id: str, pagesize: int = 12):
        return self.get_events(org_id, "future", pagesize)

    def get_all_events(self, org_id: str, pagesize: int = 12) -> list[dict]:
        events = []
        events.extend(self.get_future_events(org_id, pagesize))
        events.extend(self.get_past_events(org_id, pagesize))
        return events
