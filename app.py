import streamlit as st
import os
import time
import uuid
import random
import matplotlib.pyplot as plt
import pandas as pd

from evaluation import (
    save_evaluation,
    get_evaluation_logs,
    save_experiment_rating,
    get_experiment_ratings,
    save_experiment_pair,
    get_experiment_pairs
)

from memory import (
    save_memory,
    get_memories,
    delete_memory
)

from knowledge_graph import (
    get_or_create_knowledge_graph,
    display_knowledge_graph
)

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==================================================
# 1. APPLICATION CONFIGURATION
# ==================================================

load_dotenv()

st.set_page_config(
    page_title="Memora AI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Memora")
st.caption("Your AI-powered personal knowledge assistant")


# ==================================================
# 2. GEMINI CONNECTION
# ==================================================

api_key = os.getenv("GEMINI_API_KEY")
# Read API key from Streamlit Cloud Secrets if available
try:
    api_key = st.secrets.get("GEMINI_API_KEY", api_key)
except Exception:
    pass

client = None

if api_key:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=120000)
    )


# ==================================================
# 3. SESSION STATE INITIALIZATION
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "multi_experiment_results" not in st.session_state:
    st.session_state.multi_experiment_results = []

if "quick_experiment" not in st.session_state:
    st.session_state.quick_experiment = None
    saved_pairs = get_experiment_pairs()
    for row in saved_pairs:
        if row[1] == "test_001":
             st.session_state.quick_experiment = {
                "experiment_id": row[1],
                "question": row[2],
                "with_memory": row[3],
                "without_memory": row[4]
            }
        break

if "saved_multi_ratings" not in st.session_state:
    st.session_state.saved_multi_ratings = set()

if "saved_quick_ratings" not in st.session_state:
    st.session_state.saved_quick_ratings = set()

if "blind_orders" not in st.session_state:
    st.session_state.blind_orders = {}


# Restore already-submitted rating keys from SQLite.
# This prevents the same ratings from being submitted again
# after a Streamlit session restart.

existing_ratings = get_experiment_ratings()

for rating in existing_ratings:

    experiment_id = rating[7]
    mode = rating[2]

    if experiment_id and mode in [
        "with_memory",
        "without_memory"
    ]:

        rating_key = f"{experiment_id}_{mode}"

        if experiment_id.startswith("memora_batch_v1_"):

            st.session_state.saved_multi_ratings.add(rating_key)

        else:

            st.session_state.saved_quick_ratings.add(rating_key)


# ==================================================
# 4. NAVIGATION
# ==================================================

st.sidebar.title("🧠 Memora Workspace")

page = st.sidebar.radio(
    "Navigation",
    [
        "AI Assistant",
        "My Memories",
        "Knowledge Graph",
        "Evaluation"
    ]
)


# ==================================================
# 5. GEMINI RESPONSE FUNCTION
# ==================================================

def generate_ai_response(question, use_memory=True):

    if not client:
        return "ERROR: Gemini API key is missing. Check your .env file."

    start_time = time.perf_counter()

    if use_memory:
        memories = get_memories()
    else:
        memories = []

    if use_memory and memories:

        memory_context = "\n".join(
            [
                f"- {content} (Category: {category})"
                for memory_id, content, category, created_at in memories
            ]
        )

    else:
        memory_context = "No personal memories provided."

    mode = "with_memory" if use_memory else "without_memory"

    prompt = f"""
You are Memora, an AI-powered personal knowledge assistant.

Instructions:
- Use saved memories when they are provided and relevant.
- Do not invent personal information.
- If the memories do not contain an answer, say so clearly.
- Distinguish known facts from suggestions or assumptions.
- Give a clear and helpful answer.

USER'S SAVED MEMORIES:
{memory_context}

USER'S QUESTION:
{question}
"""

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )

            latency = time.perf_counter() - start_time

            if response.text:

                answer = response.text

                save_evaluation(
                    question=question,
                    response=answer,
                    mode=mode,
                    latency=latency
                )

                return answer

            return "ERROR: Gemini returned an empty response."

        except Exception as e:

            error = str(e)
            error_upper = error.upper()

            # Do not retry quota exhaustion or rate limits.
            if (
                "RESOURCE_EXHAUSTED" in error_upper
                or "429" in error_upper
            ):

                return (
                    "ERROR: Gemini API quota or rate limit reached. "
                    + error
                )

            temporary_errors = [
                "503",
                "504",
                "UNAVAILABLE",
                "DEADLINE_EXCEEDED"
            ]

            should_retry = any(
                error_code in error_upper
                for error_code in temporary_errors
            )

            if should_retry and attempt < 2:

                wait_time = 3 * (attempt + 1)

                time.sleep(wait_time)

                continue

            return f"ERROR: {error}"

    return "ERROR: Gemini is temporarily unavailable. Please try again."


# ==================================================
# 6. BLIND HUMAN EVALUATION
# ==================================================

def display_blind_experiment(results, saved_ratings):

    experiment_id = results["experiment_id"]

    # Randomize the order once per experiment.
    # Keep the order stable during Streamlit reruns.
    if experiment_id not in st.session_state.blind_orders:

        modes = [
            "with_memory",
            "without_memory"
        ]

        random.shuffle(modes)

        st.session_state.blind_orders[experiment_id] = modes

    modes = st.session_state.blind_orders[experiment_id]

    labels = [
        "Response A",
        "Response B"
    ]

    st.info(results["question"])

    col1, col2 = st.columns(2)

    columns = [
        col1,
        col2
    ]

    for index, mode in enumerate(modes):

        label = labels[index]

        rating_key = f"{experiment_id}_{mode}"

        response = results[mode]

        with columns[index]:

            st.markdown(f"### {label}")

            st.write(response)

            with st.form(key=f"blind_form_{rating_key}"):

                relevance = st.slider(
                    "Relevance",
                    1,
                    5,
                    3,
                    key=f"blind_relevance_{rating_key}"
                )

                personalization = st.slider(
                    "Personalization",
                    1,
                    5,
                    3,
                    key=f"blind_personalization_{rating_key}"
                )

                accuracy = st.slider(
                    "Accuracy",
                    1,
                    5,
                    3,
                    key=f"blind_accuracy_{rating_key}"
                )

                submitted = st.form_submit_button(
                    f"Submit {label} Rating",
                    disabled=rating_key in saved_ratings
                )

                if submitted:

                    save_experiment_rating(
                        question=results["question"],
                        memory_mode=mode,
                        relevance=relevance,
                        personalization=personalization,
                        accuracy=accuracy,
                        experiment_id=experiment_id
                    )

                    saved_ratings.add(rating_key)

                    st.success(f"{label} rating saved!")

            if rating_key in saved_ratings:

                st.caption("Rating submitted.")

    # Reveal the mapping only after both responses are rated.
    rating_keys = [
        f"{experiment_id}_{mode}"
        for mode in modes
    ]

    if all(key in saved_ratings for key in rating_keys):

        st.success("Both responses have been rated.")

        st.subheader("🔍 Blind Evaluation Results Revealed")

        for index, mode in enumerate(modes):

            label = labels[index]

            actual_mode = (
                "Memory ON"
                if mode == "with_memory"
                else "Memory OFF"
            )

            st.write(f"**{label} was: {actual_mode}**")


# ==================================================
# 7. AI ASSISTANT
# ==================================================

if page == "AI Assistant":

    st.header("💬 Chat with Memora")

    st.write(
        "Ask questions and explore your personal knowledge with AI."
    )

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask Memora anything...")

    if question:

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):

            with st.spinner("Memora is thinking..."):

                answer = generate_ai_response(question)

            if answer.startswith("ERROR:"):

                st.error(
                    answer.replace("ERROR:", "", 1).strip()
                )

            else:

                st.markdown(answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })


# ==================================================
# 8. MEMORY MANAGEMENT
# ==================================================

elif page == "My Memories":

    st.header("🧠 My Memories")

    st.write(
        "Save important information that Memora can remember."
    )

    with st.form("save_memory_form"):

        content = st.text_area(
            "What should Memora remember?",
            placeholder=(
                "Example: I am studying computer science "
                "and interested in AI research."
            )
        )

        category = st.selectbox(
            "Memory category",
            [
                "General",
                "Personal",
                "Preferences",
                "Work/Study",
                "Projects"
            ]
        )

        submitted = st.form_submit_button("Save Memory")

        if submitted:

            if content.strip():

                save_memory(content.strip(), category)

                st.success("Memory saved successfully!")

                st.rerun()

            else:

                st.warning("Please enter something to remember.")

    st.divider()

    st.subheader("Your Saved Memories")

    memories = get_memories()

    if memories:

        for memory_id, content, category, created_at in memories:

            with st.container():

                col1, col2 = st.columns([5, 1])

                with col1:

                    st.markdown(f"**{category}**")

                    st.write(content)

                    st.caption(
                        created_at[:19].replace("T", " ")
                    )

                with col2:

                    if st.button(
                        "Delete",
                        key=f"delete_{memory_id}"
                    ):

                        delete_memory(memory_id)

                        st.rerun()

                st.divider()

    else:

        st.info(
            "No memories saved yet. Add your first memory above!"
        )


# ==================================================
# 9. KNOWLEDGE GRAPH
# ==================================================

elif page == "Knowledge Graph":

    st.header("🧠 Knowledge Graph")

    st.write(
        "Explore concepts and relationships extracted by AI."
    )

    memories = get_memories()

    if memories:

        try:

            with st.spinner("Loading your knowledge graph..."):

                graph, status = get_or_create_knowledge_graph(
                    memories,
                    client
                )

            if status == "cached":

                st.success(
                    "Loaded saved knowledge graph. "
                    "No Gemini API call needed!"
                )

            elif status == "generated":

                st.success(
                    "New knowledge graph generated and saved!"
                )

            if graph.number_of_nodes() > 0:

                col1, col2 = st.columns(2)

                col1.metric(
                    "Entities",
                    graph.number_of_nodes()
                )

                col2.metric(
                    "Relationships",
                    graph.number_of_edges()
                )

                fig = display_knowledge_graph(graph)

                if fig:

                    st.pyplot(fig)

                    plt.close(fig)

                st.subheader("Extracted Relationships")

                for source, target, data in graph.edges(data=True):

                    st.write(
                        f"**{source}** → "
                        f"{data['relation']} → **{target}**"
                    )

            else:

                st.info("No relationships were extracted.")

        except Exception as e:

            st.error(f"Knowledge graph error: {e}")

    else:

        st.info(
            "Save some memories first to build your knowledge graph."
        )


# ==================================================
# 10. EVALUATION LAB
# ==================================================

elif page == "Evaluation":

    st.header("📊 AI Evaluation Lab")

    st.write(
        "Monitor Memora's response performance and memory usage."
    )

    # ----------------------------------------------
    # EVALUATION QUESTIONS
    # ----------------------------------------------

    evaluation_questions = [

        "What technologies am I interested in learning and working with?",

        "What is my educational background?",

        "Which technical fields or areas have I expressed interest in?",

        "Which development tools or technologies have I explicitly mentioned?",

        "What degree have I completed?",

        "What do you know about my interest in LLMs and RAG?",

        "What specific technical interests can you identify from my saved memories?",

        "What learning goals have I explicitly shared?",

        "Suggest three project ideas based on my known technical interests. Explain why each fits.",

        "What do you know about my career plans? If I haven't shared any, say so rather than guessing."

    ]

    st.divider()

    st.subheader("🧪 Multi-Question Memory Experiment")

    st.write(
        "Compare Memory ON and Memory OFF across "
        "10 questions to evaluate personalization."
    )

    with st.expander("View the 10 evaluation questions"):

        for number, question in enumerate(
            evaluation_questions,
            start=1
        ):

            st.write(f"{number}. {question}")

    # ----------------------------------------------
    # QUICK ONE-QUESTION EXPERIMENT
    # ----------------------------------------------

    st.divider()

    st.subheader("🔬 Quick Memory Comparison")

    st.write(
        "Test one question with Memory ON and Memory OFF "
        "before running the larger experiment."
    )

    quick_question = (
        "What technologies am I interested in learning "
        "and working with?"
    )

    st.info(quick_question)

    if st.button("Run One-Question Comparison"):

        with st.spinner("Generating Memory ON response..."):

            quick_on = generate_ai_response(
                quick_question,
                use_memory=True
            )

        if quick_on.startswith("ERROR:"):

            st.error(quick_on)

        else:

            time.sleep(2)

            with st.spinner("Generating Memory OFF response..."):

                quick_off = generate_ai_response(
                    quick_question,
                    use_memory=False
                )

            if quick_off.startswith("ERROR:"):

                st.error(quick_off)

            else:

                experiment_id = str(uuid.uuid4())

                # Save both answers permanently in SQLite.
                save_experiment_pair(
                    experiment_id=experiment_id,
                    question=quick_question,
                    memory_on_response=quick_on,
                    memory_off_response=quick_off,
                    model="gemini-3.5-flash",
                    prompt_version="v1"
                )

                st.session_state.quick_experiment = {
                    "experiment_id": experiment_id,
                    "question": quick_question,
                    "with_memory": quick_on,
                    "without_memory": quick_off
                }

                # Remove any old blind order for this new experiment.
                st.session_state.blind_orders.pop(
                    experiment_id,
                    None
                )

                st.success(
                    "Both responses generated and saved permanently!"
                )

    # ----------------------------------------------
    # QUICK EXPERIMENT BLIND EVALUATION
    # ----------------------------------------------

    quick_results = st.session_state.quick_experiment

    if quick_results:

        st.markdown("### 🔬 Blind Evaluation — Quick Comparison")

        display_blind_experiment(
            results=quick_results,
            saved_ratings=st.session_state.saved_quick_ratings
        )


    # ----------------------------------------------
    # BATCHED TEN-QUESTION EXPERIMENT
    # ----------------------------------------------

    BATCH_EXPERIMENT_ID = "memora_batch_v1"

    # Load previously saved batch results from SQLite.
    saved_batch_pairs = [
        row for row in get_experiment_pairs()
        if row[1].startswith(BATCH_EXPERIMENT_ID + "_")
    ]

    experiment_runs = [
        {
            "experiment_id": row[1],
            "question": row[2],
            "with_memory": row[3],
            "without_memory": row[4]
        }
        for row in saved_batch_pairs
    ]

    # Keep session state synchronized with permanent storage.
    st.session_state.multi_experiment_results = experiment_runs

    st.divider()

    st.subheader("📚 Run the 10-Question Experiment in Batches")

    st.write(
        "Each batch contains two questions and requires "
        "four successful Gemini requests."
    )

    batch_options = [
        (0, 2),
        (2, 4),
        (4, 6),
        (6, 8),
        (8, 10)
    ]

    selected_batch = st.selectbox(
        "Select question batch",
        options=batch_options,
        format_func=lambda item: (
            f"Questions {item[0] + 1}–{item[1]}"
        )
    )

    if st.button("Run Selected Batch"):

        saved_questions = {
            row[2] for row in saved_batch_pairs
        }

        failed_questions = []

        start_index, end_index = selected_batch

        progress = st.progress(0)
        status = st.empty()

        quota_reached = False
        skipped_count = 0

        for index in range(start_index, end_index):

            question = evaluation_questions[index]

            # Avoid generating duplicate experiment pairs.
            if question in saved_questions:

                skipped_count += 1

                progress.progress(
                    (index - start_index + 1)
                    / (end_index - start_index)
                )

                continue

            status.write(
                f"Running question {index + 1} "
                f"of {len(evaluation_questions)}..."
            )

            with_memory_response = generate_ai_response(
                question,
                use_memory=True
            )

            if with_memory_response.startswith("ERROR:"):

                failed_questions.append({
                    "question": question,
                    "memory_on_error": with_memory_response,
                    "memory_off_error": None
                })

                if (
                    "QUOTA" in with_memory_response.upper()
                    or "RESOURCE_EXHAUSTED" in with_memory_response.upper()
                ):
                    quota_reached = True
                    break

                progress.progress(
                    (index - start_index + 1)
                    / (end_index - start_index)
                )

                continue

            time.sleep(2)

            without_memory_response = generate_ai_response(
                question,
                use_memory=False
            )

            if without_memory_response.startswith("ERROR:"):

                failed_questions.append({
                    "question": question,
                    "memory_on_error": None,
                    "memory_off_error": without_memory_response
                })

                if (
                    "QUOTA" in without_memory_response.upper()
                    or "RESOURCE_EXHAUSTED" in without_memory_response.upper()
                ):
                    quota_reached = True
                    break

            else:

                # Give each question its own stable experiment ID.
                question_experiment_id = (
                    f"{BATCH_EXPERIMENT_ID}_{index + 1:02d}"
                )

                # Save the completed pair permanently.
                save_experiment_pair(
                    experiment_id=question_experiment_id,
                    question=question,
                    memory_on_response=with_memory_response,
                    memory_off_response=without_memory_response,
                    model="gemini-3.5-flash",
                    prompt_version="v1"
                )

                saved_questions.add(question)

            progress.progress(
                (index - start_index + 1)
                / (end_index - start_index)
            )

        # Reload all saved results after the batch.
        saved_batch_pairs = [
            row for row in get_experiment_pairs()
            if row[1].startswith(BATCH_EXPERIMENT_ID + "_")
        ]

        experiment_runs = [
            {
                "experiment_id": row[1],
                "question": row[2],
                "with_memory": row[3],
                "without_memory": row[4]
            }
            for row in saved_batch_pairs
        ]

        st.session_state.multi_experiment_results = experiment_runs

        status.empty()

        if failed_questions:

            st.warning(
                f"{len(failed_questions)} question(s) "
                "could not be completed."
            )

            for failure in failed_questions:

                with st.expander(failure["question"]):

                    if failure["memory_on_error"]:
                        st.error(
                            "Memory ON: "
                            + failure["memory_on_error"]
                        )

                    if failure["memory_off_error"]:
                        st.error(
                            "Memory OFF: "
                            + failure["memory_off_error"]
                        )

        if skipped_count:

            st.info(
                f"Skipped {skipped_count} question(s) "
                "that were already saved."
            )

        if quota_reached:

            st.error(
                "Gemini quota was reached. Stop running experiments "
                "until the quota resets."
            )

        st.success(
            f"Total permanently saved batch comparisons: "
            f"{len(experiment_runs)} out of 10."
        )


    # ----------------------------------------------
    # DISPLAY MULTI-QUESTION RESULTS AND BLIND RATINGS
    # ----------------------------------------------

    experiment_results = st.session_state.multi_experiment_results

    if experiment_results:

        st.divider()

        st.subheader("📝 Blind Evaluation of Experiment Responses")

        st.write(
            "Rate Response A and Response B without knowing "
            "which response used memory."
        )

        for index, results in enumerate(experiment_results):

            st.divider()

            st.markdown(
                f"### Experiment {index + 1}"
            )

            display_blind_experiment(
                results=results,
                saved_ratings=st.session_state.saved_multi_ratings
            )


    # ----------------------------------------------
    # EXPERIMENT DATA EXPORT
    # ----------------------------------------------

    st.divider()

    st.subheader("📥 Export Research Data")

    # Export experiment response pairs.
    all_pairs = get_experiment_pairs()

    if all_pairs:

        response_data = []

        for row in all_pairs:

            response_data.append({
                "Experiment ID": row[1],
                "Question": row[2],
                "Memory ON Response": row[3],
                "Memory OFF Response": row[4],
                "Model": row[5],
                "Prompt Version": row[6],
                "Created At": row[7]
            })

        response_df = pd.DataFrame(response_data)

        response_csv = response_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="Download Experiment Responses CSV",
            data=response_csv,
            file_name="memora_experiment_responses.csv",
            mime="text/csv"
        )

    else:

        st.info("No experiment responses available to export.")

    # Export human evaluation ratings.
    all_ratings = get_experiment_ratings()

    if all_ratings:

        rating_data = []

        for row in all_ratings:

            rating_data.append({
                "Question": row[1],
                "Memory Mode": row[2],
                "Relevance": row[3],
                "Personalization": row[4],
                "Accuracy": row[5],
                "Experiment ID": row[7]
            })

        ratings_df = pd.DataFrame(rating_data)

        ratings_csv = ratings_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="Download Human Ratings CSV",
            data=ratings_csv,
            file_name="memora_human_ratings.csv",
            mime="text/csv"
        )

    else:

        st.info("No human ratings available to export.")


    # ----------------------------------------------
    # HUMAN EVALUATION DASHBOARD
    # ----------------------------------------------

    st.divider()

    st.subheader("📈 Human Evaluation Dashboard")

    ratings = get_experiment_ratings()

    paired_experiments = {}

    for rating in ratings:

        experiment_id = rating[7]

        if experiment_id:

            if experiment_id not in paired_experiments:

                paired_experiments[experiment_id] = {}

            paired_experiments[experiment_id].setdefault(
                rating[2],
                rating
            )

    completed_pairs = {

        experiment_id: modes

        for experiment_id, modes in paired_experiments.items()

        if (
            "with_memory" in modes
            and "without_memory" in modes
        )
    }

    st.write(f"Total ratings collected: {len(ratings)}")

    st.metric(
        "Completed Paired Experiments",
        len(completed_pairs)
    )

    if completed_pairs:

        memory_on = [
            pair["with_memory"]
            for pair in completed_pairs.values()
        ]

        memory_off = [
            pair["without_memory"]
            for pair in completed_pairs.values()
        ]

        metrics = [
            ("Relevance", 3),
            ("Personalization", 4),
            ("Accuracy", 5)
        ]

        comparison_data = {}

        for metric_name, column_index in metrics:

            on_average = sum(
                row[column_index]
                for row in memory_on
            ) / len(memory_on)

            off_average = sum(
                row[column_index]
                for row in memory_off
            ) / len(memory_off)

            comparison_data[metric_name] = {

                "Memory ON": on_average,

                "Memory OFF": off_average

            }

        st.subheader("Average Human Evaluation Scores")

        chart_rows = []

        for metric_name, scores in comparison_data.items():

            chart_rows.append({

                "Metric": metric_name,

                "Memory ON": scores["Memory ON"],

                "Memory OFF": scores["Memory OFF"]

            })

        st.bar_chart(
            chart_rows,
            x="Metric",
            y=["Memory ON", "Memory OFF"]
        )

        st.subheader("Detailed Score Comparison")

        for metric_name, scores in comparison_data.items():

            col1, col2, col3 = st.columns(3)

            col1.metric(
                f"{metric_name} - Memory ON",
                f"{scores['Memory ON']:.2f}/5"
            )

            col2.metric(
                f"{metric_name} - Memory OFF",
                f"{scores['Memory OFF']:.2f}/5"
            )

            col3.metric(
                "Difference",
                f"{scores['Memory ON'] - scores['Memory OFF']:+.2f}"
            )

    else:

        st.info(
            "No completed paired experiments yet. "
            "Submit ratings for both Memory ON and Memory OFF."
        )


    # ----------------------------------------------
    # RESPONSE PERFORMANCE DASHBOARD
    # ----------------------------------------------

    st.divider()

    st.subheader("⚡ Response Performance")

    logs = get_evaluation_logs()

    if logs:

        total_queries = len(logs)

        average_latency = sum(
            log[4]
            for log in logs
        ) / total_queries

        memory_queries = sum(
            1
            for log in logs
            if log[3] == "with_memory"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Queries",
            total_queries
        )

        col2.metric(
            "Average Response Time",
            f"{average_latency:.2f} sec"
        )

        col3.metric(
            "Queries with Memory",
            memory_queries
        )

        st.divider()

        st.subheader("Response Time History")

        chart_data = {

            "Query": [
                f"Query {log[0]}"
                for log in reversed(logs)
            ],

            "Response Time (seconds)": [
                log[4]
                for log in reversed(logs)
            ]

        }

        st.line_chart(
            chart_data,
            x="Query",
            y="Response Time (seconds)"
        )

        st.divider()

        st.subheader("Evaluation Records")

        for log in logs:

            with st.expander(
                f"Query {log[0]} - {log[3]}"
            ):

                st.write("**Question:**", log[1])

                st.write("**AI Response:**", log[2])

                st.write("**Memory Mode:**", log[3])

                st.write(
                    "**Response Time:**",
                    f"{log[4]:.2f} seconds"
                )

                st.caption(log[5])

    else:

        st.info(
            "No evaluation records yet. "
            "Ask Memora a question first."
        )


# ==================================================
# 11. SIDEBAR FOOTER
# ==================================================

st.sidebar.divider()

st.sidebar.caption(
    "Memora AI | Human-Centered AI Research Project"
)
