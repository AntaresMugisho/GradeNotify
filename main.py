import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pprint import pprint

test_data = {
    "date": "2024-04-03T13:32:09.039364",
    "transcripts": [
        {
            "level": 1,
            "categories": [
                {
                    "code": "UE 111",
                    "title": "Cours d'appui I",
                    "courses": [
                        {
                            "code": "BANG 1101",
                            "title": "Texte",
                            "credits": 43,
                            "graded": 3,
                            "grade": "A+",
                            "gp": 44.4,
                            "percent": 3,
                            "credit_points":2,
                            "gpa": None
                        }
                    ]
                }
            ],
            "total": {
                "credits": 43,
                "graded": 3,
                "grade": None,
                "gp": 44,
                "percent": 3,
                "credit_points":2,
                "gpa": 45
            }
        }
    ]
}
data = {"date": datetime.now().isoformat(), "transcripts": []}
transcripts: list = data.get("transcripts")

def main():
    url = "https://mis.hau.bi/student/loadsingletranscriptforstudent2.php?level=&stucode=22100313"
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3'}

    try:
        response = requests.get(url, headers=headers)
        with open("index.html", "w") as file:
            file.write(response.text)
    except requests.exceptions.ConnectionError as e:
        print(f"Error: {e}")


def load():
    """
    Loads previously saved data from JSON
    :return: data
    """
    with open("data.json", "r") as file:
        data = json.load(file)
        return data


def save(data: dict):
    with open("data.json", "w") as file:
        json.dump(data, file, indent=4)


def scrap():
    with open("index.html", "r") as file:
        content = file.read()

    soup = BeautifulSoup(content, 'html.parser')
    marksheets = soup.find_all(id="transdetail")

    for i, marksheet in enumerate(marksheets):
        rows = marksheet.find_all("tr")

        transcript = {"level": i+1}

        # Create categories and courses
        categories = []
        courses = []
        for j, row in enumerate(rows):
            if j == 0:
                # Skip the first row cause it contains table heading
                continue

            table_data = row.find_all("td")

            # Create category
            if len(table_data) == 2:
                # A new category
                category = {
                    "code": table_data[0].text,
                    "title": table_data[1].text
                }
                categories.append(category)

            # Create course
            elif len(table_data) == 9:
                # A new course
                course = {
                    "code": table_data[0].text,
                    "title": table_data[1].text,
                    "credits": table_data[2].text,
                    "graded": table_data[3].text,
                    "grade": table_data[4].text,
                    "gp": table_data[5].text,
                    "percent": table_data[6].text,
                    "credit_points": table_data[7].text,
                    "gpa": table_data[8].text
                }

                courses.append(course)
                categories[-1].setdefault("courses", courses)

            elif len(table_data) == 8:
                # The total
                total = {
                    "credits": table_data[1].text,
                    "graded": table_data[2].text,
                    "grade": table_data[3].text,
                    "gp": table_data[4].text,
                    "percent": table_data[5].text,
                    "credit_points": table_data[6].text,
                    "gpa": table_data[7].text,
                }

                transcript.setdefault("total", total)

        transcript.setdefault("categories", categories)
        transcripts.append(transcript)

    # Add transcripts to the data object and save it
    data.setdefault("transcripts", transcripts)
    save(data)

if __name__ == "__main__":
    scrap()
