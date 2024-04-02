import requests
from bs4 import BeautifulSoup
from pprint import pprint


def main():
    url = "https://mis.hau.bi/student/loadsingletranscriptforstudent2.php?level=&stucode=22100313"
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3'}

    try:
        response = requests.get(url, headers=headers)
        with open("index.html", "w") as file:
            file.write(response.text)
    except requests.exceptions.ConnectionError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
    with open("index.html", "r") as file:
        content = file.read()

    soup = BeautifulSoup(content,'html.parser')
    table = soup.find_all(id="transdetail")

    trs = table[0].find_all("tr")

    for tr in trs:
        td = tr.find_all("td")
        #print(len(td))

        # If len(td) == 9 : Header or course code, name and marks
        #               2 : Courses category
        #               8 : Total marks
        #               1 : Second semester indicator, can occure in case of no module also
