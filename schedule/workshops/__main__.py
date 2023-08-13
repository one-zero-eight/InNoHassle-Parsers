import json

import icalendar

from schedule.workshops.config import bootcamp_config as config
from schedule.workshops.models import WorkshopEvent
from schedule.workshops.parser import WorkshopParser
import re


def sluggify(text: str) -> str:
    # replace all whitespace characters with a single dash
    # drop all non-alphanumeric characters
    # drop all trailing dashes
    return re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", text)).strip("-").lower()


if __name__ == "__main__":
    parser = WorkshopParser()
    events = parser.get_events()
    directory = config.SAVE_ICS_PATH
    json_file = config.SAVE_JSON_PATH
    bootcamp_alias = f"bootcamp{config.YEAR_OF_BOOTCAMP}"
    bootcamp_tag = {"alias": bootcamp_alias, "type": "category"}
    workshops_tag = {"alias": "workshops", "type": bootcamp_alias}
    calendars_data = {"calendars": [], "tags": [bootcamp_tag, workshops_tag]}

    for workshop_event in events:
        workshop_event: WorkshopEvent
        workshop_calendar = icalendar.Calendar(
            prodid="-//one-zero-eight//InNoHassle Schedule",
            version="2.0",
            method="PUBLISH",
        )

        workshop_calendar[
            "x-wr-calname"
        ] = f"Bootcamp {config.YEAR_OF_BOOTCAMP} workshop: {workshop_event.summary}"
        workshop_calendar["x-wr-timezone"] = config.TIMEZONE
        workshop_calendar["x-wr-caldesc"] = "Generated by InNoHassle Schedule"

        workshop_calendar.add_component(workshop_event.get_vevent())
        workshop_slug = sluggify(workshop_event.summary)
        file_name = f"{workshop_slug}.ics"
        file_path = directory / file_name
        calendars_data["calendars"].append(
            {
                "path": file_path.relative_to(file_path.parents[-2]).as_posix(),
                "name": workshop_event.summary,
                "tags": [bootcamp_tag, workshops_tag],
                "alias": f"{bootcamp_alias}-{workshop_slug}",
            }
        )

        with open(file_path, "wb") as f:
            f.write(workshop_calendar.to_ical())
        # create a new .json file with information about calendars
    with open(json_file, "w") as f:
        json.dump(calendars_data, f, indent=4, sort_keys=True)

    with open(json_file.parent / "workshops.json", "w") as f:
        workshops = [
            {
                "name": workshop.summary,
                "alias": sluggify(workshop.summary),
                "timeslots": [
                    {
                        "start": timeslot[0].isoformat(),
                        "end": timeslot[1].isoformat()
                    }
                    for timeslot in workshop.timeslots
                ],
                "date": workshop.dtstart.date().isoformat(),
                "location": workshop.location,
                "speaker": workshop.speaker,
                "capacity": workshop.capacity,
                "comments": workshop.comments
            } for workshop in events
        ]

        json.dump({"workshops": workshops}, f, indent=4, sort_keys=True)