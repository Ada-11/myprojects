
"""Simple script with a helper to fetch JSON from a URL."""

print("this is a simple python line of code")

from typing import Any
import json
import urllib.request
import urllib.error


def fetch_json(url: str, timeout: int = 10) -> Any:
	"""Fetch the given URL and return the parsed JSON.

	Raises urllib.error.URLError on network issues and ValueError on
	invalid JSON.
	"""
	req = urllib.request.Request(url, headers={"User-Agent": "python-urllib/3"})
	with urllib.request.urlopen(req, timeout=timeout) as resp:
		charset = resp.headers.get_content_charset(failobj="utf-8")
		data = resp.read().decode(charset)
		return json.loads(data)


if __name__ == "__main__":
	# example usage (won't run in tests if no network is available)
	try:
		sample = fetch_json("https://jsonplaceholder.typicode.com/todos/1")
		print("Fetched JSON:", sample)
	except Exception as e:
		print("Error fetching JSON:", e)

