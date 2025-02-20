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

import logging
import pathlib
from queue import Queue
from threading import Event, Thread
from typing import TypedDict

import click
import requests
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from slugify import slugify

from ..constants import ORG_ID
from ..eventbrite import EventBrite
from ..streamyard import StreamYard

logger = logging.getLogger(__name__)


def crop_string(s: str, N: int, ellipsis="…", end=False):
    # Check if the string needs to be cropped
    if len(s) > N - len(ellipsis):
        if end:
            return s[(-(N - len(ellipsis))) :] + ellipsis
        else:
            return ellipsis + s[(-(N - len(ellipsis))) :]
    else:
        return s


VideoEntry = TypedDict("VideoEntry", {"title": str, "url": str, "poster": str})


_sentinel = object()
_stop_event = Event()


class DownloaderWorker(Thread):
    def __init__(
        self,
        queue: Queue[VideoEntry],
        output: pathlib.Path,
        progress: Progress,
        overall_progress: tuple[Progress, TaskID],
    ):
        super().__init__()
        self.queue = queue
        self.output = output
        self.progress = progress
        self.overall_progress = overall_progress[0]
        self.overall_task = overall_progress[1]

        self.is_running = True

    def download_file(self, url: str, filename: str, local_file: pathlib.Path):
        # Create task
        self.task_id = self.progress.add_task(
            "",
            start=False,
            filename=filename,
        )

        # Download the file
        with requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # noqa: E501
            },
            stream=True,
        ) as r:
            remote_file_size = int(r.headers.get("Content-Length", 0))

            # Check if the file already exists and has the same size
            if local_file.exists() and local_file.stat().st_size == remote_file_size:
                self.progress.console.print(f"File {local_file} already downloaded.")
                return

            # Update task total
            self.progress.update(self.task_id, total=remote_file_size)

            r.raise_for_status()
            with open(local_file, "wb") as f:
                self.progress.start_task(self.task_id)
                for chunk in r.iter_content(chunk_size=8192):
                    if _stop_event.is_set():  # Exit early if stop event is set
                        return

                    self.progress.update(self.task_id, advance=len(chunk))
                    f.write(chunk)

    def run(self):
        while self.is_running:
            self.task_id = None

            if _stop_event.is_set():
                self.is_running = False
                return

            try:
                # Get entry from the queue
                entry = self.queue.get()

                # Check if we're done
                if entry is _sentinel:
                    self.is_running = False
                    return

                output_filename = slugify(entry["title"])
                output_video = self.output / f"{output_filename}.mp4"
                # output_poster = self.output / f"{output_filename}.jpg"

                vod_url = entry["url"]
                # poster_url = entry["poster"]

                # Download the video
                self.download_file(vod_url, crop_string(str(output_video), 20), output_video)

                # Download the poster
                # self.download_file(poster_url, output_filename, output_poster)

            except Exception as e:
                self.progress.console.print(f"Error: {e}")
                self.is_running = False
            finally:
                # Stop the download progress task
                if hasattr(self, "task_id") and self.task_id is not None:
                    self.progress.remove_task(self.task_id)

                # Update overall progress
                if self.is_running:
                    self.overall_progress.update(
                        self.overall_task,
                        advance=1,
                    )

                # Indicate task completion
                self.queue.task_done()


@click.command(name="download", help="Download all webinars from EventBrite")
@click.option("--output", help="Output directory")
@click.option("--threads", default=2, help="Number of download threads to use")
@click.option("--pagesize", default=20, help="Number of events to fetch per page")
@click.option("--email", required=True, help="Email to use for registration")
@click.option("--first-name", required=True, help="First name to use for registration")
@click.option("--last-name", required=True, help="Last name to use for registration")
@click.pass_context
def cli(
    ctx: click.Context,
    output: str,
    threads: int,
    pagesize: int,
    email: str,
    first_name: str,
    last_name: str,
):
    eventbrite: EventBrite = ctx.obj["client"]

    download_progress = Progress(
        TextColumn("[bold yellow]Downloading {task.fields[filename]}"),
        BarColumn(bar_width=None),
        DownloadColumn(binary_units=True),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    )

    generic_progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )

    overall_progress = Progress(TimeElapsedColumn(), BarColumn(bar_width=None), TextColumn("{task.description}"))

    group = Group(
        Panel(
            Group(
                generic_progress,
                download_progress,
            )
        ),
        overall_progress,
    )

    steps = [
        "Retrieving list of files...",
        "Getting valid StreamYard URLs...",
        "Getting valid VOD URLs...",
        "Downloading VODs...",
    ]
    current_step = 0
    overall_task_id = overall_progress.add_task("", total=len(steps))

    with Live(group):
        # Retrieve events
        overall_progress.update(
            overall_task_id,
            description=f"{steps[current_step]} ({current_step+1}/{len(steps)})",
        )
        task_id = generic_progress.add_task(steps[current_step], total=None)
        events = eventbrite.get_all_events(ORG_ID, pagesize)
        generic_progress.update(
            task_id, description=f"Found {len(events)} events.", completed=len(events), total=len(events)
        )
        generic_progress.stop_task(task_id)
        current_step += 1
        overall_progress.update(overall_task_id, advance=1)

        # Get StreamYard URLs
        overall_progress.update(
            overall_task_id,
            description=f"{steps[current_step]} ({current_step+1}/{len(steps)})",
        )
        task_id = generic_progress.add_task(steps[current_step], total=len(events))
        events = eventbrite.get_all_events(ORG_ID, pagesize)

        # TODO: multithreading to speed up the process
        urls = []
        for event in events:
            try:
                event_data = eventbrite.get_structured_content(event["id"])
                for x in event_data["modules"]:
                    if x["type"] == "webinar":
                        urls.append(x["data"]["webinar_url"]["url"])
            except requests.exceptions.HTTPError as e:
                overall_progress.console.print(f"Error while fetching event {event['id']}: {e}")
            except KeyError:
                overall_progress.console.print(f"Error while fetching event {event['id']}: No webinar URL")

            generic_progress.update(task_id, advance=1)
        generic_progress.update(
            task_id, description=f"Found {len(urls)} urls.", completed=len(events), total=len(events)
        )
        generic_progress.stop_task(task_id)
        current_step += 1
        overall_progress.update(overall_task_id, advance=1)

        # Get VODs URLs
        overall_progress.update(
            overall_task_id,
            description=f"{steps[current_step]} ({current_step+1}/{len(steps)})",
        )
        task_id = generic_progress.add_task(steps[current_step], total=len(urls))

        streamyard = StreamYard(
            proxies=ctx.obj["proxies"],
            verify=ctx.obj["verify"],
        )

        vod_download_data = []
        for url in urls:
            try:
                data = streamyard.get_webinar_info(url)

                # Registration needed
                if data["isRegistrationEnabled"] is True:
                    streamyard.register_webinar(url, data, email, first_name, last_name)

                    # Refresh data
                    data = streamyard.get_webinar_info(url)

                if "vodUrl" not in data:
                    raise Exception("VOD not found")

                if data["isVodMediaDeleted"] is True:
                    raise Exception("VOD media has been deleted")

                vod_download_data.append(
                    {
                        "title": data["title"],
                        "url": data["vodUrl"],
                        "poster": data["vodPosterUrl"],
                    }
                )
            except Exception as e:
                overall_progress.console.print(f"Error: {e} for {url}")
            finally:
                generic_progress.update(task_id, advance=1)
        generic_progress.update(
            task_id, description=f"Found {len(vod_download_data)} VODs.", completed=len(events), total=len(events)
        )
        generic_progress.stop_task(task_id)
        current_step += 1
        overall_progress.update(overall_task_id, advance=1)

        # Download VODs
        overall_progress.update(
            overall_task_id,
            description=f"{steps[current_step]} ({current_step+1}/{len(steps)})",
        )
        task_id = generic_progress.add_task(steps[current_step], total=len(vod_download_data))

        # Prepare output directory
        output_dir = pathlib.Path.cwd() / "output"
        output_dir.mkdir(exist_ok=True, parents=True)

        # Prepare queue
        queue = Queue()
        for file in vod_download_data:
            queue.put(file)

        workers: list[Thread] = []
        for _ in range(threads):
            # Add a sentinel to the queue to indicate the end of the queue
            queue.put(_sentinel)

            worker = DownloaderWorker(
                queue,
                output_dir,
                download_progress,
                (generic_progress, task_id),
            )
            worker.start()
            workers.append(worker)

        # TODO: won't work if uncommented
        # Wait for all files to download
        # queue.join()

        # Wait for all workers to finish
        try:
            for worker in workers:
                worker.join()
        except KeyboardInterrupt:
            print("Keyboard Interrupt received! Stopping workers...")
            _stop_event.set()

            # TODO: not sure if this is necessary
            # Wait for remaining workers to finish
            for worker in workers:
                worker.join()

        generic_progress.stop_task(task_id)
        current_step += 1
        overall_progress.update(overall_task_id, advance=1)
