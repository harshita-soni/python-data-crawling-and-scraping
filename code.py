from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import urljoin
import csv
import json
import pandas as pd
import matplotlib.pyplot as plt
import re
import requests


def main():
    page_limit = 999  # high limit

    base_url = "http://comp20008-jh.eng.unimelb.edu.au:9889/main/"
    seed_item = "Hodg001.html"  # first url

    seed_url = base_url + seed_item
    page = requests.get(seed_url)
    soup = BeautifulSoup(page.text, 'html.parser')

    # dict to keep track of all the pages crawled
    visited = dict()
    pages_visited = 1

    seed_headline = soup.find('h1', class_='headline')
    visited[seed_url] = seed_headline.text

    # find all links in the current page
    links = soup.findAll('a')
    seed_link = soup.findAll('a', href=re.compile("^Hodg001.html"))

    # exclude all links that link to the same page
    to_visit_relative = [link for link in links if link not in seed_link]

    # absolute paths of pages to crawl next
    to_visit = list()
    for link in to_visit_relative:
        to_visit.append(urljoin(seed_url, link['href']))

    while to_visit:
        # Impose a limit to avoid breaking the site
        if pages_visited == page_limit:
            break

        link = to_visit.pop(0)

        page = requests.get(link)
        soup = BeautifulSoup(page.text, 'html.parser')

        headline = soup.find('h1', class_='headline')
        visited[link] = headline.text

        new_links = soup.findAll('a')

        for new_link in new_links:
            new_item = new_link['href']
            new_url = urljoin(link, new_item)
            if new_url not in visited and new_url not in to_visit:
                to_visit.append(new_url)

        pages_visited += 1

    with open('task1.csv', 'w', newline='') as file:
        columns = ['url', 'headline']
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for link in visited:
            writer.writerow({'url': link, 'headline': visited[link]})

    #############################
    #       end of task 1       #
    #############################
    with open("rugby.json") as file:
        rugby = json.load(file)
    # list of all rows to be added to the csv file
    rows_list = list()

    # team names in the json file
    teams = [team['name'] for team in rugby["teams"]]

    with open('task1.csv', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            url = row['url']
            headline = row['headline']
            content = get_content(url)
            article_content = headline + ' ' + content
            matching_team = get_best_match(article_content, teams)

            # skip the articles that don't have a team name or score
            if not matching_team:
                continue

            score = get_score(article_content)
            if not score:
                continue

            rows_list.append({'url': url,
                              'headline': headline,
                              'team': matching_team,
                              'score': score})

    with open('task2.csv', 'w', newline='') as file:
        column_names = ['url', 'headline', 'team', 'score']
        writer = csv.DictWriter(file, fieldnames=column_names)
        writer.writeheader()
        for row in rows_list:
            writer.writerow({'url': row['url'],
                             'headline': row['headline'],
                             'team': row['team'],
                             'score': row['score']})

    #############################
    #       end of task 2       #
    #############################

    teams_differences = defaultdict(list)
    with open('task2.csv', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            team = row['team']
            score = row['score']
            game_difference = get_absolute_game_difference(score)
            teams_differences[team].append(game_difference)

    with open('task3.csv', 'w', newline='') as file:
        column_names = ['team', 'avg_game_difference']
        writer = csv.DictWriter(file, fieldnames=column_names)
        writer.writeheader()

        for team in teams_differences:
            avg_difference = sum(teams_differences[team]) / len(teams_differences[team])
            writer.writerow({'team': team,
                             'avg_game_difference': avg_difference})

    #############################
    #       end of task 3       #
    #############################

    file = pd.read_csv('task2.csv')
    teams = file.iloc[:, 2]
    # count occurrence of each team in the articles scraped
    team_count = teams.value_counts()
    team_count.sort_values(ascending=False, inplace=True)

    # plot a bar graph
    graph1 = team_count.iloc[:5].plot(kind="bar", color=["crimson", "orange", "gold", "green", "steelblue"])
    graph1.set_xticklabels(team_count.iloc[:5].index, rotation=20)
    graph1.set_title("Top 5 Most Frequently Written Teams")
    graph1.set_xlabel("Team name")
    graph1.set_ylabel("Number of articles")
    plt.savefig('task4.png', dpi=300, bbox_inches='tight')
    plt.show()

    #############################
    #       end of task 4       #
    #############################

    # teams and their avg_difference
    left = pd.read_csv('task3.csv')

    # teams and number of articles about them
    right = pd.DataFrame({'team': team_count.index, 'article_freq': team_count})

    df = left.merge(right)

    # normalize the data so different variables can be plotted and compared together
    normalized_df = (df.iloc[:, 1:]) / (df.iloc[:, 1:].max())
    normalized_df['team'] = df['team']
    normalized_df.sort_values(by=['article_freq', 'avg_game_difference'],
                              ascending=[False, True], inplace=True)

    # plot a double bar graph
    graph2 = normalized_df.plot(kind="bar", color=["pink", "indigo"])
    graph2.set_xticklabels(normalized_df['team'], rotation=20)
    graph2.set_title("Comparing article frequency of each team vs their average game difference")
    graph2.set_xlabel("Team name")
    plt.savefig('task5.png', dpi=300, bbox_inches='tight')
    plt.show()

    #############################
    #       end of task 5       #
    #############################


def get_content(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    article = soup.find('div', id='article_detail')
    return article.text


def get_best_match(content, teams):
    # team_pos: list of two-tuples
    # ('index of position where team name was found, team name)
    team_pos = map(lambda team: (content.find(team), team), teams)
    valid_pos = list(filter(lambda x: x[0] >= 0, team_pos))

    if not valid_pos:
        return

    match_team = min(valid_pos, key=lambda x: x[0])  # first occurrence

    return match_team[1]  # return team name


def get_score(content):
    score_pattern = re.compile(r'\s(\d{1,3})-(\d{1,3})')

    matches = score_pattern.findall(content)

    if matches:
        scores = map(lambda x: get_score_from_match(x), matches)
        max_score_tuple = max(scores, key=lambda x: x[0])
        return max_score_tuple[1]
    return


def get_score_from_match(match):
    first, last = match
    return int(first) + int(last), f'{first}-{last}'


def get_absolute_game_difference(score):
    first, second = score.strip().split('-')
    difference = abs(int(first) - int(second))
    return difference


if __name__ == "__main__":
    main()
