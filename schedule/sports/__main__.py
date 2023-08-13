import asyncio
import json
import logging
from itertools import groupby

import aiohttp as aiohttp
import icalendar

from schedule.sports.config import sports_config as config
from schedule.sports.models import SportScheduleEvent
from schedule.sports.parser import SportParser


async def main():
    async with aiohttp.ClientSession(
        headers={"Content-Type": "application/json"}
    ) as session:
        logging.basicConfig(level=logging.INFO)
        parser = SportParser(session)
        logger = SportParser.logger

        get_sports_answer = await parser.get_sports()
        sports = {sport.id: sport for sport in get_sports_answer.sports}
        sport_schedules = await parser.batch_get_sport_schedule(sports.keys())

        sport_events = []

        for sport_id, sport_schedule in sport_schedules.items():
            sport = sports[sport_id]
            _sport_events = [
                SportScheduleEvent(
                    sport=sport, sport_schedule_event=sport_schedule_event
                )
                for sport_schedule_event in sport_schedule.__root__
            ]
            sport_events.extend(_sport_events)
        logger.info(f"Processed {len(sport_events)} sport events")

        grouping = lambda x: (x.sport.name, x.sport_schedule_event.title or "")
        sport_events.sort(key=grouping)

        calendars = {
            "calendars": [],
            "title": "Sport",
            "filters": [{"alias": "sport_type", "name": "Sport type"}],
        }

        directory = config.SAVE_ICS_PATH
        logger.info(f"Saving calendars to {directory}")
        json_file = config.SAVE_JSON_PATH
        logger.info(f"Saving json to {json_file}")
        logger.info(f"Grouping events by sport.name and sport_schedule_event.title")
        for (title, subtitle), events in groupby(sport_events, key=grouping):
            calendar = icalendar.Calendar(
                prodid="-//one-zero-eight//InNoHassle Schedule",
                version="2.0",
                method="PUBLISH",
            )
            calendar_name = f"{title} - {subtitle}" if subtitle else title
            logger.info(f"Saving {calendar_name} calendar")
            calendar["x-wr-calname"] = calendar_name
            calendar["x-wr-timezone"] = config.TIMEZONE
            calendar["x-wr-caldesc"] = "Generated by InNoHassle Schedule"

            vevents = [
                event.get_vevent(config.START_OF_SEMESTER, config.END_OF_SEMESTER)
                for event in events
            ]
            calendar.subcomponents.extend(vevents)
            filename = f"{calendar_name.replace(' ', '').lower()}.ics"
            file_path = directory / filename
            calendars["calendars"].append(
                {
                    "name": calendar_name,
                    "path": file_path.relative_to(json_file.parent).as_posix(),
                    "type": "sports",
                    "satellite": {"sport_type": calendar_name},
                }
            )

            with open(file_path, "wb") as file:
                file.write(calendar.to_ical())

        logger.info(f"Saving calendars information to {json_file}")
        with open(json_file, "w") as f:
            json.dump(calendars, f, indent=4, sort_keys=True)

        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())