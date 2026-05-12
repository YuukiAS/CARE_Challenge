#!/usr/bin/env python3
"""Fetch CARE2026 validation leaderboard scores for a configured track."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_CONFIG = Path(__file__).with_name("config.json")
DEFAULT_COLUMNS = ["rank", "user", "time"]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def request_json(
    base_url: str,
    endpoint: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = None
    req_headers = dict(headers or {})
    if data is not None:
        body = urlencode(data).encode("utf-8")
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = Request(
        base_url.rstrip("/") + "/" + endpoint.lstrip("/"),
        data=body,
        headers=req_headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {endpoint}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed for {endpoint}: {exc}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {endpoint}: {payload[:500]}") from exc


def require_success(payload: dict[str, Any], endpoint: str) -> dict[str, Any]:
    if payload.get("msg") != "success":
        raise RuntimeError(f"{endpoint} failed: {payload}")
    return payload


def login(config: dict[str, Any]) -> str:
    payload = require_success(
        request_json(
            config["base_url"],
            "/login",
            method="POST",
            data={
                "username": config["username"],
                "password": config["password"],
                "track": config["track"],
            },
        ),
        "/login",
    )
    token = payload.get("data", {}).get("token")
    if not token:
        raise RuntimeError(f"/login did not return a token: {payload}")
    return str(token)


def fetch_tasks(config: dict[str, Any], headers: dict[str, str]) -> dict[str, str]:
    payload = require_success(
        request_json(config["base_url"], "/getdata", headers=headers),
        "/getdata",
    )
    tasks = payload.get("task", {})
    if not isinstance(tasks, dict):
        raise RuntimeError(f"/getdata returned unexpected task payload: {tasks}")
    return {task_id: str(info.get("name", task_id)) for task_id, info in tasks.items()}


def fetch_rank(config: dict[str, Any], headers: dict[str, str], task_id: str) -> list[dict[str, Any]]:
    payload = require_success(
        request_json(
            config["base_url"],
            "/get_rank",
            method="POST",
            data={"taskid": task_id},
            headers=headers,
        ),
        f"/get_rank taskid={task_id}",
    )
    rows = payload.get("rankdata", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"/get_rank returned unexpected rankdata for {task_id}: {rows}")
    return [row if isinstance(row, dict) else {"value": row} for row in rows]


def ordered_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for name in DEFAULT_COLUMNS:
        if any(name in row for row in rows):
            columns.append(name)
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = ordered_columns(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--task", action="append", help="Task id to fetch. Defaults to config default_tasks, or all /getdata tasks if unset.")
    parser.add_argument("--output-dir", type=Path, help="Override config output_dir.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    output_dir = args.output_dir or Path(config.get("output_dir", "results/leaderboard"))
    output_dir.mkdir(parents=True, exist_ok=True)

    token = login(config)
    headers = {"Authorization": token, "track": config["track"]}
    tasks = fetch_tasks(config, headers)
    task_ids = args.task or config.get("default_tasks") or list(tasks)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {
        "fetched_at_utc": timestamp,
        "track": config["track"],
        "tasks": {},
    }

    for task_id in task_ids:
        rows = fetch_rank(config, headers, task_id)
        result["tasks"][task_id] = {
            "name": tasks.get(task_id, task_id),
            "rows": rows,
        }
        csv_path = output_dir / f"care2026_{config['track']}_{task_id}_{timestamp}.csv"
        latest_csv_path = output_dir / f"care2026_{config['track']}_{task_id}_latest.csv"
        write_csv(csv_path, rows)
        write_csv(latest_csv_path, rows)
        print(f"{task_id}: {len(rows)} rows -> {latest_csv_path}")

    json_path = output_dir / f"care2026_{config['track']}_{timestamp}.json"
    latest_json_path = output_dir / f"care2026_{config['track']}_latest.json"
    for path in (json_path, latest_json_path):
        with path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print(f"raw json -> {latest_json_path}")


if __name__ == "__main__":
    main()
