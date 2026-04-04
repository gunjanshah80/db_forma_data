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
ma_outdir = "ma_members"
jig_uidno_file_path = "jigyasu_uid.txt"
ini_uidno_file_path = "initiated_uid.txt"
ma_uidno_file_path = "ma_uid.txt"
jig_csv_file = "od_jigyasu_details.csv"
ini_csv_file = "od_initiated_details.csv"
ma_csv_file = "ma_members_details.csv"

INDEX_URL = "https://forma.dayalbagh.org.in/index.php"
MA_INDEX_URL = "https://branch.dbapps.in"
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

ma_columns = [
    "Name", "UID", "Member Type", "Member Role",
    "Qualification", "Occupation", "Email", "Mobile No", "Address"
]

skip_fields = {"Nee", "Caste"}

file_path_list = []

# ==============================
def get_forma_login_dets():
    file_path = Path("creds.json")

    if not file_path.exists():
        print("JSON file does not exist")
        return

    with file_path.open("r") as file:
        data = json.load(file)

    return data

def get_ma_login_dets():
    file_path = Path("ma_creds.json")

    if not file_path.exists():
        print("JSON file does not exist")
        return

    with file_path.open("r") as file:
        data = json.load(file)

    return data

def get_login_page(login_dets, url, opt):

    if opt == 1:
        payload = {
            "_username": login_dets.get('username'),
            "_password": login_dets.get('passwd')
        }
        login_page = session.get(url)
        login_page.raise_for_status()
    elif opt == 2:
        payload = {
            "usernameMahilaAssoc": login_dets.get('username'),
            "userpassword": login_dets.get('passwd')
        }
        login_page = session.post(url)
        login_page.raise_for_status()

    soup = BeautifulSoup(login_page.text, "html.parser")

    csrf_token = soup.find("input", {"name": "_csrf_token"})
    csrf_value = csrf_token["value"] if csrf_token else None

    if csrf_value:
        payload["_csrf_token"] = csrf_value

    login_response = session.post(url, data=payload)
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
    ma_flag = False
    soup = BeautifulSoup(text, "html.parser")
    table = soup.find("table", {"id": "box-table-a"})

    if table is None:
        # Just find table
        table = soup.find("table")
        ma_flag = True

    rows = table.find_all("tr")

    data_dict = {}

    for row in rows:
        if ma_flag:
            key = row.find("th")
            value = row.find("td")
            if key and value:
                key = key.get_text(strip=True)
                value = value.get_text(strip=True)
                data_dict[key] = value
        else:
            cols = row.find_all("td")
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                value = cols[1].get_text(separator=" ", strip=True)
                data_dict[key] = value

    return data_dict

def get_person_profile_data(outdir, outfile, url, columns):
    response = session.get(url)
    if response.status_code == 200:
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

def get_ma_members_details(url, outdir, outfile, uidno_file, columns):
    data_url = url

    if os.path.exists(uidno_file):
        with open(uidno_file, "r") as file:
            for line in file:
                uidno = (line.strip())
                data_url = f'{data_url}?uid={uidno}'
                get_person_profile_data(outdir=outdir, outfile=outfile, url=data_url, columns=columns)
                data_url = url
    else:
        print("File does not exist")

def cleanup_file(opt):

    if opt == 1:
        file_path_list.append(f'output/{jig_outdir}/{jig_csv_file}')
        file_path_list.append(f'output/{ini_outdir}/{ini_csv_file}')
    elif opt == 2:
        file_path_list.append(f'output/{ma_outdir}/{ma_csv_file}')

    for file_path in file_path_list:
       # Check if file exists and remove it
        if os.path.isfile(file_path):
            os.remove(file_path)

# ==============================

def main():
    choice = input("Enter choice of data to be generated (1 - FormA, 2 - MA)\n")
    if choice == "1":
        login_dets = get_forma_login_dets()
        if login_dets is not None:
            response = get_login_page(login_dets=login_dets, url=f"{INDEX_URL}/login", opt=1)
            if response.status_code == 200:
                cleanup_file(opt=1)
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
    elif choice == "2":
        login_dets = get_ma_login_dets()
        if login_dets is not None:
            response = get_login_page(login_dets=login_dets, url=f"{MA_INDEX_URL}/login", opt=2)
            if response.status_code == 200:
                cleanup_file(opt=2)
                # Get MA details
                print(f"*******************************************************")
                print(f"Saving Data for Mahilla Asso. Members...")
                get_ma_members_details(url=f"{MA_INDEX_URL}/mahila-association/member/view-one"
                                       ,outdir=ma_outdir
                                       ,outfile=ma_csv_file
                                       ,uidno_file=ma_uidno_file_path
                                       ,columns=ma_columns)

    print(f"*******************************************************")

if __name__ == "__main__":
    main()
