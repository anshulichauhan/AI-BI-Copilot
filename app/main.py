import os
import time

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from google import genai


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="AI Business Intelligence Copilot",
    page_icon="📊",
    layout="wide"
)


# ==================================================
# GEMINI CONFIGURATION
# ==================================================

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

# Keep the model that worked with your free-tier account.
MODEL_NAME = "gemini-3.5-flash"

client = None

if gemini_api_key:
    client = genai.Client(
        api_key=gemini_api_key
    )


# ==================================================
# HELPER FUNCTION
# ==================================================

def generate_gemini_response(
    prompt: str,
    maximum_attempts: int = 3
) -> str:
    """
    Send a prompt to Gemini and retry temporary errors.
    """

    if client is None:
        raise RuntimeError(
            "Gemini API key was not loaded."
        )

    for attempt in range(maximum_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if response and response.text:
                return response.text

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        except Exception as error:
            error_message = str(error)

            temporary_error = any(
                code in error_message
                for code in [
                    "429",
                    "500",
                    "502",
                    "503",
                    "504"
                ]
            )

            final_attempt = (
                attempt == maximum_attempts - 1
            )

            if temporary_error and not final_attempt:
                time.sleep(5)
                continue

            raise

    raise RuntimeError(
        "Gemini could not generate a response."
    )


# ==================================================
# PAGE HEADING
# ==================================================

st.title("AI Business Intelligence Copilot")

st.write(
    "Upload Stack Overflow data, explore KPIs and trends, "
    "generate an executive report, and ask AI questions "
    "about the dataset."
)

if gemini_api_key:
    st.success(
        "Gemini API key loaded successfully."
    )
else:
    st.error(
        "Gemini API key was not found. Check your .env file."
    )


# ==================================================
# CSV UPLOADER
# ==================================================

uploaded_file = st.file_uploader(
    "Upload a Stack Overflow CSV file",
    type=["csv"]
)


# ==================================================
# RUN ANALYSIS AFTER FILE UPLOAD
# ==================================================

if uploaded_file is not None:

    # ----------------------------------------------
    # READ CSV
    # ----------------------------------------------

    try:
        df = pd.read_csv(uploaded_file)

    except Exception as error:
        st.error(
            f"The CSV file could not be read: {error}"
        )
        st.stop()

    st.success("File uploaded successfully.")

    # ----------------------------------------------
    # VALIDATE REQUIRED COLUMNS
    # ----------------------------------------------

    required_columns = {
        "title",
        "tags",
        "creation_date",
        "answer_count",
        "score",
        "view_count",
        "accepted_answer_id"
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        st.error(
            "This application currently requires the "
            "Stack Overflow dataset structure."
        )

        st.write(
            "Missing columns:",
            sorted(missing_columns)
        )

        st.write(
            "Columns found:",
            list(df.columns)
        )

        st.stop()

    # ----------------------------------------------
    # PREPARE DATA TYPES
    # ----------------------------------------------

    numeric_columns = [
        "answer_count",
        "score",
        "view_count",
        "accepted_answer_id"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df["creation_date"] = pd.to_datetime(
        df["creation_date"],
        errors="coerce"
    )

    # ----------------------------------------------
    # CALCULATE KPIs
    # ----------------------------------------------

    total_questions = len(df)

    total_views = float(
        df["view_count"].sum()
    )

    average_views = (
        total_views / total_questions
        if total_questions > 0
        else 0
    )

    average_score = float(
        df["score"].mean()
    )

    average_answers = float(
        df["answer_count"].mean()
    )

    accepted_answers = int(
        df["accepted_answer_id"]
        .notna()
        .sum()
    )

    no_recorded_accepted_answer = (
        total_questions - accepted_answers
    )

    accepted_answer_rate = (
        accepted_answers / total_questions * 100
        if total_questions > 0
        else 0
    )

    # ----------------------------------------------
    # KPI CARDS
    # ----------------------------------------------

    st.subheader("Key Performance Indicators")

    kpi1, kpi2, kpi3, kpi4, kpi5 = (
        st.columns(5)
    )

    with kpi1:
        st.metric(
            "Total Questions",
            f"{total_questions:,}"
        )

    with kpi2:
        st.metric(
            "Total Views",
            f"{total_views:,.0f}"
        )

    with kpi3:
        st.metric(
            "Average Views",
            f"{average_views:,.2f}"
        )

    with kpi4:
        st.metric(
            "Average Score",
            f"{average_score:.2f}"
        )

    with kpi5:
        st.metric(
            "Accepted Answer Rate",
            f"{accepted_answer_rate:.1f}%"
        )

    # ----------------------------------------------
    # TECHNOLOGY TAG ANALYSIS
    # ----------------------------------------------

    st.subheader("Top 10 Technology Tags")

    all_tags = (
        df["tags"]
        .dropna()
        .astype(str)
        .str.split("|")
        .explode()
        .str.strip()
    )

    all_tags = all_tags[
        all_tags != ""
    ]

    top_tags = (
        all_tags
        .value_counts()
        .head(10)
        .rename_axis("Technology")
        .reset_index(name="Question Count")
    )

    if not top_tags.empty:
        tag_chart = px.bar(
            top_tags,
            x="Question Count",
            y="Technology",
            orientation="h",
            title="Most Frequently Used Technology Tags"
        )

        tag_chart.update_layout(
            yaxis={
                "categoryorder": "total ascending"
            }
        )

        st.plotly_chart(
            tag_chart,
            use_container_width=True
        )

    else:
        st.info(
            "No valid technology tags were found."
        )

    # ----------------------------------------------
    # QUESTIONS OVER TIME
    # ----------------------------------------------

    st.subheader("Questions Over Time")

    questions_over_time = (
        df.dropna(
            subset=["creation_date"]
        )
        .assign(
            Month=lambda data: (
                data["creation_date"]
                .dt.to_period("M")
                .astype(str)
            )
        )
        .groupby("Month")
        .size()
        .reset_index(
            name="Question Count"
        )
    )

    if not questions_over_time.empty:
        time_chart = px.line(
            questions_over_time,
            x="Month",
            y="Question Count",
            markers=True,
            title="Monthly Question Volume"
        )

        st.plotly_chart(
            time_chart,
            use_container_width=True
        )

    else:
        st.info(
            "No valid creation dates were available "
            "for the time-series chart."
        )

    # ----------------------------------------------
    # ACCEPTED ANSWER ANALYSIS
    # ----------------------------------------------

    st.subheader("Accepted Answer Analysis")

    accepted_answer_data = pd.DataFrame(
        {
            "Status": [
                "Recorded Accepted Answer",
                "No Recorded Accepted Answer"
            ],
            "Question Count": [
                accepted_answers,
                no_recorded_accepted_answer
            ]
        }
    )

    accepted_chart = px.pie(
        accepted_answer_data,
        names="Status",
        values="Question Count",
        title="Recorded Accepted-Answer Status",
        hole=0.4
    )

    st.plotly_chart(
        accepted_chart,
        use_container_width=True
    )

    # ----------------------------------------------
    # TOP VIEWED QUESTIONS
    # ----------------------------------------------

    st.subheader(
        "Top 10 Most Viewed Questions"
    )

    top_viewed_questions = (
        df[
            [
                "title",
                "view_count",
                "score",
                "answer_count"
            ]
        ]
        .dropna(
            subset=[
                "title",
                "view_count"
            ]
        )
        .sort_values(
            by="view_count",
            ascending=False
        )
        .head(10)
    )

    if not top_viewed_questions.empty:
        viewed_chart = px.bar(
            top_viewed_questions,
            x="view_count",
            y="title",
            orientation="h",
            title="Questions With the Highest View Counts",
            labels={
                "view_count": "Views",
                "title": "Question"
            },
            hover_data=[
                "score",
                "answer_count"
            ]
        )

        viewed_chart.update_layout(
            yaxis={
                "categoryorder": "total ascending"
            }
        )

        st.plotly_chart(
            viewed_chart,
            use_container_width=True
        )

    # ----------------------------------------------
    # DATA PROFILING
    # ----------------------------------------------

    st.divider()
    st.subheader("Dataset Profiling")

    overview_col1, overview_col2 = (
        st.columns(2)
    )

    with overview_col1:
        st.metric(
            "Number of Rows",
            df.shape[0]
        )

    with overview_col2:
        st.metric(
            "Number of Columns",
            df.shape[1]
        )

    data_types = (
        df.dtypes
        .astype(str)
        .reset_index()
    )

    data_types.columns = [
        "Column",
        "Data Type"
    ]

    missing_values = (
        df.isnull()
        .sum()
        .reset_index()
    )

    missing_values.columns = [
        "Column",
        "Missing Values"
    ]

    with st.expander(
        "View Data Preview"
    ):
        st.dataframe(
            df.head(),
            use_container_width=True
        )

    with st.expander(
        "View Column Names"
    ):
        st.write(
            list(df.columns)
        )

    with st.expander(
        "View Data Types"
    ):
        st.dataframe(
            data_types,
            use_container_width=True,
            hide_index=True
        )

    with st.expander(
        "View Missing Values by Column"
    ):
        st.dataframe(
            missing_values,
            use_container_width=True,
            hide_index=True
        )

    # ----------------------------------------------
    # DATA QUALITY
    # ----------------------------------------------

    st.subheader("Data Quality Summary")

    duplicate_rows = int(
        df.duplicated().sum()
    )

    total_missing = int(
        df.isnull().sum().sum()
    )

    quality_col1, quality_col2 = (
        st.columns(2)
    )

    with quality_col1:
        st.metric(
            "Exact Duplicate Rows",
            duplicate_rows
        )

    with quality_col2:
        st.metric(
            "Total Missing Values",
            total_missing
        )

    if (
        duplicate_rows == 0
        and total_missing == 0
    ):
        st.success(
            "No exact duplicate rows or missing values were found."
        )

    elif duplicate_rows == 0:
        st.info(
            f"No exact duplicate rows were found, "
            f"but the dataset contains "
            f"{total_missing} missing values."
        )

    elif total_missing == 0:
        st.warning(
            f"The dataset contains "
            f"{duplicate_rows} exact duplicate rows "
            "but no missing values."
        )

    else:
        st.warning(
            f"The dataset contains "
            f"{duplicate_rows} exact duplicate rows "
            f"and {total_missing} missing values."
        )

    # ----------------------------------------------
    # CREATE DATASET CONTEXT FOR GEMINI
    # ----------------------------------------------

    missing_value_summary = ", ".join(
        (
            f"{row['Column']}: "
            f"{int(row['Missing Values'])}"
        )
        for _, row in missing_values.iterrows()
        if row["Missing Values"] > 0
    )

    if not missing_value_summary:
        missing_value_summary = (
            "No missing values"
        )

    top_technology_summary = ", ".join(
        top_tags[
            "Technology"
        ]
        .head(5)
        .tolist()
    )

    top_question_summary = "\n".join(
        (
            f"- {row['title']} "
            f"({row['view_count']:,.0f} views, "
            f"score {row['score']}, "
            f"{row['answer_count']} answers)"
        )
        for _, row in (
            top_viewed_questions
            .head(5)
            .iterrows()
        )
    )

    dataset_context = f"""
Stack Overflow Dataset Summary

Total questions: {total_questions:,}
Total views: {total_views:,.0f}
Average views per question: {average_views:.2f}
Average score: {average_score:.2f}
Average answers per question: {average_answers:.2f}
Questions with a recorded accepted answer: {accepted_answers:,}
Questions without a recorded accepted answer: {no_recorded_accepted_answer:,}
Accepted answer rate: {accepted_answer_rate:.1f}%
Top technologies: {top_technology_summary}
Exact duplicate rows: {duplicate_rows}
Total missing values: {total_missing}
Missing values by column: {missing_value_summary}

Top viewed questions:
{top_question_summary}
"""

    # ----------------------------------------------
    # AI EXECUTIVE REPORT
    # ----------------------------------------------

    st.divider()
    st.subheader(
        "AI-Generated Executive Report"
    )

    insight_prompt = f"""
You are a careful Business Intelligence Analyst.

Analyse the dataset context below.

{dataset_context}

Produce a concise management-style report with:

1. Executive summary
2. Key trends
3. Engagement observations
4. Data-quality observations
5. Three practical recommendations

Rules:

- Use only the supplied evidence.
- Separate observed facts, calculated insights,
  and assumptions.
- Do not describe questions without a recorded
  accepted answer as unresolved.
- Do not automatically treat missing
  accepted_answer_id values as data errors.
- Do not invent causes, user behaviour,
  business outcomes, or SEO conclusions.
- State clearly when something cannot be
  determined from the supplied information.
"""

    if st.button(
        "Generate AI Executive Report",
        type="primary"
    ):
        try:
            with st.spinner(
                "Gemini is analysing the dataset..."
            ):
                report_text = (
                    generate_gemini_response(
                        insight_prompt
                    )
                )

            with st.container(
                border=True
            ):
                st.markdown(
                    report_text
                )

            st.download_button(
                label="Download Executive Report",
                data=report_text,
                file_name="ai_executive_report.txt",
                mime="text/plain"
            )

        except Exception as error:
            st.error(
                "Gemini could not generate "
                f"the report: {error}"
            )

    # ----------------------------------------------
    # ASK AI ABOUT THE DATASET
    # ----------------------------------------------

    st.divider()
    st.subheader(
        "Ask AI About Your Dataset"
    )

    user_question = st.text_input(
        "Ask a question about the uploaded dataset",
        placeholder=(
            "For example: Which engagement "
            "metric should be investigated?"
        )
    )

    if st.button("Ask Gemini"):

        if not user_question.strip():
            st.warning(
                "Please enter a question first."
            )

        else:
            question_prompt = f"""
You are a careful Business Intelligence Analyst.

Use only the dataset context below.

{dataset_context}

User question:

{user_question}

Answer professionally and concisely.

Rules:

- Use only the supplied dataset context.
- Do not guess or invent explanations.
- Clearly separate facts from assumptions.
- State when the answer cannot be determined.
- Do not claim that a missing
  accepted_answer_id means that a question
  is unresolved.
"""

            try:
                with st.spinner(
                    "Gemini is thinking..."
                ):
                    answer_text = (
                        generate_gemini_response(
                            question_prompt
                        )
                    )

                with st.container(
                    border=True
                ):
                    st.markdown(
                        answer_text
                    )

            except Exception as error:
                st.error(
                    "Gemini could not answer "
                    f"the question: {error}"
                )

else:
    st.info(
        "Upload a Stack Overflow CSV file "
        "to begin analysing the dataset."
    )