import requests
import csv
import os
from pathlib import Path
import json
from bs4 import BeautifulSoup

# ==============================
# CONFIG
# ==============================

jig_uidno_file_path = "jigyasu_uid.txt"
ini_uidno_file_path = "initiated_uid.txt"
jig_csv_path = "od_jigyasu_details.csv"
ini_csv_path = "od_initiated_details.csv"

INDEX_URL = "https://forma.dayalbagh.org.in/index.php"
OD_BRANCH_CODE = "B000214"

session = requests.Session()

columns = [
    "UID", "Affiliation", "NAME", "Father UID", "Fathers Name",
    "Mother UID", "Mother Name", "Spouse UID", "Spouse Name",
    "Date of Birth", "Date of Registration", "Occupation",
    "Address", "Email ID", "Phone Number", "Qualification", "Nationality"
]
# ==============================

def get_login_dets():
    file_path = Path("creds.json")

    if not file_path.exists():
        print("JSON file does not exist")
        return

    with file_path.open("r") as file:
        data = json.load(file)

    return data

def get_login_page(login_dets):
    login_url = f"{INDEX_URL}/login"
    login_page = session.get(login_url)
    login_page.raise_for_status()

    payload = {
        "_username": login_dets.get('username'),
        "_password": login_dets.get('passwd')
    }

    soup = BeautifulSoup(login_page.text, "html.parser")

    csrf_token = soup.find("input", {"name": "_csrf_token"})
    csrf_value = csrf_token["value"] if csrf_token else None

    if csrf_value:
        payload["_csrf_token"] = csrf_value

    login_response = session.post(login_url, data=payload)
    login_response.raise_for_status()

    return login_response

def save_data_to_csv(outdir, outfile, data):
    output_dir = Path(f"output/{outdir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = f'{output_dir}/{outfile}'

    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(columns)
        writer.writerow([data.get(col, "") for col in columns])

def parse_html_response(text):
    soup = BeautifulSoup(text, "html.parser")
    table = soup.find("table", {"id": "box-table-a"})

    rows = table.find_all("tr")

    data_dict = {}

    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) == 2:
            key = cols[0].get_text(strip=True)
            value = cols[1].get_text(separator=" ", strip=True)
            data_dict[key] = value

    return data_dict

def get_person_profile_data(outdir, outfile, url):
    response = session.get(url)
    if response.status_code == 200:
        data = parse_html_response(response.text)
        save_data_to_csv(outdir=outdir, outfile=outfile, data=data)

def get_person_details(outdir, outfile, uidno_file):
    data_url = f"{INDEX_URL}"

    if os.path.exists(uidno_file):
        with open(uidno_file, "r") as file:
            for line in file:
                uidno = (line.strip())
                data_url = f'{data_url}/viewonjigyasuselect?_uid={uidno}&_branchid={OD_BRANCH_CODE}'
                get_person_profile_data(outdir=outdir, outfile=outfile, url=data_url)
                print(f"Saving Data for {uidno} to: {outdir}/{outfile}")
                data_url = f"{INDEX_URL}"

    else:
        print("File does not exist")

# ==============================

def main():
    login_dets = get_login_dets()
    if login_dets is not  None:
        response = get_login_page(login_dets=login_dets)
        if response.status_code == 200:
            # Get Jigyasu details
            get_person_details(outdir="jigyasu", outfile=jig_csv_path, uidno_file=jig_uidno_file_path)
            # Get Initiated details
            # get_person_details(outdir="initiated", outfile=jig_csv_path, uidno_file=ini_uidno_file_path)

if __name__ == "__main__":
    main()

