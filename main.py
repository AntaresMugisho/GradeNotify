import json
import os
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger


load_dotenv()

logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add("logs/err.log", level="WARNING", rotation="512 Kb")


def get_course(table_data: list) -> dict:
    course_keys = ["course_code", "course_title", "credits", "graded", "grade", "gp", "percent", "credits_points",
                   "gpa"]
    course_values = []
    for i in range(9):
        value = table_data[i].text if table_data[i].text else None
        if value and value.isnumeric():
            value = int(value)
        elif value:
            try:
                value = float(value)
            except ValueError:
                pass
        course_values.append(value)

    course = dict(zip(course_keys, course_values))
    return course


def get_category(table_data: list) -> dict:
    category = {
        "category_code": table_data[0].text,
        "category_title": table_data[1].text,
        "courses": []
    }
    return category


def get_total(table_data: list) -> dict:
    total = {
        "credits": int(table_data[1].text),
        "graded": int(table_data[2].text),
        "grade": table_data[3].text,
        "gp": float(table_data[4].text),
        "percent": float(table_data[5].text),
        "credit_points": float(table_data[6].text),
        "gpa": float(table_data[7].text),
    }
    return total


def save_data(data: dict):
    try:
        with open("data.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Can't save data in file: {e}")


def get_previous_data() -> dict:
    """
    Loads previously saved data from JSON
    :return: data
    """
    with open("data.json", "r") as file:
        previous_data = json.load(file)
        return previous_data



def extract_courses(data: dict) -> list:
    courses = []
    for transcript in data["transcripts"]:
        categories = transcript["first_semester"]["categories"] + transcript["second_semester"]["categories"]
        for category in categories:
            courses.extend(category["courses"])

    return courses


def compare(previous: dict, actual: dict):

    old_courses = extract_courses(previous)
    actual_courses = extract_courses(actual)

    diff = [course for course in actual_courses if course not in old_courses]

    if not diff:
        return False

    return diff


def notify(message: str):
    try:
        requests.post("https://api.pushover.net/1/messages.json", data={
            'user': os.environ["PUSHOVER_USER"],
            'token': os.environ["PUSHOVER_TOKEN"],
            'message': message,
            'url': "https://mis.hau.bi",
            'url_title': "View in the browser"
        }).raise_for_status()

    except requests.RequestException as e:
        logger.error(f"Failed to send notification : {e}")
        raise e


def scrap(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all(id="transdetail")

    transcripts = [{} for _ in tables]

    for i, table in enumerate(tables):
        # Create a single transcript
        rows = table.find_all("tr")

        semesters = []
        categories = []
        totals = []

        # Skip the first row cause it contains table heading that is not interesting us
        for row in rows[1:]:
            tds = row.find_all("td")

            # If a row contains 2 td, it's a category row
            if len(tds) == 2:
                category = get_category(tds)
                categories.append(category)

            # If a row contains 9 td, it's a course row
            elif len(tds) == 9:
                course = get_course(tds)
                categories[-1]["courses"].append(course)

            # If a row contains 8 td, it's a total row
            elif len(tds) == 8:
                total = get_total(tds)
                totals.append(total)

                semesters.append(categories)

            # In the case row contains 1 td, it's a second semester start row
            elif len(tds) == 1:
                categories = []

        # Write collected data in a transcript
        if len(semesters) == 0:
            totals = [{}, {}]
            semesters = [[], []]
        elif len(semesters) == 1:
            totals.append({})
            semesters.append([])

        transcripts[i] = {
            "level": i + 1,
            "first_semester": {
                "total": totals[0],
                "categories": semesters[0],
            },
            "second_semester": {
                "total": totals[1],
                "categories": semesters[1],
            }
        }

    return {
        "date": datetime.now().isoformat(),
        "transcripts": transcripts
    }


if __name__ == "__main__":
    url = f"https://mis.hau.bi/student/loadsingletranscriptforstudent2.php?stucode={os.environ['STUCODE']}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/109.0.0.0 Safari/537.3'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error while requesting the page : {e}")
    else:
        previous_data = get_previous_data()
        actual_data = scrap(response.text)
        updated = compare(previous_data, actual_data)

        if updated:
            message = "Hello Antares, some of your grades were updated:\n"
            for course in updated:
                message += f"    • {course['course_title'].strip()} : {course['percent']} %\n"

            notify(message)
            save_data(actual_data)
