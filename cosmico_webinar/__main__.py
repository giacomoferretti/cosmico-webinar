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

import click

from .commands import download, helpers
from .eventbrite import EventBrite

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    verbosity = logging.DEBUG if verbose else logging.INFO
    log_format = "[%(name)s:%(levelname)s] %(message)s" if verbose else "[%(levelname)s] %(message)s"

    logging.basicConfig(level=verbosity, format=log_format)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode")
@click.option("-p", "--proxy", type=str, help="Use a proxy")
@click.option("--no-verify", is_flag=True, help="Disables SSL verification")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, proxy: str, no_verify: bool):
    setup_logging(verbose)

    ctx.ensure_object(dict)
    ctx.obj["proxies"] = {}
    ctx.obj["verify"] = no_verify
    ctx.obj["verbose"] = verbose

    if proxy:
        ctx.obj["proxies"] = {"http": proxy, "https": proxy}

    ctx.obj["client"] = EventBrite(
        proxies=ctx.obj["proxies"],
        verify=ctx.obj["verify"],
    )


cli.add_command(download.cli)
cli.add_command(helpers.cli)

if __name__ == "__main__":
    cli()
