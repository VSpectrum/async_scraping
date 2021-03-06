import asyncio
import aiohttp
import csv
from bs4 import BeautifulSoup

sema = asyncio.BoundedSemaphore(20)

BASE_URL = 'https://www.cricbuzz.com'

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

async def process_match(session: aiohttp.ClientSession, url: str, num: int):
    try:
        async with sema, session.request('GET', url=url) as resp:
            cricbuzz_match_resp = await resp.text()
            print(f"Received data for match #{num}")
            cricbuzz_match = BeautifulSoup(cricbuzz_match_resp, features="html.parser")
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
    except Exception as e:
        return (url, e)


async def get_matches(session: aiohttp.ClientSession, url: str) -> str:
    resp = await session.request('GET', url=url)
    body = await resp.text()
    possible_matches = []
    cricbuzz_matches = BeautifulSoup(body, features="html.parser")
    for a in cricbuzz_matches.find_all('a', href=True):
        if '/cricket-scores' in a['href']:
            possible_matches.append(BASE_URL+a['href'])
    return possible_matches

async def get_match_details(session: aiohttp.ClientSession, url: str) -> None:
    resp = await session.request('GET', url=url)
    body = await resp.text()
    print(f"Received data for {url}")

    possible_matches = []
    cricbuzz_matches = BeautifulSoup(body, features="html.parser")
    for a in cricbuzz_matches.find_all('a', href=True):
        if '/cricket-scores' in a['href']:
            possible_matches.append(BASE_URL+a['href'])
    return possible_matches


async def main():
    year = 2008
    scorecard_archives_url = f'https://www.cricbuzz.com/cricket-scorecard-archives/{year}'

    async with aiohttp.request('GET', url=scorecard_archives_url) as resp:
        resp = await resp.text()

    possible_series = []
    cricbuzz_series = BeautifulSoup(resp, features="html.parser")
    for a in cricbuzz_series.find_all('a', href=True):
        if '/matches' in a['href']:
            possible_series.append(BASE_URL+a['href'])
    print(f'# of Series found in {year}: {len(possible_series)}')

    # get all matches in year
    series_matches = ''
    async with aiohttp.ClientSession() as session:
        tasks = [get_matches(session, url) for url in possible_series]
        series_matches = await asyncio.gather(*tasks, return_exceptions=True)
    matches_in_year = [match for matches in series_matches for match in matches]
    
    print(f'# of Matches found in {year}: {len(matches_in_year)}')
    # get match details from match url list above
    async with aiohttp.ClientSession() as session:
        tasks = [process_match(session, url, num) for num, url in enumerate(matches_in_year)]
        series_matches = await asyncio.gather(*tasks, return_exceptions=True)

    for failed in series_matches:
        if failed:
            print()
    await asyncio.sleep(20)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
