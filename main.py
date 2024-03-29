import streamlit as st
import pymongo

import pandas as pd
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import numpy as np

# Initialize connection.
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["host"])

# Pull data from the collection.
@st.cache_data(ttl=600)
def get_data() -> pd.DataFrame:
    """
    Pull data from MongoDB Atlas

    Returns:
        pd.DataFrame: cleaned dataframe on specific collection
    """
    client = init_connection()
    db = client.sample_analytics
    df = db.customers.find(
        ).sort({
            "_id":1
        }).limit(
            50
        )

    df = pd.DataFrame(df)
    
    # Data cleaning
    df = df.drop(columns=[
        '_id',
        'accounts',
        'tier_and_details',
        'active'
    ])

    return df

# UI Filter widget
def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()
    
    # Convert date type data to standard format
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col], format="%d/%m/%Y")
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            left.write("↳")
            
            # Treat columns with < 10 unique values as categorical
            if isinstance(df[column], pd.CategoricalDtype) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    _min,
                    _max,
                    (_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].str.contains(user_text_input)]

    return df


    
def load_view():
    data = get_data()
    
    # UI Display
    st.title("My MongoCustomers")
    st.write(
            """Explore your MongoDB Atlas data through Streamlit with MUG@KL #2 Meetup
            """
        )
    st.dataframe(filter_dataframe(data), hide_index=True)


load_view()