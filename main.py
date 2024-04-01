import requests


def main():

    url = "https://mis.hau.bi/student/loadsingletranscriptforstudent2.php?level=&stucode=22100313"
    headers=("User-Agent : Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/109.0.0.0 Safari/537.3")
    response = requests.get(url, headers)

    with open("index.html", "w") as file:
        file.write(response.text)

if __name__ == "__main__":
    main()