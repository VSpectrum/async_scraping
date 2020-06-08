import requests
from bs4 import BeautifulSoup
from time import sleep
import csv

years_of_interest = [year for year in range(2016, 2017)]
BASE_URL = 'https://www.cricbuzz.com'

def process_match(match: str):
    print(f'fetching match: {match}')
    cricbuzz_match_resp = requests.get(match)
    cricbuzz_match = BeautifulSoup(cricbuzz_match_resp.text, features="html.parser")
    game_actions = cricbuzz_match.find_all(["p", "span"], ["cb-col-90", "cb-col-8"])
    game_actions_cleaned = []
    action_list = []
    for i in range(len(game_actions)):
        if i & 1:  # description
            action_list += clean_action(game_actions[i].text)
            game_actions_cleaned.append(action_list)
            action_list = []
        else:  # ball number
            action_list.append(game_actions[i].text)
    match_name = cricbuzz_match.find(["h1"]).text.split(',')[0].replace(' ', '_')
    match_date =  cricbuzz_match.find(attrs={"itemprop": "startDate"})['content'].split('T')[0]

    if game_actions_cleaned:
        with open(f'data/{match_name}T{match_date}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(game_actions_cleaned)
    else:
        with open('invalid_match.txt', 'a') as logfile:
            logfile.write(match)
            logfile.write('\n')

def clean_action(description: str) -> list:
    description = description.lower()
    if ' to ' in description:
        description = description.replace(' to ', ',').replace('!', ',')
    description = description.replace('no run', '0').replace('six', '6').replace('four', '4')
    description = description.replace('1 run', '1').replace('2 runs', '2').replace('3 runs', '3')
    parts = [part.strip() for part in description.split(',')[:3]]
    
    out_reason = ""
    if len(parts) == 3 and 'out' in parts[2]:
        out_reason = parts[2].replace('out', '').strip()
        parts[2] = 'out'
    parts.append(out_reason)
    
    return parts


for year in years_of_interest:
    print(f'fetching for year: {year}')
    scorecard_archives_url = f'https://www.cricbuzz.com/cricket-scorecard-archives/{year}'
    resp = requests.get(scorecard_archives_url)
    
    possible_series = []
    cricbuzz_series = BeautifulSoup(resp.text, features="html.parser")
    for a in cricbuzz_series.find_all('a', href=True):
        if '/matches' in a['href']:
            possible_series.append(BASE_URL+a['href'])
    print(f'# of Series found in {year}: {len(possible_series)}')

    possible_matches = []
    for idx, matches in enumerate(possible_series):
        print(f'aggregating matches (/cricket-scores/) in series #{idx}')
        cricbuzz_matches_resp = requests.get(matches)
        cricbuzz_matches = BeautifulSoup(cricbuzz_matches_resp.text, features="html.parser")
        for a in cricbuzz_matches.find_all('a', href=True):
            if '/cricket-scores' in a['href']:
                possible_matches.append(BASE_URL+a['href'])
            
    for match in possible_matches:
        process_match(match)
print("Done!")