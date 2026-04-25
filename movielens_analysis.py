#!/usr/bin/env python3
from collections import defaultdict, Counter, OrderedDict
from datetime import datetime, timezone
import re
import pytest
import sys
import os
from unittest.mock import Mock, patch
import requests
import json
from bs4 import BeautifulSoup



def average(values):
    return sum(values) / len(values)

def median(values):
    vals = sorted(values)
    n = len(vals)
    mid = n // 2

    if n % 2 == 1:
        return vals[mid]
    else:
        return (vals[mid - 1] + vals[mid]) / 2

class Ratings:
    """
    Analyzing data from ratings.csv
    """
    def __init__(self, path_to_the_file):
        self.ratings = []
        self.by_movie = defaultdict(list)
        self.by_user = defaultdict(list)
        with open(path_to_the_file, "r") as f:
            try:
                header = f.readline().strip()
                if header != "userId,movieId,rating,timestamp":
                    raise Exception("wrong header")
            except Exception as e:
                print(f"error handled: {e}, u r dummy")

            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(",")
                    if len(parts) != 4:
                        raise Exception("wrong number of fields")
                    
                    user_s, movie_s, rating_s, ts_s = parts
                    user_id = int(user_s)
                    movie_id = int(movie_s)
                    rating = float(rating_s)
                    timestamp = int(ts_s)

                    if timestamp <= 0:
                        raise ValueError("timestamp must be positive")
                    if rating < 0.5 or rating > 5.0 or rating * 2 != int(rating * 2):
                        raise ValueError("rating must be from 0.5 to 5.0 with step 0.5")
                    year = datetime.fromtimestamp(timestamp, tz=timezone.utc).year
                    record = {
                        "user": user_id,
                        "movie": movie_id,
                        "rating": rating,
                        "year": year,
                    }

                    self.ratings.append(record)
                    self.by_movie[movie_id].append(record)
                    self.by_user[user_id].append(record)

                except Exception as e:
                    print(f"error handled: {e} for line: {line}")
        self.movies = self.Movies(self)
        self.users = self.Users(self)

    class Movies:

        def __init__(self, parent):
            self.parent = parent

        def dist_by_year(self):
            """
            The method returns a dict where the keys are years and the values are counts. 
            Sort it by years ascendingly. You need to extract years from timestamps.
            """
            ratings_by_year = Counter()
            for record in self.parent.ratings:
                ratings_by_year[record["year"]] += 1

            return dict(sorted(ratings_by_year.items()))
        
        def dist_by_rating(self):
            """
            The method returns a dict where the keys are ratings and the values are counts.
         Sort it by ratings ascendingly.
            """
            ratings_distribution = Counter()
            for record in self.parent.ratings:
                ratings_distribution[record["rating"]] += 1

            return dict(sorted(ratings_distribution.items()))
        
        def top_by_num_of_ratings(self, n):
            """
            The method returns top-n movies by the number of ratings. 
            It is a dict where the keys are movie titles and the values are numbers.
            Sort it by numbers descendingly.
            """
            counts = {}
            for mid, lst in self.parent.by_movie.items():
                counts[mid] = len(lst)
            top_movies = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
            return dict(top_movies)
        
        def top_by_ratings(self, n, metric=average):
            """
            The method returns top-n movies by the average or median of the ratings.
            It is a dict where the keys are movie titles and the values are metric values.
            Sort it by metric descendingly.
            The values should be rounded to 2 decimals.
            """
            scores = {}

            for mid, lst in self.parent.by_movie.items():
                ratings = [r["rating"] for r in lst]
                value = metric(ratings)
                scores[mid] = round(value, 2)

            top_movies = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]
            
            return dict(top_movies)
        
        def top_controversial(self, n):
            """
            The method returns top-n movies by the variance of the ratings.
            It is a dict where the keys are movie titles and the values are the variances.
          Sort it by variance descendingly.
            The values should be rounded to 2 decimals.
            """

            scores = {}
            
            for mid, lst in self.parent.by_movie.items():
                ratings = [r["rating"] for r in lst]
                mean = average(ratings)
                value = average([(x - mean) ** 2 for x in ratings])
                scores[mid] = round(value, 2)

            top_movies = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

            return dict(top_movies)
        def most_polarized(self, n, min_votes=10):
            """
            Returns top-n movies with high variance and enough ratings.
            """
            scores = {}

            for mid, lst in self.parent.by_movie.items():
                if len(lst) < min_votes:
                    continue

                ratings = [r["rating"] for r in lst]
                mean = average(ratings)
                var = average([(x - mean) ** 2 for x in ratings])
                scores[mid] = round(var, 2)

            return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n])

    class Users:
        """
        In this class, three methods should work. 
        The 1st returns the distribution of users by the number of ratings made by them.
        The 2nd returns the distribution of users by average or median ratings made by them.
        The 3rd returns top-n users with the biggest variance of their ratings.
     Inherit from the class Movies. Several methods are similar to the methods from it.
        """
        def __init__(self, parent):
            self.parent = parent

        def dist_by_num_of_ratings(self):
            counter = Counter()

            for ratings in self.parent.by_user.values():
                counter[len(ratings)] += 1

            return dict(sorted(counter.items()))
        
        def dist_by_ratings(self, metric=average):
            counter = Counter()

            for ratings in self.parent.by_user.values():
                values = [r["rating"] for r in ratings]
                value = round(metric(values), 2)
                counter[value] += 1
            
            return dict(sorted(counter.items()))
        
        def top_controversial(self, n):
            scores = {}
            
            for uid, lst in self.parent.by_user.items():
                ratings = [r["rating"] for r in lst]
                mean = average(ratings)
                value = average([(x - mean) ** 2 for x in ratings])
                scores[uid] = round(value, 2)

            top_users = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

            return dict(top_users)
        def rating_bias(self):
            """
            Returns overall average user rating.
            """
            all_ratings = [r["rating"] for r in self.parent.ratings]
            return round(average(all_ratings), 2)
        
class Tags:
    """
    Analyzing data from tags.csv
    """
    def __init__(self, path_to_the_file):
        self.tags = []
        with open(path_to_the_file, "r") as f:
            try:
                header = f.readline().strip()
                if header != "userId,movieId,tag,timestamp":
                    raise Exception("wrong header")
            except Exception as e:
                print(f"error handled: {e}, u r dummy")

            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(",")
                    if len(parts) != 4:
                        raise Exception("wrong number of fields")
                    
                    user_s, movie_s, tag_s, ts_s = parts
                    user_id = int(user_s)
                    movie_id = int(movie_s)
                    tag = tag_s
                    timestamp = int(ts_s)

                    if timestamp <= 0:
                        raise ValueError("timestamp must be positive")
                    year = datetime.fromtimestamp(timestamp, tz=timezone.utc).year
                    record = {
                        "user": user_id,
                        "movie": movie_id,
                        "tag": tag,
                        "year": year,
                    }

                    self.tags.append(record)

                except Exception as e:
                    print(f"error handled: {e} for line: {line}")

    def most_words(self, n):
        """
        The method returns top-n tags with most words inside. It is a dict 
        where the keys are tags and the values are the number of words inside the tag.
        Drop the duplicates. Sort it by numbers descendingly.
        """
        unique_tags = set(record["tag"] for record in self.tags)
        counts = {}

        for tag in unique_tags:
            words = re.findall(r"\b\w+\b", tag)
            counts[tag] = len(words)
        
        top_big = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

        return dict(top_big)

    def longest(self, n):
        """
        The method returns top-n longest tags in terms of the number of characters.
        It is a list of the tags. Drop the duplicates. Sort it by numbers descendingly.
        """
        unique_tags = set(record["tag"] for record in self.tags)
        counts = {}

        for tag in unique_tags:
            counts[tag] = len(tag)
        
        top_big = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

        return dict(top_big)

    def most_words_and_longest(self, n):
        """
        The method returns the intersection between top-n tags with most words inside and 
        top-n longest tags in terms of the number of characters.
        Drop the duplicates. It is a list of the tags.
        """
        most_words = self.most_words(n)
        longest = self.longest(n)

        intersection = set(most_words.keys()) & set(longest.keys())

        return sorted(intersection, key=lambda t: (-most_words[t], -len(t)))
        
    def most_popular(self, n):
        """
        The method returns the most popular tags. 
        It is a dict where the keys are tags and the values are the counts.
        Drop the duplicates. Sort it by counts descendingly.
        """
        popular_tags = Counter()
        for record in self.tags:
            popular_tags[record["tag"]] += 1
        return dict(popular_tags.most_common(n))
        
    def tags_with(self, word):
        """
        The method returns all unique tags that include the word given as the argument.
        Drop the duplicates. It is a list of the tags. Sort it by tag names alphabetically.
        """
        word = word.lower()
        unique_tags = set(record["tag"] for record in self.tags)
        tags_with_word = []

        for tag in unique_tags:
            words = re.findall(r"\b\w+\b", tag.lower())
            if word in words:
                tags_with_word.append(tag)

        return sorted(tags_with_word)
    
    def tag_word_frequency(self, n):
        """
        Returns top-n most frequent words in tags.
        """
        counter = Counter()

        for r in self.tags:
            words = re.findall(r"\b\w+\b", r["tag"].lower())
            counter.update(words)

        return dict(counter.most_common(n))

class TestAnalytics:
    @classmethod
    def setup_class(cls):
        cls.ratings = Ratings("../datasets/ratings.csv")
        cls.tags = Tags("../datasets/tags.csv")

    # ===== Ratings.Movies =====

    def test_dist_by_year(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,4.0,946684800\n"
                "2,1,5.0,946684800\n"
                "1,2,3.0,978307200\n"
            )

        r = Ratings(file)
        res = r.movies.dist_by_year()
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        assert list(res.keys()) == sorted(res.keys())
        assert res == {2000: 2, 2001: 1}

    def test_dist_by_rating(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,4.0,946684800\n"
                "2,1,4.0,946684800\n"
                "3,1,5.0,946684800\n"
            )
        r = Ratings(file)
        res = r.movies.dist_by_rating()
        assert isinstance(res, dict)
        assert all(isinstance(k, float) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        assert list(res.keys()) == sorted(res.keys())
        assert res == {4.0: 2, 5.0: 1}

    def test_top_by_num_of_ratings(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,4.0,946684800\n"
                "2,1,5.0,946684800\n"
                "1,2,2.0,946684800\n"
                "2,1,2.0,946684800\n"
            )
        r = Ratings(file)
        res = r.movies.top_by_num_of_ratings(10)
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {
        1: 3.0,
        2: 1.0
        }

    def test_top_by_ratings(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,4.0,946684800\n"
                "2,1,5.0,946684800\n"
                "1,2,2.0,946684800\n"
                "2,2,2.0,946684800\n"
            )
        r = Ratings(file)
        res = r.movies.top_by_ratings(2)
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, float) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {1: 4.5, 2: 2.0}

    def test_top_controversial_movies(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,1.0,946684800\n"
                "2,1,5.0,946684800\n"
                "1,2,3.0,946684800\n"
                "2,2,3.0,946684800\n"
            )
        r = Ratings(file)
        res = r.movies.top_controversial(10)
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, float) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {1: 4.0, 2: 0.0}

    def test_most_polarized(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,2.0,946684800\n"
                "2,1,4.0,946684800\n"
                "1,2,3.0,946684800\n"
                "2,2,3.0,946684800\n"
            )
        r = Ratings(file)
        res = r.movies.most_polarized(2, min_votes=1)
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, float) for v in res.values())
        assert res == {1: 1.0, 2: 0.0}

    # ===== Ratings.Users =====

    def test_users_dist_by_num_of_ratings(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,4.0,946684800\n"
                "1,2,5.0,946684800\n"
                "2,1,3.0,946684800\n"
            )
        r = Ratings(file)
        res = r.users.dist_by_num_of_ratings()
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        assert list(res.keys()) == sorted(res.keys())
        assert res == {1: 1, 2: 1}

    def test_users_dist_by_ratings(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,2.0,946684800\n"
                "2,1,5.0,946684800\n"
                "1,2,3.0,946684800\n"
                "2,2,3.0,946684800\n"
            )
        r = Ratings(file)
        res = r.users.dist_by_ratings()
        assert isinstance(res, dict)
        assert all(isinstance(k, float) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        assert list(res.keys()) == sorted(res.keys())
        assert res == {4.0: 1, 2.5: 1}

    def test_users_top_controversial(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,1.0,946684800\n"
                "2,1,5.0,946684800\n"
                "1,2,3.0,946684800\n"
                "2,2,5.0,946684800\n"
            )
        r = Ratings(file)
        res = r.users.top_controversial(10)
        assert isinstance(res, dict)
        assert all(isinstance(k, int) for k in res.keys())
        assert all(isinstance(v, float) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {1: 1.0, 2: 0.0}

    def test_rating_bias(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,rating,timestamp\n"
                "1,1,4.0,946684800\n"
                "2,1,2.0,946684800\n"
            )
        r = Ratings(file)
        res = r.users.rating_bias()
        assert isinstance(res, float)
        assert 0.5 <= res <= 5.0
        assert res == 3.0

    # ===== Tags =====

    def test_most_words(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,tag,timestamp\n"
                "1,1,very good movie,946684800\n"
                "2,1,good movie,946684800\n"
            )
        t = Tags(file)
        res = t.most_words(2)
        assert isinstance(res, dict)
        assert all(isinstance(k, str) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {"very good movie": 3, "good movie": 2}

    def test_longest(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,tag,timestamp\n"
                "1,1,short,946684800\n"
                "2,1,very long tag,946684800\n"
                "2,2,smol,946684800\n"
            )
        t = Tags(file)
        res = t.longest(2)
        assert isinstance(res, dict)
        assert all(isinstance(k, str) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {"very long tag": len("very long tag"), "short": len("short")}

    def test_most_words_and_longest(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,tag,timestamp\n"
                "1,1,very good movie,946684800\n"
                "2,1,good movie,946684800\n"
                "3,1,boring,946684800\n"
            )
        t = Tags(file)
        res = t.most_words_and_longest(2)
        assert isinstance(res, list)
        assert all(isinstance(x, str) for x in res)
        assert res == ["very good movie", "good movie"]

    def test_most_popular(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,tag,timestamp\n"
                "1,1,good,946684800\n"
                "2,1,good,946684800\n"
                "3,1,bad,946684800\n"
            )
        t = Tags(file)
        res = t.most_popular(2)
        assert isinstance(res, dict)
        assert all(isinstance(k, str) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        values = list(res.values())
        assert values == sorted(values, reverse=True)
        assert res == {"good": 2,"bad": 1}

    def test_tags_with(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,tag,timestamp\n"
                "1,1,very good movie,946684800\n"
                "2,1,bad movie,946684800\n"
            )
        t = Tags(file)
        res = t.tags_with("good")
        assert isinstance(res, list)
        assert all(isinstance(x, str) for x in res)
        assert res == sorted(res)
        assert res == ["very good movie"]

    def test_tag_word_frequency(self, tmp_path):
        file = tmp_path / "ratings.csv"
        with open(file, "w") as f:
            f.write(
                "userId,movieId,tag,timestamp\n"
                "1,1,good movie,946684800\n"
                "2,1,good acting,946684800\n"
            )
        t = Tags(file)
        res = t.tag_word_frequency(2)
        assert isinstance(res, dict)
        assert all(isinstance(k, str) for k in res.keys())
        assert all(isinstance(v, int) for v in res.values())
        assert res == {"good": 2, "movie": 1}

class Links:
    """Analyzing data from links.csv with lazy loading and JSON caching"""

    def __init__(self, path_to_the_file, cache_file="imdb_cache.json"):
        self.movie_links = {}
        self._load_movie_links(path_to_the_file)

        self.cache_file = cache_file
        self.parsed_films = {}
        self._load_cache()

    def _load_movie_links(self, file_path):
        """Загружает соответствие movieId -> imdbId из файла"""
        try:
            with open(file_path, "r") as f:
                next(f)  # пропускает заголовок!!!!
                for line_num, line in enumerate(f, 2):
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split(",")
                    if len(parts) >= 2:
                        try:
                            movie_id = int(parts[0])
                            imdb_id = parts[1]
                            self.movie_links[movie_id] = imdb_id
                        except (ValueError, IndexError) as e:
                            print(f"Ошибка в строке {line_num}: {e} - {line}")
        except FileNotFoundError:
            print(f"Файл не найден: {file_path}")
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")

    def _load_cache(self):
        """Загружает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.parsed_films = json.load(f)
                print(f"Загружено {len(self.parsed_films)} фильмов из кэша")
        except Exception as e:
            print(f"Ошибка при загрузке кэша: {e}")
            self.parsed_films = {}

    def _save_cache(self):
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.parsed_films, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении кэша: {e}")

    def _parse_imdb(self, imdb_id):
        """Парсит данные с IMDb или возвращает из кэша"""
        if imdb_id in self.parsed_films:
            return self.parsed_films[imdb_id]

        # print(f"Парсим IMDb для tt{imdb_id}...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = f"https://www.imdb.com/title/tt{imdb_id}/"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к IMDb для tt{imdb_id}: {e}")
            return self._get_default_film_data(imdb_id)
        except Exception as e:
            print(f"Неожиданная ошибка при парсинге tt{imdb_id}: {e}")
            return self._get_default_film_data(imdb_id)

        film_data = self._extract_film_data(soup, imdb_id)
        self.parsed_films[imdb_id] = film_data
        self._save_cache()

        return film_data

    def _extract_film_data(self, soup, imdb_id):
        """Извлекает данные фильма из HTML"""
        data = {"imdb_id": imdb_id}

        title_elem = soup.find("span", class_="hero__primary-text")
        data["title"] = (
            title_elem.get_text(strip=True) if title_elem else f"Movie_{imdb_id}"
        )

        rating_elem = soup.find("span", class_="ipc-rating-star--rating")
        if rating_elem:
            try:
                data["rating"] = float(rating_elem.text)
            except ValueError:
                data["rating"] = "N/A"
        else:
            data["rating"] = "N/A"

        runtime_elem = soup.find(
            "ul",
            class_="ipc-inline-list ipc-inline-list--show-dividers sc-b41e510f-3 ggypaO baseAlt",
        )
        if runtime_elem:
            runtime_items = runtime_elem.find_all(class_="ipc-inline-list__item")
            if len(runtime_items) == 3:
                data["runtime"] = runtime_items[-1].text if runtime_items else "N/A"
            else:
                data["runtime"] = "N/A"
        else:
            data["runtime"] = "N/A"

        director_elem = soup.find(
            "a",
            class_="ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link",
        )
        data["director"] = director_elem.text if director_elem else "Unknown"

        budget_elem = soup.select_one('li[data-testid="title-boxoffice-budget"]')
        if budget_elem:
            value_span = budget_elem.find("span", class_="ipc-metadata-list-item__list-content-item")
            if value_span:
                budget_text = value_span.get_text(strip=True)

                data["budget"] = (budget_text.split("(")[0].strip() if budget_text else "N/A")
            else:
                data["budget"] = "N/A"
        else:
            data["budget"] = "N/A"

        
        gross_elem = soup.select_one('li[data-testid="title-boxoffice-cumulativeworldwidegross"]')
        if gross_elem:
            gross_value = gross_elem.find("span",class_="ipc-metadata-list-item__list-content-item ipc-btn--not-interactable",)
            data["gross"] = gross_value.get_text(strip=True) if gross_value else "N/A"
        else:
            data["gross"] = "N/A"

        return data

    def _get_default_film_data(self, imdb_id):
        """Возвращает данные по умолчанию при ошибке парсинга"""
        return {
            "imdb_id": imdb_id,
            "title": f"Movie_{imdb_id}",
            "rating": "N/A",
            "runtime": "N/A",
            "director": "Unknown",
            "budget": "N/A",
            "gross": "N/A",
        }

    def _parse_movies_lazy(self, movie_ids):
        """Ленивый парсинг: парсит только те фильмы, которых нет в кэше"""
        movies_to_parse = []
        for movie_id in movie_ids:
            imdb_id = self.movie_links.get(movie_id)
            if imdb_id and imdb_id not in self.parsed_films:
                movies_to_parse.append(imdb_id)

        if movies_to_parse:
            print(f"Парсим {len(movies_to_parse)} новых фильмов...")
            for imdb_id in movies_to_parse:
                try:
                    self._parse_imdb(imdb_id)
                except Exception as e:
                    print(f"Ошибка при парсинге tt{imdb_id}: {e}")

    @staticmethod
    def runtime_to_minutes(time_str):
        """Парсит строку с длительностью в минуты"""
        if not time_str or str(time_str).strip() in ["", "N/A"]:
            return 0

        time_str = str(time_str).strip().lower()
        minutes = 0

        # часы
        h_match = re.search(r"(\d+)\s*h", time_str)
        if h_match:
            minutes += int(h_match.group(1)) * 60

        # минуты
        m_match = re.search(r"(\d+)\s*m", time_str)
        if m_match:
            minutes += int(m_match.group(1))

        #  только число
        if minutes == 0:
            num_match = re.search(r"^(\d+)$", time_str)
            if num_match:
                minutes = int(num_match.group(1))

        return minutes

    def _parse_budget_to_number(self, budget_str):
        """Преобразует строку бюджета в числовой формат"""
        if not budget_str or budget_str.strip().lower() in ["n/a", "unknown", ""]:
            return 0

        s = budget_str.lower().replace(",", "").strip()
        match = re.search(r"\d+(\.\d+)?", s)


        if not match:
            return 0

        number = float(match.group())
        if '¥' in s:
            number = (number)*0.006322
        elif 'RUB' in s:
            number = (number)*0.012848
        elif 'CNY' in s:
            number = (number)*0.1435

        return int(number)

    def get_imdb(self, list_of_movies, list_of_fields, force_update=False):
        """
        Returns a list of lists [movieId, field1, field2, ...] for given movies.
        Sort by movieId descending.
        """
        if not list_of_movies or not list_of_fields:
            return []

        if force_update:
            self._parse_movies_lazy(list_of_movies)

        sorted_movies = sorted(list_of_movies, reverse=True)
        result = []

        for movie_id in sorted_movies:
            imdb_id = self.movie_links.get(movie_id)
            if not imdb_id:
                continue

            film_data = self.parsed_films.get(imdb_id)
            if not film_data:
                continue

            row = [movie_id]
            for field in list_of_fields:
                row.append(film_data.get(field, "N/A"))
            result.append(row)

        return result

    def force_update_all(self):
        for f in self.movie_links.values():
            self._parse_imdb(f)

    def find_all_highest_rated_movies(self, force_update=False):
        """
        Находит все фильмы с максимальным рейтингом (если их несколько)
        Возвращает список фильмов
        """
        movies = []
        highest_rating = -1

        if force_update:
            self._update_all_movies()

        for film_data in self.parsed_films.values():
            try:
                rating = float(film_data.get("rating"))
                if rating > highest_rating:
                    highest_rating = rating
            except (ValueError, TypeError):
                continue

        for film_data in self.parsed_films.values():
            try:
                rating = float(film_data.get("rating"))
                if rating == highest_rating:
                    movies.append(film_data)
            except (ValueError, TypeError):
                continue

        return movies, highest_rating

    def ratings(self, force_update=False):
        ratings = []

        if force_update:
            self._update_all_movies()
        for film_data in self.parsed_films.values():
            try:
                rate = float(film_data.get("rating"))
            except:
                continue
            ratings.append(rate)
        return ratings

    def top_directors(self, n, force_update=False):
        """Returns top-n directors by movie count"""
        if n <= 0:
            return {}

        if force_update:
            self._update_all_movies()

        directors = []
        for film_data in self.parsed_films.values():
            director = film_data.get("director", "").strip()
            if director and director not in ["Unknown", "N/A"]:
                directors.append(director)

        if not directors:
            return {}

        return dict(Counter(directors).most_common(n))

    def _update_all_movies(self):
        """Парсит все фильмы из movie_links"""
        print("Парсим все фильмы...")
        for imdb_id in self.movie_links.values():
            if imdb_id not in self.parsed_films:
                try:
                    self._parse_imdb(imdb_id)
                except Exception as e:
                    print(f"Ошибка при парсинге tt{imdb_id}: {e}")

    def most_expensive(self, n, force_update=False):
        """Returns top-n movies by budget"""
        if n <= 0 or not self.parsed_films:
            return {}

        if force_update:
            self._update_all_movies()

        movies_with_budgets = []
        for imdb_id, film_data in self.parsed_films.items():
            title = film_data.get("title", f"Movie_{imdb_id}")
            budget_str = film_data.get("budget", "0")
            budget_value = self._parse_budget_to_number(budget_str)
            movies_with_budgets.append((title, budget_value))

        if not movies_with_budgets:
            return {}

        movies_with_budgets.sort(key=lambda x: x[1], reverse=True)
        return dict(movies_with_budgets[:n])

    def most_profitable(self, n, force_update=False):
        """Returns top-n movies by profit (gross - budget)"""
        if n <= 0 or not self.parsed_films:
            return {}

        if force_update:
            self._update_all_movies()

        movies_with_profit = []
        for imdb_id, film_data in self.parsed_films.items():
            title = film_data.get("title", f"Movie_{imdb_id}")
            budget = self._parse_budget_to_number(film_data.get("budget", "0"))
            gross = self._parse_budget_to_number(film_data.get("gross", "0"))
            profit = gross - budget
            movies_with_profit.append((title, profit))

        if not movies_with_profit:
            return {}

        movies_with_profit.sort(key=lambda x: x[1], reverse=True)
        return dict(movies_with_profit[:n])

    def longest(self, n, force_update=False):
        """Returns top-n movies by runtime"""
        if n <= 0 or not self.parsed_films:
            return {}

        if force_update:
            self._update_all_movies()

        movies_with_runtime = []
        for imdb_id, film_data in self.parsed_films.items():
            title = film_data.get("title", f"Movie_{imdb_id}")
            runtime_str = film_data.get("runtime", "0")
            runtime_minutes = self.runtime_to_minutes(runtime_str)
            movies_with_runtime.append((title, runtime_minutes))

        if not movies_with_runtime:
            return {}

        movies_with_runtime.sort(key=lambda x: x[1], reverse=True)
        return dict(movies_with_runtime[:n])

    def top_cost_per_minute(self, n, force_update=False):
        """Returns top-n movies by budget per minute"""
        if n <= 0 or not self.parsed_films:
            return {}

        if force_update:
            self._update_all_movies()

        movies_with_cost = []
        for imdb_id, film_data in self.parsed_films.items():
            title = film_data.get("title", f"Movie_{imdb_id}")
            budget = self._parse_budget_to_number(film_data.get("budget", "0"))
            runtime_minutes = self.runtime_to_minutes(film_data.get("runtime", "0"))

            cost_per_minute = (
                round(budget / runtime_minutes, 2) if runtime_minutes > 0 else 0
            )
            movies_with_cost.append((title, cost_per_minute))

        if not movies_with_cost:
            return {}

        movies_with_cost.sort(key=lambda x: x[1], reverse=True)
        return dict(movies_with_cost[:n])

    def clear_cache(self):
        """Очищает кэш"""
        self.parsed_films = {}
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("Кэш очищен")
        except Exception as e:
            print(f"Ошибка при удалении файла кэша: {e}")

    def get_cache_stats(self):
        """Возвращает статистику кэша"""
        return {
            "total_films": len(self.parsed_films),
            "cache_file": self.cache_file,
            "total_movies_in_links": len(self.movie_links),
        }


class Movies:
    def __init__(self, path_to_the_file):
        self.data = []
        with open(path_to_the_file, "r", encoding="utf-8") as f:
            f.readline()  # пропускает заголовок
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # разделитель между названием и жанрами
                last_comma = line.rfind(",")
                if last_comma != -1:
                    movie_id_end = line.find(",")
                    movie_id = line[:movie_id_end]
                    title = line[movie_id_end + 1 : last_comma].strip('" ')
                    genres = line[last_comma + 1 :].strip()

                    self.data.append(
                        {"movieId": movie_id, "title": title, "genres": genres}
                    )

    def dist_by_release(self):
        """
        The method returns a dict or an OrderedDict where the keys are years and the values are counts.
        You need to extract years from the titles. Sort it by counts descendingly.
        """

        # год в формате (1994), (2001), (1999-2000)
        year_pattern = r"\((\d{4})(?:\s*[-–]\s*\d{4})?\)"

        years = []
        for row in self.data:
            title = row.get("title", "")

            # год в названии
            match = re.search(year_pattern, title)
            if match:
                # первый год, если указан диапазон
                year = match.group(1)
                years.append(year)

        #  количество фильмов по годам
        year_counts = Counter(years)

        # по количеству фильмов в убывающем порядке
        sorted_years = sorted(year_counts.items(), key=lambda x: x[1], reverse=True)

        return OrderedDict(sorted_years)

    def dist_by_genres(self):
        all_genres = []
        for row in self.data:
            genres = row.get("genres", "")
            if genres and genres != "(no genres listed)":
                genres_list = genres.split("|")
                all_genres.extend(genres_list)

        genre_counts = Counter(all_genres)
        return OrderedDict(
            sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        )

    def most_genres(self, n):
        movies_with_counts = []

        for row in self.data:
            title = row.get("title", "")
            genres = row.get("genres", "")

            if not genres or genres.strip() == "" or genres == "(no genres listed)":
                genre_count = 0
            else:
                genres_list = [g.strip() for g in genres.split("|") if g.strip()]
                genre_count = len(genres_list)

            movies_with_counts.append((title, genre_count))

        movies_with_counts.sort(key=lambda x: x[1], reverse=True)

        top_n = (
            movies_with_counts[:n]
            if n <= len(movies_with_counts) and n > 0
            else movies_with_counts
        )

        return OrderedDict(top_n)

class TestLinks:
    """Test suite for Links class - проверяем только требования из задания"""

    @pytest.fixture
    def setup_test_file(self, tmp_path):
        """Создаем тестовый CSV файл"""
        test_data = """movieId,imdbId,tmdbId
1,114709,862
2,113497,8844
3,113228,15602
4,114885,31357
5,113041,11862"""

        file_path = tmp_path / "test_links.csv"
        file_path.write_text(test_data)
        return str(file_path)

    @pytest.fixture
    def links_instance(self, setup_test_file, tmp_path):
        """Создаем экземпляр Links с тестовыми данными"""
        cache_file = tmp_path / "test_cache.json"
        return Links(setup_test_file, str(cache_file))

    @pytest.fixture
    def mock_imdb_data(self):
        """Тестовые данные для имитации парсинга IMDb"""
        return {
            "114709": {
                "imdb_id": "114709",
                "title": "Toy Story (1995)",
                "rating": 8.3,
                "runtime": "81 min",
                "director": "John Lasseter",
                "budget": "$30,000,000",
                "gross": "$373,554,033",
            },
            "113497": {
                "imdb_id": "113497",
                "title": "Jumanji (1995)",
                "rating": 6.9,
                "runtime": "104 min",
                "director": "Joe Johnston",
                "budget": "$65,000,000",
                "gross": "$262,797,249",
            },
            "113228": {
                "imdb_id": "113228",
                "title": "Grumpier Old Men (1995)",
                "rating": 6.6,
                "runtime": "101 min",
                "director": "Howard Deutch",
                "budget": "$25,000,000",
                "gross": "$71,000,000",
            },
        }

    # ТЕСТ 1: Проверка get_imdb
    @patch("requests.get")
    def test_get_imdb_return_type_and_sort(
        self, mock_get, links_instance, mock_imdb_data
    ):
        """
        Проверяем что get_imdb возвращает правильный тип данных
        и данные отсортированы по movieId в убывающем порядке
        """
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Мокаем парсинг, чтобы возвращать тестовые данные
        original_parsing = links_instance._parse_imdb

        def mock_parsing(imdb_id):
            return mock_imdb_data.get(
                imdb_id,
                {
                    "imdb_id": imdb_id,
                    "title": f"Movie {imdb_id}",
                    "rating": 0.0,
                    "runtime": "0 min",
                    "director": "Unknown",
                    "budget": "$0",
                    "gross": "$0",
                },
            )

        links_instance._parsing_imdb = Mock(side_effect=mock_parsing)

        # Тестируемые параметры
        movie_ids = [1, 3, 2]  # Не в порядке
        fields = ["title", "director", "rating"]

        result = links_instance.get_imdb(movie_ids, fields)

        # 1. Проверяем тип возвращаемых данных
        assert isinstance(result, list), (
            f"Метод должен возвращать list, получен {type(result)}"
        )


        # Проверяем типы элементов в списках
        for field_list in result:
            assert isinstance(field_list, list), (
                f"Элементы должны быть списками, получен {type(field_list)}"
            )

            for value in field_list:
                # Проверяем тип в зависимости от поля
                if field_list is result[0]:  # title
                    assert isinstance(value, str), (
                        f"Название должно быть строкой, получен {type(value)}"
                    )
                elif field_list is result[1]:  # director
                    assert isinstance(value, str), (
                        f"Режиссер должен быть строкой, получен {type(value)}"
                    )
                elif field_list is result[2]:  # rating
                    # rating может быть float или строкой "N/A"
                    assert isinstance(value, (float, int, str)), (
                        f"Рейтинг должен быть числом или строкой, получен {type(value)}"
                    )

        # Восстанавливаем оригинальный метод
        links_instance._parsing_imdb = original_parsing

    # ТЕСТ 2: Проверка top_directors
    @patch("requests.get")
    def test_top_directors_return_type_and_sort(
        self, mock_get, links_instance, mock_imdb_data
    ):
        """
        Проверяем что top_directors возвращает правильный тип данных
        и данные отсортированы по количеству фильмов в убывающем порядке
        """
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Заполняем кэш тестовыми данными
        links_instance.parsed_films = mock_imdb_data.copy()

        n = 2
        result = links_instance.top_directors(n)

        # 1. Проверяем тип возвращаемых данных
        assert isinstance(result, dict), (
            f"Метод должен возвращать dict, получен {type(result)}"
        )

        # 2. Проверяем тип ключей (режиссеры)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        # 3. Проверяем тип значений (количество фильмов)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        # 4. Проверяем что данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию количества фильмов"
        )

        # 5. Проверяем что возвращается правильное количество элементов
        assert len(result) == min(n, len(mock_imdb_data)), (
            f"Должно вернуться {min(n, len(mock_imdb_data))} элементов, получено {len(result)}"
        )

    # ТЕСТ 3: Проверка most_expensive
    @patch("requests.get")
    def test_most_expensive_return_type_and_sort(
        self, mock_get, links_instance, mock_imdb_data
    ):
        """
        Проверяем что most_expensive возвращает правильный тип данных
        и данные отсортированы по бюджету в убывающем порядке
        """
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Заполняем кэш тестовыми данными
        links_instance.parsed_films = mock_imdb_data.copy()

        n = 2
        result = links_instance.most_expensive(n)

        # 1. Проверяем тип возвращаемых данных
        assert isinstance(result, dict), (
            f"Метод должен возвращать dict, получен {type(result)}"
        )

        # 2. Проверяем тип ключей (названия фильмов)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        # 3. Проверяем тип значений (бюджеты)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        # 4. Проверяем что данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию бюджета"
        )

    # ТЕСТ 4: Проверка most_profitable
    @patch("requests.get")
    def test_most_profitable_return_type_and_sort(
        self, mock_get, links_instance, mock_imdb_data
    ):
        """
        Проверяем что most_profitable возвращает правильный тип данных
        и данные отсортированы по прибыли в убывающем порядке
        """
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Заполняем кэш тестовыми данными
        links_instance.parsed_films = mock_imdb_data.copy()

        n = 2
        result = links_instance.most_profitable(n)

        # 1. Проверяем тип возвращаемых данных
        assert isinstance(result, dict), (
            f"Метод должен возвращать dict, получен {type(result)}"
        )

        # 2. Проверяем тип ключей (названия фильмов)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        # 3. Проверяем тип значений (прибыль)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        # 4. Проверяем что данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию прибыли"
        )

    # ТЕСТ 5: Проверка longest
    @patch("requests.get")
    def test_longest_return_type_and_sort(
        self, mock_get, links_instance, mock_imdb_data
    ):
        """
        Проверяем что longest возвращает правильный тип данных
        и данные отсортированы по длительности в убывающем порядке
        """
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Заполняем кэш тестовыми данными
        links_instance.parsed_films = mock_imdb_data.copy()

        n = 2
        result = links_instance.longest(n)

        # 1. Проверяем тип возвращаемых данных
        assert isinstance(result, dict), (
            f"Метод должен возвращать dict, получен {type(result)}"
        )

        # 2. Проверяем тип ключей (названия фильмов)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        # 3. Проверяем тип значений (длительность в минутах)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        # 4. Проверяем что данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию длительности"
        )

    # ТЕСТ 6: Проверка top_cost_per_minute
    @patch("requests.get")
    def test_top_cost_per_minute_return_type_and_sort(
        self, mock_get, links_instance, mock_imdb_data
    ):
        """
        Проверяем что top_cost_per_minute возвращает правильный тип данных
        и данные отсортированы по стоимости за минуту в убывающем порядке
        """
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Заполняем кэш тестовыми данными
        links_instance.parsed_films = mock_imdb_data.copy()

        n = 2
        result = links_instance.top_cost_per_minute(n)

        # 1. Проверяем тип возвращаемых данных
        assert isinstance(result, dict), (
            f"Метод должен возвращать dict, получен {type(result)}"
        )

        # 2. Проверяем тип ключей (названия фильмов)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        # 3. Проверяем тип значений (стоимость за минуту)
        for value in result.values():
            assert isinstance(value, float), (
                f"Значения должны быть float, получен {type(value)}"
            )
            # Проверяем округление до 2 знаков
            assert len(str(value).split(".")[1]) <= 2, (
                f"Значение {value} должно быть округлено до 2 знаков"
            )

        # 4. Проверяем что данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию стоимости за минуту"
        )

    # ТЕСТ 7: Проверка вспомогательных методов
    def test_runtime_to_minutes(self, links_instance):
        """Проверяем преобразование времени в минуты"""
        test_cases = [
            ("81 min", 81),
            ("2 h 21 min", 141),  # 2*60 + 21
            ("2h 21m", 141),
            ("", 0),
            ("N/A", 0),
            ("120", 120),  # только число
        ]

        for time_str, expected in test_cases:
            result = links_instance.runtime_to_minutes(time_str)
            assert isinstance(result, int), (
                f"Результат должен быть int, получен {type(result)}"
            )
            assert result == expected, (
                f"Для '{time_str}' ожидалось {expected}, получено {result}"
            )

    def test_parse_budget_to_number(self, links_instance):
        """Проверяем преобразование бюджета в число"""
        test_cases = [
            ("$30,000,000", 30000000),
            ("$65 million", 65000000),
            ("$25M", 25000000),
            ("$1.5 billion", 1500000000),
            ("N/A", 0),
            ("", 0),
            ("unknown", 0),
        ]

        for budget_str, expected in test_cases:
            result = links_instance._parse_budget_to_number(budget_str)
            assert isinstance(result, int), (
                f"Результат должен быть int, получен {type(result)}"
            )
            assert result == expected, (
                f"Для '{budget_str}' ожидалось {expected}, получено {result}"
            )

    # ТЕСТ 8: Проверка граничных случаев
    @patch("requests.get")
    def test_edge_cases(self, mock_get, links_instance, mock_imdb_data):
        """Проверяем граничные случаи"""
        # Мокаем запрос к IMDb
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response

        # Заполняем кэш тестовыми данными
        links_instance.parsed_films = mock_imdb_data.copy()

        # n = 0 или отрицательное
        result = links_instance.top_directors(0)
        assert result == {}, "При n=0 должен возвращаться пустой словарь"

        result = links_instance.most_expensive(-1)
        assert result == {}, "При отрицательном n должен возвращаться пустой словарь"

        # n больше количества данных
        result = links_instance.longest(100)
        assert len(result) == len(mock_imdb_data), (
            f"При n > количества данных должен возвращаться весь список, получено {len(result)} элементов"
        )

        # Пустые списки для get_imdb
        result = links_instance.get_imdb([], ["title", "director"])
        assert result == [], (
            "При пустом списке movieId должен возвращаться пустой список"
        )

class TestMovies:
    """Test suite for Movies class - проверяем только требования из задания"""

    @pytest.fixture
    def setup_test_file(self, tmp_path):
        """Создаем тестовый CSV файл"""
        test_data = """movieId,title,genres
1,Toy Story (1995),Adventure|Animation|Children|Comedy|Fantasy
2,Jumanji (1995),Adventure|Children|Fantasy
3,Grumpier Old Men (1995),Comedy|Romance
4,Waiting to Exhale (1995),Comedy|Drama|Romance
5,Father of the Bride Part II (1995),Comedy
6,Heat (1995),Action|Crime|Thriller
7,No Year Movie,Action|Comedy
8,Another No Year,(no genres listed)"""

        file_path = tmp_path / "test_movies.csv"
        file_path.write_text(test_data)
        return str(file_path)

    @pytest.fixture
    def movies_instance(self, setup_test_file):
        """Создаем экземпляр Movies с тестовыми данными"""
        return Movies(setup_test_file)

    # ТЕСТ 1: Проверка dist_by_release
    def test_dist_by_release_return_type_and_sort(self, movies_instance):
        """
        Проверяем что метод возвращает правильный тип данных
        и данные отсортированы по убыванию
        """
        result = movies_instance.dist_by_release()

        # тип возвращаемых данных
        assert isinstance(result, OrderedDict), (
            f"Метод должен возвращать OrderedDict, получен {type(result)}"
        )

        # тип ключей (годы)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        # тип значений (количество)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        # данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию количества"
        )

    # ТЕСТ 2: Проверка dist_by_genres
    def test_dist_by_genres_return_type_and_sort(self, movies_instance):
        """
        Проверяем что метод возвращает правильный тип данных
        и данные отсортированы по убыванию
        """
        result = movies_instance.dist_by_genres()

        #  тип возвращаемых данных
        assert isinstance(result, OrderedDict), (
            f"Метод должен возвращать OrderedDict, получен {type(result)}"
        )

        #  тип ключей (жанры)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )
            assert key != "(no genres listed)", (
                "Не должно быть '(no genres listed)' в результатах"
            )

        # тип значений (количество)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        #  данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию количества"
        )

        #  значения из тестовых данных
        assert result["Comedy"] == 5
        assert result["Adventure"] == 2

    # ТЕСТ 3: Проверка most_genres
    def test_most_genres_return_type_and_sort(self, movies_instance):
        """
        Проверяем что метод возвращает правильный тип данных
        и данные отсортированы по убыванию
        """
        n = 3  # для top-3
        result = movies_instance.most_genres(n)

        #  тип возвращаемых данных
        assert isinstance(result, OrderedDict), (
            f"Метод должен возвращать OrderedDict, получен {type(result)}"
        )

        # тип ключей (названия фильмов)
        for key in result.keys():
            assert isinstance(key, str), (
                f"Ключи должны быть строками, получен {type(key)}"
            )

        #  тип значений (количество жанров)
        for value in result.values():
            assert isinstance(value, int), (
                f"Значения должны быть целыми числами, получен {type(value)}"
            )

        # данные отсортированы по убыванию
        values = list(result.values())
        assert values == sorted(values, reverse=True), (
            "Данные должны быть отсортированы по убыванию количества жанров"
        )

        # о возвращается правильное количество фильмов
        assert len(result) == min(n, len(movies_instance.data)), (
            f"Должно вернуться {min(n, len(movies_instance.data))} фильмов, получено {len(result)}"
        )

        #  конкретные значения
        # Toy Story (1995) имеет 5 жанров, должен быть первым
        first_movie = list(result.keys())[0]
        assert "Toy Story" in first_movie
        assert result[first_movie] == 5

    # ТЕСТ 4: Проверка граничных случаев для most_genres
    def test_most_genres_edge_cases(self, movies_instance):
        """Проверяем граничные случаи для most_genres"""

        # Тест с n=0 (должен вернуть все фильмы)
        result_all = movies_instance.most_genres(0)
        assert isinstance(result_all, OrderedDict)
        assert len(result_all) == len(movies_instance.data)

        # Тест с n больше чем количество фильмов
        result_large_n = movies_instance.most_genres(100)
        assert len(result_large_n) == len(movies_instance.data)

        # Тест с n=1
        result_one = movies_instance.most_genres(1)
        assert len(result_one) == 1

        #  значения отсортированы
        values = list(result_one.values())
        assert values == sorted(values, reverse=True)

    # ТЕСТ 5: Проверка что методы работают с фильмами без года
    def test_movies_without_year(self, movies_instance):
        """Проверяем обработку фильмов без года в названии"""
        result = movies_instance.dist_by_release()

        #  только фильмы с годом (6 из 8 тестовых фильмов)
        assert "1995" in result
        assert result["1995"] == 6  # 6 фильмов с 1995 годом

    # ТЕСТ 6: Проверка что методы работают с фильмами без жанров
    def test_movies_without_genres(self, movies_instance):
        """Проверяем обработку фильмов без жанров"""
        result = movies_instance.dist_by_genres()

        # '(no genres listed)' не должно быть в результатах
        assert "(no genres listed)" not in result

        # Проверяем most_genres для фильма без жанров
        all_movies = movies_instance.most_genres(0)

        # Находим фильм без жанров
        for title, count in all_movies.items():
            if "Another No Year" in title:
                assert count == 0, f"Фильм без жанров должен иметь 0, получено {count}"
                break


def main():
    ratings = Ratings("../datasets/ratings.csv")
    years = ratings.movies.dist_by_year()
    ratings_dist = ratings.movies.dist_by_rating()
    top = ratings.movies.top_by_num_of_ratings(5)
    top_average = ratings.movies.top_by_ratings(100)
    top_controversial = ratings.movies.top_controversial(10)

    dist_by_num = ratings.users.dist_by_num_of_ratings()
    dist_by_ratings = ratings.users.dist_by_ratings()
    user_top_controversial = ratings.users.top_controversial(10)

    print(user_top_controversial)

    links = Links(
        "../datasets/links.csv",
        cache_file="imdb_cache.json",
    )

    print("\nСтатистика кэша:")
    stats = links.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # первые 10 movieId для демонстрации
    sample_movie_ids = list(links.movie_links.keys())[:100]

    print(f"\nЗапрашиваем данные для {len(sample_movie_ids)} фильмов...")

    fields = ["title", "director", "budget", "gross", "runtime", "rating"]

    # парсить только те фильмы, которых нет в кэше
    result = links.get_imdb(sample_movie_ids, fields)

    print("\n" + "=" * 50)
    print("Демонстрация методов (используют кэшированные данные):")
    print("=" * 50)

    print("\nТоп 5 режиссеров:")
    print(links.top_directors(5))

    print("\nСамые дорогие фильмы (топ 5):")
    print(links.most_expensive(5))

    print("\nСамые прибыльные фильмы (топ 5):")
    print(links.most_profitable(5))

    print("\nСамые долгие фильмы (топ 5):")
    print(links.longest(5))

    print("\nСамые дорогие фильмы в расчете на минуту (топ 5):")
    print(links.top_cost_per_minute(5))

    print("\n" + "=" * 50)
    print("Финальная статистика кэша:")
    print("=" * 50)
    stats = links.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
