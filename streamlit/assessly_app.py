import streamlit as st
import json
from snowflake.snowpark.context import get_active_session

# ============================================================
# CONFIG & SESSION
# ============================================================
st.set_page_config(page_title="Assessly", layout="wide")
session = get_active_session()

# Custom CSS for polished UI
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
        font-size: 1rem;
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
    .stat-card h2 {
        margin: 0;
        font-size: 2rem;
        color: white;
    }
    .stat-card p {
        margin: 5px 0 0 0;
        opacity: 0.9;
        font-size: 0.85rem;
    }
    .card {
        background: #f8f9fc;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .badge-hired {
        background: #d1fae5;
        color: #065f46;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-no {
        background: #fee2e2;
        color: #991b1b;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-maybe {
        background: #fef3c7;
        color: #92400e;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
    }
    div[data-testid="stSidebar"] .stMarkdown h1,
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] label {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# State
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"
if "candidate_logged_in" not in st.session_state:
    st.session_state.candidate_logged_in = False

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("# ✦ ASSESSLY")
    st.markdown("*AI Hiring Agent*")
    st.markdown("---")
    
    mode = st.radio("Select Mode", ["Recruiter", "Candidate"], label_visibility="collapsed")
    
    if mode == "Recruiter":
        st.markdown("---")
        menu_items = {
            "Dashboard": "dashboard",
            "Create Job": "create_job",
            "Assessments": "assessments",
            "Candidates": "candidates",
            "Results & Reports": "results",
        }
        for label, page_key in menu_items.items():
            if st.button(label, use_container_width=True, 
                        type="primary" if st.session_state.current_page == page_key else "secondary"):
                st.session_state.current_page = page_key
                st.rerun()
    else:
        st.session_state.current_page = "candidate_portal"
    
    st.markdown("---")
    st.caption("Powered by Snowflake Cortex AI")


# ============================================================
# PAGE: DASHBOARD
# ============================================================
def page_dashboard():
    st.markdown('<p class="main-header">Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Overview of your hiring pipeline</p>', unsafe_allow_html=True)
    
    jobs_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS").collect()[0]["CNT"]
    assessments_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS WHERE status = 'PUBLISHED'").collect()[0]["CNT"]
    candidates_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES").collect()[0]["CNT"]
    evaluated_count = session.sql("SELECT COUNT(*) as cnt FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES WHERE status = 'EVALUATED'").collect()[0]["CNT"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="stat-card"><h2>{jobs_count}</h2><p>Total Jobs</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card"><h2>{assessments_count}</h2><p>Active Assessments</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="stat-card"><h2>{candidates_count}</h2><p>Total Candidates</p></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="stat-card"><h2>{evaluated_count}</h2><p>Evaluated</p></div>""", unsafe_allow_html=True)
    
    st.markdown("")
    st.markdown("")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("Recent Jobs")
        jobs_df = session.sql("""
            SELECT job_id as ID, title as Title, department as Department, 
                   seniority_level as Seniority, status as Status, created_at as Created
            FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS ORDER BY created_at DESC LIMIT 5
        """).to_pandas()
        
        if len(jobs_df) > 0:
            st.dataframe(jobs_df, use_container_width=True, hide_index=True)
        else:
            st.info("No jobs created yet. Click **Create Job** to get started!")
    
    with col_right:
        st.subheader("Pending Reviews")
        pending_df = session.sql("""
            SELECT c.candidate_name as Candidate, c.status as Status
            FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c
            WHERE c.status = 'COMPLETED'
            ORDER BY c.completed_at DESC LIMIT 5
        """).to_pandas()
        
        if len(pending_df) > 0:
            for _, row in pending_df.iterrows():
                st.markdown(f"**{row['CANDIDATE']}** — awaiting evaluation")
        else:
            st.caption("No pending reviews")


# ============================================================
# PAGE: CREATE JOB
# ============================================================
def page_create_job():
    st.markdown('<p class="main-header">Create New Job</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Describe the role and let AI generate the assessment</p>', unsafe_allow_html=True)
    
    with st.form("create_job_form"):
        title = st.text_input("Job Title *", placeholder="e.g. Senior Backend Engineer")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            department = st.text_input("Department", placeholder="e.g. Engineering")
        with col2:
            seniority = st.selectbox("Seniority Level", 
                ["Junior", "Mid-level", "Senior", "Lead", "Principal", "Manager"])
        with col3:
            employment_type = st.selectbox("Employment Type",
                ["Full-time", "Part-time", "Contract", "Internship"])
        
        description = st.text_area("Job Description *", height=120,
            placeholder="Describe the role, responsibilities, and what the ideal candidate looks like...")
        
        requirements = st.text_area("Requirements & Skills *", height=120,
            placeholder="List technical skills, experience requirements, certifications, etc...")
        
        st.markdown("---")
        auto_generate = st.checkbox("Auto-generate assessment after creating job", value=True)
        submitted = st.form_submit_button("Create Job & Generate Assessment", type="primary", use_container_width=True)
    
    if submitted:
        if not title or not description:
            st.error("Please fill in Job Title and Description.")
            return
        
        with st.spinner("Creating job..."):
            session.sql("""
                INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS (title, description, requirements, department, seniority_level, employment_type, status)
                VALUES (?, ?, ?, ?, ?, ?, 'DRAFT')
            """, params=[title, description, requirements, department, seniority, employment_type]).collect()
            job_id = session.sql("SELECT MAX(job_id) as id FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS").collect()[0]["ID"]
        
        st.success(f"Job **{title}** created! (ID: {job_id})")
        
        if auto_generate:
            with st.spinner("AI is analyzing competencies..."):
                result = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_COMPETENCIES({job_id})").collect()[0][0]
                st.info(f"Competencies: {result}")
            
            with st.spinner("AI is generating assessment questions — this may take 30-60 seconds..."):
                result = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_ASSESSMENT({job_id})").collect()[0][0]
                st.success(f"Assessment: {result}")
            
            st.balloons()


# ============================================================
# PAGE: ASSESSMENTS
# ============================================================
def page_assessments():
    st.markdown('<p class="main-header">Assessments</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Review AI-generated assessments and manage questions</p>', unsafe_allow_html=True)
    
    assessments_df = session.sql("""
        SELECT a.assessment_id, a.title, j.title as job_title, a.duration_minutes, 
               a.total_questions, a.passing_score, a.status, a.created_at
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id
        ORDER BY a.created_at DESC
    """).to_pandas()
    
    if len(assessments_df) == 0:
        st.info("No assessments yet. Create a job to auto-generate one.")
        return
    
    assessment_options = {f"{row['TITLE']} ({row['STATUS']})": row['ASSESSMENT_ID'] 
                         for _, row in assessments_df.iterrows()}
    selected_label = st.selectbox("Select Assessment", list(assessment_options.keys()))
    selected_id = assessment_options[selected_label]
    
    assessment_row = assessments_df[assessments_df['ASSESSMENT_ID'] == selected_id].iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Questions", assessment_row['TOTAL_QUESTIONS'])
    col2.metric("Duration", f"{assessment_row['DURATION_MINUTES']} min")
    col3.metric("Passing Score", f"{assessment_row['PASSING_SCORE']}%")
    col4.metric("Status", assessment_row['STATUS'])
    
    if assessment_row['STATUS'] == 'DRAFT':
        if st.button("Publish Assessment", type="primary"):
            session.sql(f"""
                UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS 
                SET status = 'PUBLISHED', published_at = CURRENT_TIMESTAMP() 
                WHERE assessment_id = {selected_id}
            """).collect()
            st.success("Assessment published! Candidates can now be invited.")
            st.rerun()
    else:
        st.success("This assessment is **PUBLISHED** and ready for candidates.")
    
    st.markdown("---")
    st.subheader("Questions Preview")
    
    questions_df = session.sql(f"""
        SELECT q.question_id, q.question_type, q.difficulty, q.question_text, 
               q.options, q.correct_answer, q.max_score, q.sort_order,
               c.competency_name
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS q
        LEFT JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES c ON c.competency_id = q.competency_id
        WHERE q.assessment_id = {selected_id}
        ORDER BY q.sort_order
    """).to_pandas()
    
    for _, row in questions_df.iterrows():
        type_emoji = {"MCQ": "🔘", "SHORT_ANSWER": "✍️", "ESSAY": "📝"}.get(row['QUESTION_TYPE'], "❓")
        diff_color = {"EASY": "green", "MEDIUM": "orange", "HARD": "red"}.get(row['DIFFICULTY'], "gray")
        
        with st.expander(f"{type_emoji} Q{row['SORT_ORDER']}. {row['QUESTION_TEXT'][:80]}... — :{diff_color}[{row['DIFFICULTY']}]"):
            st.markdown(f"**Competency:** {row['COMPETENCY_NAME'] or 'General'} | **Max Score:** {row['MAX_SCORE']}")
            st.markdown("---")
            st.write(row['QUESTION_TEXT'])
            
            if row['QUESTION_TYPE'] == 'MCQ' and row['OPTIONS']:
                options = json.loads(row['OPTIONS']) if isinstance(row['OPTIONS'], str) else row['OPTIONS']
                if options:
                    for i, opt in enumerate(options):
                        if opt == row['CORRECT_ANSWER']:
                            st.markdown(f"**:green[{chr(65+i)}. {opt}]** ✓")
                        else:
                            st.markdown(f"{chr(65+i)}. {opt}")
            
            if row['CORRECT_ANSWER'] and row['QUESTION_TYPE'] != 'MCQ':
                with st.popover("View Answer Key"):
                    st.write(row['CORRECT_ANSWER'])


# ============================================================
# PAGE: CANDIDATES
# ============================================================
def page_candidates():
    st.markdown('<p class="main-header">Candidates</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Invite candidates and track their progress</p>', unsafe_allow_html=True)
    
    assessments_df = session.sql("""
        SELECT a.assessment_id, a.title, j.title as job_title
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id
        WHERE a.status = 'PUBLISHED'
        ORDER BY a.created_at DESC
    """).to_pandas()
    
    if len(assessments_df) == 0:
        st.warning("No published assessments. Please publish an assessment first.")
        return
    
    # Add candidate
    with st.expander("➕ Add New Candidate", expanded=True):
        with st.form("add_candidate_form"):
            assessment_options = {f"{row['TITLE']} — {row['JOB_TITLE']}": row['ASSESSMENT_ID'] 
                                 for _, row in assessments_df.iterrows()}
            selected_assessment = st.selectbox("Assessment", list(assessment_options.keys()))
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Candidate Name *")
            with col2:
                email = st.text_input("Candidate Email")
            
            submitted = st.form_submit_button("Add Candidate & Generate Token", type="primary", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("Candidate name is required.")
            else:
                assessment_id = assessment_options[selected_assessment]
                result = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.ADD_CANDIDATE({assessment_id}, ?, ?)", params=[name, email]).collect()[0][0]
                st.success(result)
                st.info("Share the access token with the candidate. They will use it to start the assessment.")
    
    st.markdown("---")
    st.subheader("Candidate List")
    
    candidates_df = session.sql("""
        SELECT c.candidate_id, c.candidate_name as Name, c.candidate_email as Email, 
               c.access_token as Token, c.status as Status, a.title as Assessment,
               c.completed_at as Completed
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
        ORDER BY c.created_at DESC
    """).to_pandas()
    
    if len(candidates_df) > 0:
        # Color-coded status
        st.dataframe(candidates_df[['NAME', 'EMAIL', 'TOKEN', 'STATUS', 'ASSESSMENT']], 
                    use_container_width=True, hide_index=True)
        
        # Evaluate completed candidates
        completed = candidates_df[candidates_df['STATUS'] == 'COMPLETED']
        if len(completed) > 0:
            st.markdown("---")
            st.subheader("Ready for Evaluation")
            for _, row in completed.iterrows():
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"**{row['NAME']}** — {row['ASSESSMENT']}")
                if col2.button("Evaluate with AI", key=f"eval_{row['CANDIDATE_ID']}", type="primary"):
                    with st.spinner(f"AI is evaluating {row['NAME']}..."):
                        result = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATE_CANDIDATE({row['CANDIDATE_ID']})").collect()[0][0]
                        st.success(result)
                    st.rerun()
    else:
        st.info("No candidates yet. Add one above!")


# ============================================================
# PAGE: RESULTS
# ============================================================
def page_results():
    st.markdown('<p class="main-header">Results & Reports</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered evaluation results and hiring recommendations</p>', unsafe_allow_html=True)
    
    results_df = session.sql("""
        SELECT e.evaluation_id, c.candidate_id, c.candidate_name,
               j.title as job_title, e.total_score, e.max_possible_score,
               e.percentage_score, e.recommendation, e.ai_reasoning,
               e.competency_scores, e.created_at
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATIONS e
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c ON c.candidate_id = e.candidate_id
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
        JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id
        ORDER BY e.percentage_score DESC
    """).to_pandas()
    
    if len(results_df) == 0:
        st.info("No evaluation results yet. Evaluate candidates from the Candidates page.")
        return
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Evaluated", len(results_df))
    col2.metric("Strong Hire", len(results_df[results_df['RECOMMENDATION'] == 'STRONG_HIRE']))
    col3.metric("Hire", len(results_df[results_df['RECOMMENDATION'] == 'HIRE']))
    col4.metric("No Hire", len(results_df[results_df['RECOMMENDATION'] == 'NO_HIRE']))
    
    st.markdown("---")
    
    # Ranking
    st.subheader("Candidate Ranking")
    for idx, row in results_df.iterrows():
        rec = row['RECOMMENDATION']
        badge_class = {"STRONG_HIRE": "badge-hired", "HIRE": "badge-hired", "MAYBE": "badge-maybe", "NO_HIRE": "badge-no"}.get(rec, "badge-maybe")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.markdown(f"**{row['CANDIDATE_NAME']}** — {row['JOB_TITLE']}")
        col2.markdown(f"**{row['PERCENTAGE_SCORE']:.0f}%**")
        col3.markdown(f'<span class="{badge_class}">{rec}</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed view
    st.subheader("Detailed Report")
    candidate_options = {f"{row['CANDIDATE_NAME']} ({row['PERCENTAGE_SCORE']:.0f}%)": idx 
                        for idx, row in results_df.iterrows()}
    
    selected = st.selectbox("Select Candidate", list(candidate_options.keys()))
    idx = candidate_options[selected]
    row = results_df.iloc[idx]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Score", f"{row['TOTAL_SCORE']:.0f} / {row['MAX_POSSIBLE_SCORE']:.0f}")
    col2.metric("Percentage", f"{row['PERCENTAGE_SCORE']:.1f}%")
    col3.metric("Recommendation", row['RECOMMENDATION'])
    
    st.markdown("---")
    st.markdown("#### AI Assessment")
    st.write(row['AI_REASONING'])
    
    if row['COMPETENCY_SCORES']:
        scores_data = json.loads(row['COMPETENCY_SCORES']) if isinstance(row['COMPETENCY_SCORES'], str) else row['COMPETENCY_SCORES']
        if scores_data:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Strengths:**")
                for s in scores_data.get('strengths', []):
                    st.markdown(f"- ✅ {s}")
            with col2:
                st.markdown("**Areas to Improve:**")
                for w in scores_data.get('weaknesses', []):
                    st.markdown(f"- ⚠️ {w}")
    
    st.markdown("---")
    if st.button("Generate Detailed Hiring Report", type="primary"):
        with st.spinner("Generating comprehensive report..."):
            report = session.sql(f"CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_RECOMMENDATION({row['CANDIDATE_ID']})").collect()[0][0]
            st.markdown("### Detailed Hiring Report")
            st.markdown(report)


# ============================================================
# PAGE: CANDIDATE PORTAL
# ============================================================
def page_candidate_portal():
    st.markdown('<p class="main-header">Assessment Portal</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete your assessment below</p>', unsafe_allow_html=True)
    
    if st.session_state.candidate_logged_in:
        render_candidate_assessment()
        return
    
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Enter your access token")
        st.caption("You should have received this from your recruiter")
        token = st.text_input("Access Token", type="password", label_visibility="collapsed", placeholder="Paste your access token here")
        
        if st.button("Start Assessment", type="primary", use_container_width=True):
            if not token:
                st.error("Please enter your access token.")
                return
            
            candidate = session.sql("""
                SELECT c.candidate_id, c.candidate_name, c.assessment_id, c.status,
                       a.title as assessment_title, a.duration_minutes
                FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c
                JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
                WHERE c.access_token = ? AND a.status = 'PUBLISHED'
            """, params=[token]).collect()
            
            if not candidate:
                st.error("Invalid token or assessment not available.")
                return
            
            c = candidate[0]
            if c["STATUS"] == "COMPLETED":
                st.warning("You have already completed this assessment.")
                return
            if c["STATUS"] == "EVALUATED":
                st.info("Your assessment has been evaluated. Results will be shared soon.")
                return
            
            st.session_state.candidate_logged_in = True
            st.session_state.candidate_id = c["CANDIDATE_ID"]
            st.session_state.candidate_name = c["CANDIDATE_NAME"]
            st.session_state.assessment_id = c["ASSESSMENT_ID"]
            st.session_state.assessment_title = c["ASSESSMENT_TITLE"]
            st.session_state.duration_minutes = c["DURATION_MINUTES"]
            
            session.sql(f"""
                UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES 
                SET status = 'IN_PROGRESS', started_at = CURRENT_TIMESTAMP()
                WHERE candidate_id = {c['CANDIDATE_ID']}
            """).collect()
            st.rerun()


def render_candidate_assessment():
    candidate_id = st.session_state.candidate_id
    assessment_id = st.session_state.assessment_id
    
    st.info(f"**{st.session_state.candidate_name}** — {st.session_state.assessment_title} ({st.session_state.duration_minutes} min)")
    
    questions = session.sql(f"""
        SELECT question_id, question_type, question_text, options, max_score, sort_order
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS
        WHERE assessment_id = {assessment_id}
        ORDER BY sort_order
    """).to_pandas()
    
    if len(questions) == 0:
        st.error("No questions found.")
        return
    
    existing_answers = session.sql(f"""
        SELECT question_id, answer_text 
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS 
        WHERE candidate_id = {candidate_id}
    """).to_pandas()
    existing_map = dict(zip(existing_answers['QUESTION_ID'].tolist(), existing_answers['ANSWER_TEXT'].tolist())) if len(existing_answers) > 0 else {}
    
    answered_count = len(existing_map)
    st.progress(answered_count / len(questions), text=f"Progress: {answered_count}/{len(questions)} answered")
    
    answers = {}
    
    with st.form("assessment_form"):
        for _, row in questions.iterrows():
            q_id = row['QUESTION_ID']
            st.markdown("---")
            type_label = {"MCQ": "Multiple Choice", "SHORT_ANSWER": "Short Answer", "ESSAY": "Essay/Code"}.get(row['QUESTION_TYPE'], row['QUESTION_TYPE'])
            st.markdown(f"**Question {row['SORT_ORDER']}** | {type_label} | {row['MAX_SCORE']} points")
            st.markdown(row['QUESTION_TEXT'])
            
            default_val = existing_map.get(q_id, "")
            
            if row['QUESTION_TYPE'] == 'MCQ':
                options_data = json.loads(row['OPTIONS']) if isinstance(row['OPTIONS'], str) else row['OPTIONS']
                if options_data and isinstance(options_data, list):
                    answers[q_id] = st.radio(
                        "Select your answer:",
                        options_data,
                        key=f"q_{q_id}",
                        index=options_data.index(default_val) if default_val in options_data else None
                    )
                else:
                    answers[q_id] = st.text_input("Your answer:", value=default_val, key=f"q_{q_id}")
            elif row['QUESTION_TYPE'] == 'SHORT_ANSWER':
                answers[q_id] = st.text_area("Your answer:", value=default_val, height=100, key=f"q_{q_id}")
            elif row['QUESTION_TYPE'] == 'ESSAY':
                answers[q_id] = st.text_area("Your answer:", value=default_val, height=200, key=f"q_{q_id}")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        save_btn = col1.form_submit_button("💾 Save Progress", use_container_width=True)
        submit_btn = col2.form_submit_button("📤 Submit Assessment", type="primary", use_container_width=True)
    
    if save_btn or submit_btn:
        for q_id, answer_text in answers.items():
            if answer_text:
                existing = session.sql(f"""
                    SELECT answer_id FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS 
                    WHERE candidate_id = {candidate_id} AND question_id = {q_id}
                """).collect()
                
                if existing:
                    session.sql(f"""
                        UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS 
                        SET answer_text = ?, answered_at = CURRENT_TIMESTAMP()
                        WHERE candidate_id = {candidate_id} AND question_id = {q_id}
                    """, params=[answer_text]).collect()
                else:
                    session.sql(f"""
                        INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS (candidate_id, question_id, answer_text)
                        VALUES ({candidate_id}, {q_id}, ?)
                    """, params=[answer_text]).collect()
        
        if save_btn:
            st.success("Progress saved!")
        
        if submit_btn:
            answered_now = len([a for a in answers.values() if a])
            if answered_now < len(questions):
                st.warning(f"Please answer all questions ({answered_now}/{len(questions)} answered).")
            else:
                session.sql(f"""
                    UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES 
                    SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP()
                    WHERE candidate_id = {candidate_id}
                """).collect()
                st.session_state.candidate_logged_in = False
                st.success("Assessment submitted successfully! Your results will be reviewed shortly.")
                st.balloons()


# ============================================================
# ROUTER
# ============================================================
page_map = {
    "dashboard": page_dashboard,
    "create_job": page_create_job,
    "assessments": page_assessments,
    "candidates": page_candidates,
    "results": page_results,
    "candidate_portal": page_candidate_portal,
}

current = st.session_state.current_page
if current in page_map:
    page_map[current]()
else:
    page_dashboard()
