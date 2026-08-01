-- ============================================================
-- ASSESSLY - Standalone Database Setup
-- Run in Snowflake worksheet with "Run All" or via SnowSQL
-- ============================================================

-- Helper function
CREATE OR REPLACE FUNCTION ASSESSLY_DB.ASSESSLY_SCHEMA.PARSE_AI_JSON(response TEXT)
RETURNS VARIANT
LANGUAGE SQL
AS
$$
    TRY_PARSE_JSON(
        TRIM(
            REGEXP_REPLACE(
                REGEXP_REPLACE(TRIM(response), '^```(json)?\\s*', ''),
                '\\s*```$', ''
            )
        )
    )
$$;

-- Generate competencies
CREATE OR REPLACE PROCEDURE ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_COMPETENCIES(p_job_id NUMBER)
RETURNS TEXT
LANGUAGE SQL
EXECUTE AS CALLER
AS
DECLARE
    v_title VARCHAR;
    v_description TEXT;
    v_requirements TEXT;
    v_seniority VARCHAR;
    v_prompt TEXT;
    v_response TEXT;
    v_competencies VARIANT;
BEGIN
    SELECT title, description, requirements, seniority_level
    INTO :v_title, :v_description, :v_requirements, :v_seniority
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS WHERE job_id = :p_job_id;

    v_prompt := 'You are an expert HR consultant. Analyze this job and extract key competencies. Job Title: ' || :v_title || ' | Description: ' || COALESCE(:v_description, 'N/A') || ' | Requirements: ' || COALESCE(:v_requirements, 'N/A') || ' | Seniority: ' || COALESCE(:v_seniority, 'N/A') || '. Return a JSON array of competencies. Each must have: name (string), category (TECHNICAL or SOFT_SKILL or DOMAIN_KNOWLEDGE or PROBLEM_SOLVING), description (string), weight (number 0.5 to 2.0). Return ONLY valid JSON array, no markdown, no code blocks.';

    v_response := SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', :v_prompt);
    v_competencies := ASSESSLY_DB.ASSESSLY_SCHEMA.PARSE_AI_JSON(:v_response);

    IF (v_competencies IS NULL) THEN
        RETURN 'ERROR: Failed to parse AI response';
    END IF;

    DELETE FROM ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES WHERE job_id = :p_job_id;

    INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES (job_id, competency_name, competency_category, description, weight)
    SELECT :p_job_id, f.value:name::VARCHAR, f.value:category::VARCHAR, f.value:description::VARCHAR, f.value:weight::NUMBER(3,2)
    FROM TABLE(FLATTEN(input => :v_competencies)) f;

    RETURN 'SUCCESS: Generated ' || ARRAY_SIZE(:v_competencies) || ' competencies';
END;

-- Generate assessment with questions
CREATE OR REPLACE PROCEDURE ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_ASSESSMENT(p_job_id NUMBER)
RETURNS TEXT
LANGUAGE SQL
EXECUTE AS CALLER
AS
DECLARE
    v_title VARCHAR;
    v_seniority VARCHAR;
    v_assessment_id NUMBER;
    v_competency_list TEXT;
    v_prompt TEXT;
    v_response TEXT;
    v_questions VARIANT;
BEGIN
    SELECT title, seniority_level INTO :v_title, :v_seniority
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS WHERE job_id = :p_job_id;

    SELECT LISTAGG(competency_name || ' (' || competency_category || ')', ', ')
    INTO :v_competency_list
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES WHERE job_id = :p_job_id;

    IF (:v_competency_list IS NULL OR :v_competency_list = '') THEN
        CALL ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_COMPETENCIES(:p_job_id);
        SELECT LISTAGG(competency_name || ' (' || competency_category || ')', ', ')
        INTO :v_competency_list
        FROM ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES WHERE job_id = :p_job_id;
    END IF;

    INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS (job_id, title, description, duration_minutes, status)
    VALUES (:p_job_id, 'Assessment for ' || :v_title, 'AI-generated assessment', 60, 'DRAFT');

    SELECT MAX(assessment_id) INTO :v_assessment_id FROM ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS WHERE job_id = :p_job_id;

    v_prompt := 'You are an expert assessment designer. Create a technical assessment. Position: ' || :v_title || ' | Seniority: ' || COALESCE(:v_seniority, 'Mid-level') || ' | Competencies: ' || :v_competency_list || '. Generate exactly 10 questions: 5 MCQ, 3 SHORT_ANSWER, 2 ESSAY. For each provide: type (MCQ/SHORT_ANSWER/ESSAY), difficulty (EASY/MEDIUM/HARD), question_text, options (array of 4 strings for MCQ, null for others), correct_answer (text), rubric (grading criteria), competency (which competency), max_score (10 for MCQ, 15 for SHORT_ANSWER, 25 for ESSAY). Return ONLY valid JSON array, no markdown, no code blocks.';

    v_response := SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', :v_prompt);
    v_questions := ASSESSLY_DB.ASSESSLY_SCHEMA.PARSE_AI_JSON(:v_response);

    IF (v_questions IS NULL) THEN
        RETURN 'ERROR: Failed to parse AI response for questions';
    END IF;

    INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS (assessment_id, competency_id, question_type, difficulty, question_text, options, correct_answer, rubric, max_score, sort_order)
    SELECT :v_assessment_id, c.competency_id, f.value:type::VARCHAR, f.value:difficulty::VARCHAR,
           f.value:question_text::VARCHAR, f.value:options, f.value:correct_answer::VARCHAR,
           f.value:rubric::VARCHAR, f.value:max_score::NUMBER(5,2), f.index + 1
    FROM TABLE(FLATTEN(input => :v_questions)) f
    LEFT JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES c ON c.job_id = :p_job_id AND c.competency_name = f.value:competency::VARCHAR;

    UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS
    SET total_questions = (SELECT COUNT(*) FROM ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS WHERE assessment_id = :v_assessment_id)
    WHERE assessment_id = :v_assessment_id;

    UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS SET status = 'ASSESSMENT_READY', updated_at = CURRENT_TIMESTAMP() WHERE job_id = :p_job_id;

    RETURN 'SUCCESS: Assessment created with ' || ARRAY_SIZE(:v_questions) || ' questions (ID: ' || :v_assessment_id || ')';
END;

-- Evaluate candidate
CREATE OR REPLACE PROCEDURE ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATE_CANDIDATE(p_candidate_id NUMBER)
RETURNS TEXT
LANGUAGE SQL
EXECUTE AS CALLER
AS
DECLARE
    v_assessment_id NUMBER;
    v_answers_json TEXT;
    v_prompt TEXT;
    v_response TEXT;
    v_eval VARIANT;
    v_total_score NUMBER(5,2);
    v_max_score NUMBER(5,2);
    v_pct NUMBER(5,2);
    v_recommendation VARCHAR;
BEGIN
    SELECT assessment_id INTO :v_assessment_id
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES WHERE candidate_id = :p_candidate_id;

    SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
        'question_id', q.question_id, 'question_type', q.question_type,
        'question_text', q.question_text, 'correct_answer', q.correct_answer,
        'rubric', q.rubric, 'max_score', q.max_score, 'candidate_answer', ca.answer_text
    ))::TEXT INTO :v_answers_json
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS ca
    JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS q ON q.question_id = ca.question_id
    WHERE ca.candidate_id = :p_candidate_id;

    v_prompt := 'You are an expert technical evaluator. Score each answer fairly. Candidate Answers: ' || :v_answers_json || '. Return JSON: {"scores": [{"question_id": <id>, "score": <number>, "feedback": "<text>"}], "overall_assessment": "<text>", "strengths": ["<s1>"], "weaknesses": ["<w1>"]}. Rules: MCQ full marks if correct else 0. SHORT_ANSWER partial credit. ESSAY score by rubric. Return ONLY valid JSON.';

    v_response := SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', :v_prompt);
    v_eval := ASSESSLY_DB.ASSESSLY_SCHEMA.PARSE_AI_JSON(:v_response);

    IF (v_eval IS NULL) THEN
        RETURN 'ERROR: Failed to parse evaluation response';
    END IF;

    UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS ca
    SET score = s.value:score::NUMBER(5,2), ai_feedback = s.value:feedback::VARCHAR
    FROM TABLE(FLATTEN(input => :v_eval:scores)) s
    WHERE ca.question_id = s.value:question_id::NUMBER AND ca.candidate_id = :p_candidate_id;

    SELECT SUM(score), SUM(q.max_score) INTO :v_total_score, :v_max_score
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS ca
    JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS q ON q.question_id = ca.question_id
    WHERE ca.candidate_id = :p_candidate_id;

    v_pct := (:v_total_score / NULLIF(:v_max_score, 0)) * 100;
    v_recommendation := CASE
        WHEN :v_pct >= 80 THEN 'STRONG_HIRE'
        WHEN :v_pct >= 65 THEN 'HIRE'
        WHEN :v_pct >= 50 THEN 'MAYBE'
        ELSE 'NO_HIRE'
    END;

    INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATIONS (candidate_id, total_score, max_possible_score, percentage_score, recommendation, ai_reasoning, competency_scores)
    VALUES (:p_candidate_id, :v_total_score, :v_max_score, :v_pct, :v_recommendation,
            :v_eval:overall_assessment::VARCHAR,
            OBJECT_CONSTRUCT('strengths', :v_eval:strengths, 'weaknesses', :v_eval:weaknesses));

    UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES SET status = 'EVALUATED' WHERE candidate_id = :p_candidate_id;

    RETURN 'SUCCESS: Score ' || :v_pct || '% - Recommendation: ' || :v_recommendation;
END;

-- Generate recommendation report
CREATE OR REPLACE PROCEDURE ASSESSLY_DB.ASSESSLY_SCHEMA.GENERATE_RECOMMENDATION(p_candidate_id NUMBER)
RETURNS TEXT
LANGUAGE SQL
EXECUTE AS CALLER
AS
DECLARE
    v_candidate_name VARCHAR;
    v_job_title VARCHAR;
    v_eval_data TEXT;
    v_prompt TEXT;
    v_response TEXT;
BEGIN
    SELECT c.candidate_name, j.title,
           OBJECT_CONSTRUCT('total_score', e.total_score, 'max_score', e.max_possible_score,
               'percentage', e.percentage_score, 'recommendation', e.recommendation,
               'reasoning', e.ai_reasoning, 'competency_scores', e.competency_scores)::TEXT
    INTO :v_candidate_name, :v_job_title, :v_eval_data
    FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES c
    JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS a ON a.assessment_id = c.assessment_id
    JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS j ON j.job_id = a.job_id
    JOIN ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATIONS e ON e.candidate_id = c.candidate_id
    WHERE c.candidate_id = :p_candidate_id;

    v_prompt := 'You are a senior hiring manager. Write a professional hiring recommendation report (3-5 paragraphs). Candidate: ' || :v_candidate_name || ' | Position: ' || :v_job_title || ' | Data: ' || :v_eval_data || '. Include: 1) Executive summary 2) Key strengths 3) Areas of concern 4) Final recommendation with confidence 5) Suggested next steps.';

    v_response := SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', :v_prompt);

    UPDATE ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATIONS SET ai_reasoning = :v_response WHERE candidate_id = :p_candidate_id;
    RETURN :v_response;
END;

-- Add candidate helper
CREATE OR REPLACE PROCEDURE ASSESSLY_DB.ASSESSLY_SCHEMA.ADD_CANDIDATE(p_assessment_id NUMBER, p_name VARCHAR, p_email VARCHAR)
RETURNS TEXT
LANGUAGE SQL
EXECUTE AS CALLER
AS
DECLARE
    v_token VARCHAR;
    v_candidate_id NUMBER;
BEGIN
    v_token := REPLACE(UUID_STRING(), '-', '');

    INSERT INTO ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES (assessment_id, candidate_name, candidate_email, access_token, status)
    VALUES (:p_assessment_id, :p_name, :p_email, :v_token, 'INVITED');

    SELECT MAX(candidate_id) INTO :v_candidate_id FROM ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES WHERE access_token = :v_token;

    RETURN 'Candidate added. ID: ' || :v_candidate_id || ' | Access Token: ' || :v_token;
END;
