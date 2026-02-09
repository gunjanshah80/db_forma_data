import requests
import csv
import os
from pathlib import Path
import json
from bs4 import BeautifulSoup

# ==============================
# CONFIG
# ==============================

jig_outdir = "jigyasu"
ini_outdir = "initiated"
jig_uidno_file_path = "jigyasu_uid.txt"
ini_uidno_file_path = "initiated_uid.txt"
jig_csv_file = "od_jigyasu_details.csv"
ini_csv_file = "od_initiated_details.csv"

INDEX_URL = "https://forma.dayalbagh.org.in/index.php"
OD_BRANCH_CODE = "B000214"

session = requests.Session()

jig_columns = [
    "UID", "Affiliation", "NAME", "Father UID", "Fathers Name",
    "Mother UID", "Mother Name", "Spouse UID", "Spouse Name",
    "Date of Birth", "Date of Registration", "Occupation",
    "Address", "Email ID", "Phone Number", "Qualification", "Nationality"
]

ini_columns = [
    "UID", "Affiliation", "NAME", "Fathers Name", "Husbands Name",
    "Date of Birth", "Occupation", "Address", "Email ID", "Phone Number",
    "Date of First Initiation", "Date of Second Initiation",
    "Qualification", "Nationality", "Membership Type"
]

skip_fields = {"Nee", "Caste"}

file_path_list = [f'output/{jig_outdir}/{jig_csv_file}',
                  f'output/{ini_outdir}/{ini_csv_file}']
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

def save_data_to_csv(outdir, outfile, data, columns):
    output_dir = Path(f"output/{outdir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = f'{output_dir}/{outfile}'

    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(columns)
        writer.writerow([data.get(col, "") for col in columns if col not in skip_fields])

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

def get_person_profile_data(outdir, outfile, url, columns):
    response = session.get(url)
    if response.status_code == 200:
        #print(response.text)
        data = parse_html_response(response.text)
        save_data_to_csv(outdir=outdir, outfile=outfile, data=data, columns=columns)

def get_person_details(url, outdir, outfile, uidno_file, columns):
    data_url = url

    if os.path.exists(uidno_file):
        with open(uidno_file, "r") as file:
            for line in file:
                uidno = (line.strip())
                data_url = f'{data_url}_uid={uidno}&_branchid={OD_BRANCH_CODE}'
                get_person_profile_data(outdir=outdir, outfile=outfile, url=data_url, columns=columns)
                data_url = url

    else:
        print("File does not exist")

def cleanup_file():
   for file_path in file_path_list:
       # Check if file exists and remove it
        if os.path.isfile(file_path):
            os.remove(file_path)
# ==============================

def main():
    login_dets = get_login_dets()
    if login_dets is not  None:
        response = get_login_page(login_dets=login_dets)
        if response.status_code == 200:
            cleanup_file()
            # Get Jigyasu details
            print(f"*******************************************************")
            print(f"Saving Data for Jigyasu brothers and sisters...")
            get_person_details(url=f"{INDEX_URL}/viewonjigyasuselect?"
                               ,outdir=jig_outdir
                               ,outfile=jig_csv_file
                               ,uidno_file=jig_uidno_file_path
                               ,columns=jig_columns)
            print(f"*******************************************************")
            print(f"Saving Data for Initiated brothers and sisters...")
            # Get Initiated details
            get_person_details(url=f"{INDEX_URL}/viewonuidselect?"
                               ,outdir=ini_outdir
                               ,outfile=ini_csv_file
                               ,uidno_file=ini_uidno_file_path
                               ,columns=ini_columns)
            print(f"*******************************************************")

if __name__ == "__main__":
    main()
