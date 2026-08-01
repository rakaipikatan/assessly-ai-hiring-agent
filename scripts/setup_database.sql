-- ============================================================
-- ASSESSLY AI HIRING AGENT - Database Setup
-- Run this entire script in a Snowflake worksheet
-- ============================================================

CREATE DATABASE IF NOT EXISTS ASSESSLY_DB;
CREATE SCHEMA IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA;

-- Tables
CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.JOBS (
    job_id NUMBER AUTOINCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    requirements TEXT,
    department VARCHAR(200),
    seniority_level VARCHAR(50),
    employment_type VARCHAR(50) DEFAULT 'Full-time',
    status VARCHAR(20) DEFAULT 'DRAFT',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.COMPETENCIES (
    competency_id NUMBER AUTOINCREMENT PRIMARY KEY,
    job_id NUMBER NOT NULL,
    competency_name VARCHAR(200) NOT NULL,
    competency_category VARCHAR(100),
    description TEXT,
    weight NUMBER(3,2) DEFAULT 1.0,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSMENTS (
    assessment_id NUMBER AUTOINCREMENT PRIMARY KEY,
    job_id NUMBER NOT NULL,
    title VARCHAR(500),
    description TEXT,
    duration_minutes NUMBER DEFAULT 60,
    passing_score NUMBER(5,2) DEFAULT 70.0,
    total_questions NUMBER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'DRAFT',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    published_at TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.QUESTIONS (
    question_id NUMBER AUTOINCREMENT PRIMARY KEY,
    assessment_id NUMBER NOT NULL,
    competency_id NUMBER,
    question_type VARCHAR(20) NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'MEDIUM',
    question_text TEXT NOT NULL,
    options VARIANT,
    correct_answer TEXT,
    rubric TEXT,
    max_score NUMBER(5,2) DEFAULT 10.0,
    sort_order NUMBER DEFAULT 0,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATES (
    candidate_id NUMBER AUTOINCREMENT PRIMARY KEY,
    assessment_id NUMBER NOT NULL,
    candidate_name VARCHAR(300) NOT NULL,
    candidate_email VARCHAR(300),
    access_token VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'INVITED',
    started_at TIMESTAMP_NTZ,
    completed_at TIMESTAMP_NTZ,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.CANDIDATE_ANSWERS (
    answer_id NUMBER AUTOINCREMENT PRIMARY KEY,
    candidate_id NUMBER NOT NULL,
    question_id NUMBER NOT NULL,
    answer_text TEXT,
    score NUMBER(5,2),
    ai_feedback TEXT,
    answered_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.EVALUATIONS (
    evaluation_id NUMBER AUTOINCREMENT PRIMARY KEY,
    candidate_id NUMBER NOT NULL,
    total_score NUMBER(5,2),
    max_possible_score NUMBER(5,2),
    percentage_score NUMBER(5,2),
    recommendation VARCHAR(20),
    ai_reasoning TEXT,
    competency_scores VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
