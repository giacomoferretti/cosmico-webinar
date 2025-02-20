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

import requests


class StreamYard:
    def __init__(self, proxies: dict[str, str] = {}, verify: bool = True):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # noqa: E501
                "Referer": "https://streamyard.com/",
            }
        )
        self.session.proxies = proxies
        self.session.verify = verify

        if not verify:
            __import__("urllib3").disable_warnings()

    def get_webinar_info(self, url: str) -> dict:
        webinar_id = url.split("/")[-1]

        # Update token
        if "jwtOnAir" not in self.session.cookies:
            r = self.session.get(url)
            r.raise_for_status()

        r = self.session.get(f"https://oa-api.streamyard.com/api/public/webinars/{webinar_id}")
        r.raise_for_status()
        return r.json()

    def register_webinar(self, url: str, webinar_data: dict, email: str, first_name: str, last_name: str):
        webinar_id = url.split("/")[-1]

        fields_id = webinar_data["registrationFieldDefinitions"][0]["id"]
        fields_data = webinar_data["registrationFieldDefinitions"][0]["fields"]["data"]
        fields_values = {}
        for field in fields_data:
            if field["isRequired"]:
                # Email
                if field["type"] == "email":
                    fields_values[field["id"]] = email
                # First name
                elif field["type"] == "firstName":
                    fields_values[field["id"]] = first_name
                # Last name
                elif field["type"] == "lastName":
                    fields_values[field["id"]] = last_name

        registration_url = f"https://oa-api.streamyard.com/api/public/webinars/{webinar_id}/registrations"
        registration_data = {
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "fields": {
                "definitionId": fields_id,
                "values": fields_values,
            },
            "timeZone": "Europe/Rome",
        }
        r = self.session.post(registration_url, json=registration_data, headers={"X-Csrf-Protection": "true"})
        r.raise_for_status()
        return r.json()
