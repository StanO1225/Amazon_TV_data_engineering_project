
import pandas as pd
import numpy as np
from math import floor
from functools import reduce

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(amazon_titles, *args, **kwargs):
    """
    Template code for a transformer block.

    Add more parameters to this function if this block has multiple parent blocks.
    There should be one parameter for each output variable from each parent block.

    Args:
        data: The output from the upstream parent block
        args: The output from any additional upstream blocks (if applicable)

    Returns:
        Anything (e.g. data frame, dictionary, array, int, str, etc.)
    """
    # Specify your transformation logic here

    amazon_titles.rename({'id' : 'film_id'}, axis = 1, inplace=True)

    #imdb id uneccesary, age certification too many nulls
    amazon_titles.drop(columns=["imdb_id", "age_certification"], inplace=True)

    #Replacing nulls in seasons col with 0s if it is a movie
    movie_mask = (amazon_titles['type'] == 'MOVIE')
    amazon_titles.loc[movie_mask, 'seasons'] = 0

    # If no production countries then NA
    country_mask = (amazon_titles['production_countries'] == '[]')
    amazon_titles.loc[country_mask, 'production_countries'] = np.nan

        #Drop other rows with nulls
    # amazon_titles.dropna(inplace=True)


    # Create tmdb_imdb_dim 

    tmdb_imdb_dim = amazon_titles[['imdb_score', 'imdb_votes', 'tmdb_popularity', 'tmdb_score']].drop_duplicates()
    tmdb_imdb_dim.reset_index(inplace=True)
    tmdb_imdb_dim['imdb_tmdb_id'] = tmdb_imdb_dim.index
    tmdb_imdb_dim.drop(columns='index', inplace=True)

    tmdb_imdb_dim['imdb_diff_tmdb'] = tmdb_imdb_dim['imdb_score'] - tmdb_imdb_dim['tmdb_score']
    tmdb_imdb_dim['score_sum'] = tmdb_imdb_dim['imdb_score'] + tmdb_imdb_dim['tmdb_score']

    # Create year_dim
    year_dim = amazon_titles['release_year'].drop_duplicates()
    year_dim = year_dim.reset_index()
    year_dim['year_id'] = year_dim.index
    year_dim.drop(columns='index', inplace=True)

    year_dim.describe()

    def get_decade(yr):
        return f"{floor(yr/10)*10}s"

    year_dim['decade'] = year_dim['release_year'].apply(lambda x : get_decade(x))

    def string_to_set(cats):
        cats = cats.replace("[", '')
        cats = cats.replace("]", '')
        cats = cats.replace("'", '')
        cats = cats.replace(',', '')
        cats_list = cats.split()
        cats_set = set(cats_list)
        return cats_set

    genre_copy = amazon_titles["genres"].apply(string_to_set)

    all_genres = reduce(lambda x, y: x.union(y), genre_copy)

    #Create genre_dim

    genre_dim = amazon_titles['genres'].drop_duplicates()
    genre_dim = genre_dim.reset_index()
    genre_dim['genre_id'] = genre_dim.index
    genre_dim.drop(columns='index', inplace=True)

    for genre in all_genres:
        genre_dim[genre] = genre_dim['genres'].apply(lambda x: int(genre in x))
    genre_dim['num_genres'] = genre_dim['genres'].apply(lambda x: len(x.split(',')))

    # Creating fact table
    fact_table = amazon_titles.copy()

    fact_table = pd.merge(fact_table, year_dim, on = 'release_year')
    fact_table = pd.merge(fact_table, genre_dim, on = 'genres', how = 'left')
    fact_table = pd.merge(fact_table, tmdb_imdb_dim, on = ['imdb_score', 'imdb_votes', 'tmdb_popularity', 'tmdb_score'], how='inner')

    fact_table.drop(fact_table.columns.difference(['film_id', 'year_id', 'imdb_tmdb_id', 'genre_id', 'title', 'type', 'description', 'seasons', 'production_countries']), axis=1, inplace=True)

    return {'tmdb_imdb_dim': tmdb_imdb_dim.to_dict(orient = 'dict'), 
            'year_dim': year_dim.to_dict(orient='dict'),
            'genre_dim': genre_dim.to_dict(orient='dict'),
            'fact_table': fact_table.to_dict(orient='dict')}
            
@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
