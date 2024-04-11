import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger


load_dotenv()

logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add("logs/err.log", level="WARNING", rotation="512 Kb")

DB_FILE_PATH = Path(__file__).parent / "db.json"


def get_course(table_data: list) -> dict:
    """
    From a list of HTML table data create a course as a dictionary
    :param table_data: a list of td HTML tags containing a course details
    :return: a designed key - value course
    """
    course_keys = ["course_code", "course_title", "credits", "graded", "grade", "gp", "percent",
                   "credits_points", "gpa"]
    course_values = []
    for i in range(len(course_keys)):
        value = table_data[i].text if table_data[i].text else None
        if value is not None:
            value = int(value) if value.isnumeric() else float(value) if value.replace(".", "").isnumeric() else value

        course_values.append(value)

    return dict(zip(course_keys, course_values))


def get_category(table_data: list) -> dict:
    """
     From a list of HTML table data create a course category as a dictionary
    :param table_data: a list of td HTML tags containing a course category details
    :return: a designed key - value course
    """
    category = {
        "category_code": table_data[0].text,
        "category_title": table_data[1].text,
        "courses": []
    }
    return category


def get_total(table_data: list) -> dict:
    """
    From a list of HTML table data, represent marks details as a dictionary
    :param table_data: a list of td HTML tags containing the student grade total marks
    :return: a designed key - value marks details
    """
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
    """
    Write scrapped data into a JSON file
    :param data: The data obtained after the site scrapping
    """
    logger.info("Writing data into the JSON file...")
    if not DB_FILE_PATH.exists():
        with open(DB_FILE_PATH, "w") as file:
            file.write("")

    with open(DB_FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_previous_data() -> dict:
    """
    Get previously saved student marks from JSON file
    :return: The previously saved student marks or empty dict if there was no previously saved data
    """
    logger.info("Reading data from JSON file...")
    try:
        with open(DB_FILE_PATH, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.warning(f"Can't find the JSON file.")
        return {}

    return data


def extract_courses(data: dict) -> list:
    """
    Get courses from all transcripts
    :param data: JSON data containing all student transcripts as well as their courses details
    :return: The list of courses extracted from all transcripts
    """
    courses = []
    if data.get("transcripts"):
        for transcript in data["transcripts"]:
            categories = transcript["first_semester"]["categories"] + transcript["second_semester"]["categories"]
            for category in categories:
                courses.extend(category["courses"])

    return courses


def compare(previous: dict, actual: dict):
    """
    Check if there is difference between previously saved transcripts and the actually scrapped one
    :param previous: The old student transcripts saved on DB_FILE
    :param actual: The actual transcripts as scrapped from the university website
    :return: A list of courses that changed or False if there is no difference between old and actual transcripts
    """
    old_courses = extract_courses(previous)
    actual_courses = extract_courses(actual)

    diff = [course for course in actual_courses if course not in old_courses]
    if not diff:
        return False

    return diff


def notify(message: str):
    """
    Send a notification to the student using Pushover API
    :param message: The message to be sent as notification
    """
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


def scrap(html_content: str) -> dict:
    """
    Scrap the university website to extract student transcripts
    :param html_content: The HTML page content to scrap
    :return: A structured dictionary containing student transcripts
    """
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

            # If a row contains 2 td tags, it's a category row
            if len(tds) == 2:
                category = get_category(tds)
                categories.append(category)

            # If a row contains 9 td tags, it's a course row
            elif len(tds) == 9:
                course = get_course(tds)
                categories[-1]["courses"].append(course)

            # If a row contains 8 td tags, it's a total row
            elif len(tds) == 8:
                total = get_total(tds)
                totals.append(total)

                # As the total row is the last, append categories to the semesters list and clear them to prepare
                # the next semester categories
                semesters.append(categories)
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
    url = f"https://mis.hau.bi/student/loadsingletranscriptforstudent2.php?stucode={os.environ['STUDENT_CODE']}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/109.0.0.0 Safari/537.3'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error while requesting the page : {e}")
    else:
        actual_data = scrap(response.text)
        previous_data = get_previous_data()

        updated = compare(previous_data, actual_data)
        if updated:
            message = f"Hello {os.environ['STUDENT_NAME']} 👋, some of your grades were updated:\n"
            for course in updated:
                message += f"    • {course['course_title'].strip()} : {course['percent']} %\n"

            notify(message)
            save_data(actual_data)
