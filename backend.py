import pandas as pd
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import streamlit as st

def load_file_to_sqlite(files):
    if files[0].name.endswith(".csv"):
        df = pd.read_csv(files[0])
    else:
        df = pd.read_excel(files[0])
    
    conn = sqlite3.connect(":memory:",check_same_thread=False)
    df.to_sql("target", conn, index=False, if_exists="replace")
    return df, conn

def multi_load_file_to_sqlite(files, join_instructions):
    dfs = []
    for f in files:
        f.seek(0)
        if f.name.endswith(".csv"):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)
        dfs.append(df)

    # Start with first DataFrame
    merged_df = dfs[0]

    # Apply joins sequentially
    for (left_idx, left_col, right_idx, right_col, how) in join_instructions:
        merged_df = pd.merge(
            merged_df,
            dfs[right_idx],
            left_on=left_col,
            right_on=right_col,
            how=how
        )

    conn = sqlite3.connect(":memory:",check_same_thread=False)
    merged_df.to_sql("target", conn, index=False, if_exists="replace")
    return merged_df, conn, "target"

def get_sql_chain(api_key):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)

    prompt = PromptTemplate(
        input_variables=["question", "columns"],
        template="""
You are a data analyst. Convert the following question into a SQL query.
Table name: target
Columns: {columns}
Question: {question}
⚠️ IMPORTANT: Output only the raw SQL query. 
Do not include markdown, code fences, the word 'sql', or any explanation.
"""
    )

    # LCEL Chain
    chain = prompt | llm | StrOutputParser()
    return chain


def execute_sql_query(conn, query):
    try:
        result_df = pd.read_sql_query(query, conn)
        return result_df, None
    except Exception as e:
        return None, str(e)
