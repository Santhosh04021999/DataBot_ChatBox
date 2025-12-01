import streamlit as st
import pandas as pd
from backend import load_file_to_sqlite,get_sql_chain,execute_sql_query,multi_load_file_to_sqlite

st.title("📁 Ask Your File Bot")

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "sql_history" not in st.session_state:
    st.session_state.sql_history = []
if "df" not in st.session_state:
    st.session_state.df = None
if "conn" not in st.session_state:
    st.session_state.conn = None

def llm(user_input,conn,df):
    if user_input:
        schema = ", ".join(df.columns)
        key='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'
        sql_chain = get_sql_chain(key)
        sql_query = sql_chain.invoke({"question": user_input, "columns": schema}).strip()

        result_df, error = execute_sql_query(conn, sql_query)
        # st.write(result_df)

        st.session_state.chat_history.append((user_input, sql_query, result_df if error is None else error))

        if st.session_state.chat_history:
            if st.button("Clear History"):
                st.session_state.chat_history = []
            for q, sql, result in reversed(st.session_state.chat_history):
                st.markdown(f"**You:** {q}")
                st.markdown(f"**Bot (SQL):** `{sql}`")
                if isinstance(result, str):
                    st.error(result)
                else:
                    st.dataframe(result)

    st.subheader("Custom Query:")
    custom_sql = st.text_area("Enter SQL query")

    if st.button("Run SQL") and custom_sql.strip():
        result_df, error = execute_sql_query(conn, custom_sql.strip())
        st.session_state.sql_history.append((user_input,custom_sql, result_df if error is None else error))

        if st.session_state.sql_history:
            st.subheader("SQL History")
            if st.button("Clear_SQL_History"):
                st.session_state.sql_history = []
            for q, sql, result in reversed(st.session_state.sql_history):
                st.markdown(f"**You:** {q}")
                st.markdown(f"**Bot (SQL):** `{sql}`")
                if isinstance(result, str):
                    st.error(result)
                else:
                    st.dataframe(result)


# Upload
files = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"],accept_multiple_files=True)
user_input=None
if len(files)==1:
    df, conn = load_file_to_sqlite(files)
    st.session_state.conn=conn
    st.session_state.df=df
    st.success("File loaded into SQLite!")

    st.subheader("Preview:")
    st.dataframe(df.head())

    st.subheader("Detected Columns:")
    st.write(df.dtypes)

    st.subheader("Ask a question:")
    user_input = st.text_input("Your question")
    llm(user_input,conn,df)

if files and len(files) > 1:
    st.subheader("Define Joins Between Files")
    file_order = st.multiselect("Select the order of files to join",
        options=[f.name for f in files])
    # Reorder the uploaded files based on selection
    files = [f for name in file_order for f in files if f.name == name]
    dfs = []
    for idx, f in enumerate(files):
        if f.name.endswith(".csv"):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)
        dfs.append(df)
    join_instructions = []
    for i in range(len(files)-1):
        file_left=files[i].name
        file_right=files[i+1].name
        st.markdown(f"**Join {file_left} → {file_left}**")
        left_col = st.selectbox(f"Column from File {i}", dfs[i].columns, key=f"left_{i}")
        right_col = st.selectbox(f"Column from File {i+1}", dfs[i+1].columns, key=f"right_{i}")
        how = st.selectbox(f"Join type for File {i} → File {i+1}", ["inner","left","right","outer"], key=f"how_{i}")
        if left_col and right_col:
            join_instructions.append((i, left_col, i+1, right_col, how))

    if st.button("Perform Join") and join_instructions:
        df, conn, table_name = multi_load_file_to_sqlite(files,join_instructions)
        st.session_state.conn=conn
        st.session_state.df=df
        st.success(f"Files joined successfully into table: {table_name}")
        st.dataframe(df.head())
        st.subheader("Detected Columns:")
        st.write(df.dtypes)


    if "df" in st.session_state and "conn"  in st.session_state:
        st.subheader("Ask a question:")
        user_input = st.text_input("Your question")
        llm(user_input, st.session_state.conn, st.session_state.df)




