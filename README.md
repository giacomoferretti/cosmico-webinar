# Cosmico Webinar Downloader

Get all the StreamYard links for [Cosmico](https://www.eventbrite.it/o/cosmico-58596271643)'s webinars

## Usage

```text
$ cosmico-webinar --help

Usage: cosmico-webinar [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose     Enables verbose mode
  -p, --proxy TEXT  Use a proxy
  --no-verify       Disables SSL verification
  --help            Show this message and exit.

Commands:
  download  Download all webinars from EventBrite
  helpers   Helper commands
```

### Download all available VODs

> NOTE: Your email address, first name and last name are used to register to the webinar, if necessary.

`cosmico-webinar download --email YOUR_EMAIL_ADDRESS --first-name YOUR_NAME --last-name YOUR_LAST_NAME`
