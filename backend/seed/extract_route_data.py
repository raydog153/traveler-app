"""One-time extraction of the `routeData` JS literal embedded in
bus_route_map.html into a committed fixture (fixtures/route_data.json).

`routeData` is used only as a historical lat/lng lookup during seeding (see
seed.py) -- the seeded gas rows are joined to it by city + reconstructed
full date, which is what disambiguates cities that share a short name across
different states/years (e.g. "Georgetown" appears as a first-visit city in
both the 2022 and 2023 groups).

Run once:

    python -m seed.extract_route_data /path/to/bus_route_map.html

Known correction (manually applied to fixtures/route_data.json, NOT
automatically re-applied by this script): "Pembroke" was moved from the 2022
group to the 2021 group, to match a year typo fixed in gas_raw.json (see the
docstring in extract_gas_maintenance.py) -- the source HTML's routeData was
itself derived from the same mis-dated sheet row, so it inherited the error.
If this script is re-run against a fresh bus_route_map.html, re-check whether
this correction still needs to be re-applied.
"""

import json
import re
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def main(html_path: str) -> None:
    html = Path(html_path).read_text()
    match = re.search(r"const routeData = (\{.*?\});", html, re.DOTALL)
    if not match:
        raise SystemExit("could not find `const routeData = ...;` in the given HTML file")

    route_data = json.loads(match.group(1))

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIXTURES_DIR / "route_data.json"
    out_path.write_text(json.dumps(route_data, indent=2))

    n_locations = sum(len(day["locations"]) for day in route_data["days"])
    print(f"route data: {len(route_data['days'])} years, {n_locations} cities -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m seed.extract_route_data /path/to/bus_route_map.html")
        sys.exit(1)
    main(sys.argv[1])
