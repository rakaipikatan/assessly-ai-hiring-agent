import streamlit as st
import json
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Assessly", layout="wide")
session = get_active_session()

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        color: #6b7280;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .stat-card h2 { margin: 0; font-size: 2rem; color: white; }
    .stat-card p { margin: 5px 0 0 0; opacity: 0.9; font-size: 0.85rem; }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
    }
    div[data-testid="stSidebar"] .stMarkdown, div[data-testid="stSidebar"] label {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# State
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"
if "candidate_logged_in" not in st.session_state:
    st.session_state.candidate_logged_in = False

# Sidebar
with st.sidebar:
    st.markdown("# ASSESSLY")
    st.markdown("*AI Hiring Agent*")
    st.markdown("---")
    mode = st.radio("Mode", ["Recruiter", "Candidate"])
    if mode == "Recruiter":
        st.markdown("---")
        menu = {"Dashboard": "dashboard", "Create Job": "create_job", "Assessments": "assessments", "Candidates": "candidates", "Results": "results"}
        for label, key in menu.items():
            if st.button(label, use_container_width=True, type="primary" if st.session_state.current_page == key else "secondary"):
                st.session_state.current_page = key
                st.rerun()
    else:
        st.session_state.current_page = "candidate_portal"
    st.markdown("---")
    st.caption("Powered by Snowflake Cortex AI")

# === DASHBOARD ===
def page_dashboard():
    st.markdown('<p class="main-header">Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Overview of your hiring pipeline</p>', unsafe_allow_html=True)
    jobs_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS").collect()[0]["CNT"]
    assessments_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS WHERE status = 'PUBLISHED'").collect()[0]["CNT"]
    candidates_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES").collect()[0]["CNT"]
    evaluated_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES WHERE status = 'EVALUATED'").collect()[0]["CNT"]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h2>{jobs_count}</h2><p>Total Jobs</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h2>{assessments_count}</h2><p>Active Assessments</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h2>{candidates_count}</h2><p>Total Candidates</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h2>{evaluated_count}</h2><p>Evaluated</p></div>', unsafe_allow_html=True)
    st.markdown("")
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Recent Jobs")
        jobs_df = session.sql("SELECT job_id as ID, title as Title, department as Dept, seniority_level as Level, status as Status FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS ORDER BY created_at DESC LIMIT 5").to_pandas()
        if len(jobs_df) > 0:
            st.dataframe(jobs_df, use_container_width=True, hide_index=True)
        else:
            st.info("No jobs yet. Click **Create Job** to get started!")
    with col_right:
        st.subheader("Pending Reviews")
        pending_df = session.sql("SELECT c.candidate_name as Name, c.status as Status FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c WHERE c.status = 'COMPLETED' LIMIT 5").to_pandas()
        if len(pending_df) > 0:
            for _, row in pending_df.iterrows():
                st.markdown(f"**{row['NAME']}** — awaiting eval")
        else:
            st.caption("No pending reviews")

# === CREATE JOB ===
def page_create_job():
    st.markdown('<p class="main-header">Create New Job</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Describe the role and let AI generate the assessment</p>', unsafe_allow_html=True)
    with st.form("create_job_form"):
        title = st.text_input("Job Title *", placeholder="e.g. Senior Backend Engineer")
        col1, col2, col3 = st.columns(3)
        with col1:
            department = st.text_input("Department", placeholder="Engineering")
        with col2:
            seniority = st.selectbox("Seniority", ["Junior", "Mid-level", "Senior", "Lead", "Principal"])
        with col3:
            employment_type = st.selectbox("Type", ["Full-time", "Part-time", "Contract"])
        description = st.text_area("Job Description *", height=120, placeholder="Describe the role...")
        requirements = st.text_area("Requirements & Skills *", height=120, placeholder="Python, FastAPI, PostgreSQL...")
        auto_generate = st.checkbox("Auto-generate assessment", value=True)
        submitted = st.form_submit_button("Create Job & Generate Assessment", type="primary", use_container_width=True)
    if submitted:
        if not title or not description:
            st.error("Please fill in Job Title and Description.")
            return
        with st.spinner("Creating job..."):
            session.sql("INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS (title, description, requirements, department, seniority_level, employment_type, status) VALUES (?, ?, ?, ?, ?, ?, 'DRAFT')", params=[title, description, requirements, department, seniority, employment_type]).collect()
            job_id = session.sql("SELECT MAX(job_id) as id FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS").collect()[0]["ID"]
        st.success(f"Job **{title}** created! (ID: {job_id})")
        if auto_generate:
            with st.spinner("AI is mapping competencies..."):
                r1 = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_COMPETENCIES({job_id})").collect()[0][0]
                st.info(r1)
            with st.spinner("AI is generating assessment questions (30-60s)..."):
                r2 = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_ASSESSMENT({job_id})").collect()[0][0]
                st.success(r2)
            st.balloons()

# === ASSESSMENTS ===
def page_assessments():
    st.markdown('<p class="main-header">Assessments</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Review and publish AI-generated assessments</p>', unsafe_allow_html=True)
    assessments_df = session.sql("""
        SELECT a.assessment_id, a.title, j.title as job_title, a.total_questions, a.status
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id
        ORDER BY a.created_at DESC
    """).to_pandas()
    if len(assessments_df) == 0:
        st.info("No assessments yet. Create a job to generate one.")
        return
    st.dataframe(assessments_df, use_container_width=True, hide_index=True)
    selected_id = st.selectbox("Select Assessment ID", assessments_df["ASSESSMENT_ID"].tolist())
    row = assessments_df[assessments_df["ASSESSMENT_ID"] == selected_id].iloc[0]
    col1, col2 = st.columns(2)
    if row["STATUS"] == "DRAFT":
        if col1.button("Publish Assessment", type="primary"):
            session.sql(f"UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS SET status = 'PUBLISHED', published_at = CURRENT_TIMESTAMP() WHERE assessment_id = {selected_id}").collect()
            st.success("Published!")
            st.rerun()
    else:
        col1.success("PUBLISHED")
    if col2.button("View Questions"):
        questions_df = session.sql(f"""
            SELECT sort_order as Q, question_type as Type, difficulty as Difficulty, question_text as Question, max_score as Points
            FROM ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS WHERE assessment_id = {selected_id} ORDER BY sort_order
        """).to_pandas()
        st.dataframe(questions_df, use_container_width=True, hide_index=True)

# === CANDIDATES ===
def page_candidates():
    st.markdown('<p class="main-header">Candidates</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Invite candidates and track progress</p>', unsafe_allow_html=True)
    published = session.sql("""
        SELECT a.assessment_id, a.title || ' - ' || j.title as label
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id WHERE a.status = 'PUBLISHED'
    """).to_pandas()
    if len(published) > 0:
        with st.form("add_candidate"):
            assess_id = st.selectbox("Assessment", published["ASSESSMENT_ID"].tolist(), format_func=lambda x: published[published["ASSESSMENT_ID"]==x]["LABEL"].values[0])
            col1, col2 = st.columns(2)
            cand_name = col1.text_input("Candidate Name *")
            cand_email = col2.text_input("Candidate Email")
            if st.form_submit_button("Add Candidate", type="primary", use_container_width=True):
                if cand_name:
                    result = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.ADD_CANDIDATE({assess_id}, ?, ?)", params=[cand_name, cand_email]).collect()[0][0]
                    st.success(result)
    else:
        st.warning("Publish an assessment first.")
    st.markdown("---")
    st.subheader("Candidate List")
    candidates_df = session.sql("""
        SELECT c.candidate_id as ID, c.candidate_name as Name, c.access_token as Token, c.status as Status, a.title as Assessment
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
        ORDER BY c.created_at DESC
    """).to_pandas()
    if len(candidates_df) > 0:
        st.dataframe(candidates_df, use_container_width=True, hide_index=True)
        completed = candidates_df[candidates_df["STATUS"] == "COMPLETED"]
        if len(completed) > 0:
            st.subheader("Ready for Evaluation")
            for _, row in completed.iterrows():
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{row['NAME']}** — {row['ASSESSMENT']}")
                if col2.button("Evaluate", key=f"eval_{row['ID']}"):
                    with st.spinner(f"AI evaluating {row['NAME']}..."):
                        result = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATE_CANDIDATE({row['ID']})").collect()[0][0]
                        st.success(result)
                    st.rerun()

# === RESULTS ===
def page_results():
    st.markdown('<p class="main-header">Results & Reports</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered evaluation results and hiring recommendations</p>', unsafe_allow_html=True)
    results_df = session.sql("""
        SELECT c.candidate_id, c.candidate_name as Candidate, j.title as Position,
               e.percentage_score as Score, e.recommendation as Recommendation,
               e.ai_reasoning as AI_Assessment, e.competency_scores
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATIONS e
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c ON c.candidate_id = e.candidate_id
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id
        ORDER BY e.percentage_score DESC
    """).to_pandas()
    if len(results_df) == 0:
        st.info("No results yet. Evaluate candidates first.")
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Evaluated", len(results_df))
    col2.metric("Strong Hire", len(results_df[results_df["RECOMMENDATION"] == "STRONG_HIRE"]))
    col3.metric("No Hire", len(results_df[results_df["RECOMMENDATION"] == "NO_HIRE"]))
    st.dataframe(results_df[["CANDIDATE", "POSITION", "SCORE", "RECOMMENDATION"]], use_container_width=True, hide_index=True)
    for _, row in results_df.iterrows():
        with st.expander(f"{row['CANDIDATE']} — {row['SCORE']:.0f}% — {row['RECOMMENDATION']}"):
            st.write(row["AI_ASSESSMENT"])
            if row["COMPETENCY_SCORES"]:
                scores = json.loads(row["COMPETENCY_SCORES"]) if isinstance(row["COMPETENCY_SCORES"], str) else row["COMPETENCY_SCORES"]
                if scores:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Strengths:**")
                        for s in scores.get("strengths", []):
                            st.markdown(f"- {s}")
                    with c2:
                        st.markdown("**Weaknesses:**")
                        for w in scores.get("weaknesses", []):
                            st.markdown(f"- {w}")
    st.markdown("---")
    report_options = {f"{row['CANDIDATE']} — {row['POSITION']}": row["CANDIDATE_ID"] for _, row in results_df.iterrows()}
    selected_report = st.selectbox("Generate report for", list(report_options.keys()))
    if st.button("Generate Hiring Report", type="primary"):
        cid = report_options[selected_report]
        with st.spinner("Generating..."):
            report = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_RECOMMENDATION({cid})").collect()[0][0]
            st.markdown("### Hiring Report")
            st.markdown(report)

# === CANDIDATE PORTAL ===
def page_candidate_portal():
    st.markdown('<p class="main-header">Assessment Portal</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete your assessment below</p>', unsafe_allow_html=True)
    if st.session_state.candidate_logged_in:
        render_assessment()
        return
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Enter your access token")
        token = st.text_input("Access Token", type="password", placeholder="Paste token here")
        if st.button("Start Assessment", type="primary", use_container_width=True) and token:
            candidate = session.sql(f"""
                SELECT c.candidate_id, c.candidate_name, c.assessment_id, c.status, a.title, a.duration_minutes
                FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c
                JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
                WHERE c.access_token = '{token}' AND a.status = 'PUBLISHED'
            """).collect()
            if not candidate:
                st.error("Invalid token.")
            elif candidate[0]["STATUS"] in ("COMPLETED", "EVALUATED"):
                st.warning("Already completed.")
            else:
                c = candidate[0]
                st.session_state.candidate_logged_in = True
                st.session_state.cand_id = c["CANDIDATE_ID"]
                st.session_state.assess_id = c["ASSESSMENT_ID"]
                st.session_state.cand_name = c["CANDIDATE_NAME"]
                st.session_state.assess_title = c["TITLE"]
                st.session_state.duration = c["DURATION_MINUTES"]
                session.sql(f"UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES SET status = 'IN_PROGRESS', started_at = CURRENT_TIMESTAMP() WHERE candidate_id = {c['CANDIDATE_ID']}").collect()
                st.rerun()

def render_assessment():
    cand_id = st.session_state.cand_id
    assess_id = st.session_state.assess_id
    st.info(f"**{st.session_state.cand_name}** — {st.session_state.assess_title} ({st.session_state.duration} min)")
    questions = session.sql(f"""
        SELECT question_id, question_type, question_text, options, max_score, sort_order
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS WHERE assessment_id = {assess_id} ORDER BY sort_order
    """).to_pandas()
    if len(questions) == 0:
        st.error("No questions found.")
        return
    answers = {}
    with st.form("answer_form"):
        for _, row in questions.iterrows():
            st.markdown(f"---")
            st.markdown(f"**Question {row['SORT_ORDER']}** | {row['QUESTION_TYPE']} | {row['MAX_SCORE']} pts")
            st.markdown(row["QUESTION_TEXT"])
            if row["QUESTION_TYPE"] == "MCQ" and row["OPTIONS"]:
                opts = json.loads(row["OPTIONS"]) if isinstance(row["OPTIONS"], str) else row["OPTIONS"]
                if opts and isinstance(opts, list):
                    answers[row["QUESTION_ID"]] = st.radio("Answer:", opts, key=f"q_{row['QUESTION_ID']}")
            elif row["QUESTION_TYPE"] == "SHORT_ANSWER":
                answers[row["QUESTION_ID"]] = st.text_area("Answer:", height=80, key=f"q_{row['QUESTION_ID']}")
            else:
                answers[row["QUESTION_ID"]] = st.text_area("Answer:", height=150, key=f"q_{row['QUESTION_ID']}")
        col1, col2 = st.columns(2)
        save_btn = col1.form_submit_button("Save Progress", use_container_width=True)
        submit_btn = col2.form_submit_button("Submit Assessment", type="primary", use_container_width=True)
    if save_btn or submit_btn:
        for q_id, ans in answers.items():
            if ans:
                existing = session.sql(f"SELECT answer_id FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS WHERE candidate_id = {cand_id} AND question_id = {q_id}").collect()
                if existing:
                    session.sql(f"UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS SET answer_text = ?, answered_at = CURRENT_TIMESTAMP() WHERE candidate_id = {cand_id} AND question_id = {q_id}", params=[ans]).collect()
                else:
                    session.sql(f"INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS (candidate_id, question_id, answer_text) VALUES ({cand_id}, {q_id}, ?)", params=[ans]).collect()
        if save_btn:
            st.success("Progress saved!")
        if submit_btn:
            session.sql(f"UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP() WHERE candidate_id = {cand_id}").collect()
            st.session_state.candidate_logged_in = False
            st.success("Assessment submitted!")
            st.balloons()

# Router
pages = {"dashboard": page_dashboard, "create_job": page_create_job, "assessments": page_assessments, "candidates": page_candidates, "results": page_results, "candidate_portal": page_candidate_portal}
pages.get(st.session_state.current_page, page_dashboard)()
