"""Shared test fixtures for the resume intelligence system."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base_agent import AgentInput, AgentOutput, RetrievedSegment
from src.rag.retriever import Retriever


SAMPLE_RESUME = """
John Doe
Software Engineer | john@example.com

Summary
Experienced software engineer with 5 years of Python development.

Experience
- Built REST API serving 10K requests/day with 99.9% uptime
- Led migration of monolithic app to microservices architecture
- Implemented CI/CD pipeline reducing deployment time by 60%
- Worked on database optimization improving query performance

Education
B.S. Computer Science, MIT, 2018

Skills
Python, JavaScript, FastAPI, React, PostgreSQL, Docker, AWS, Git
"""

SAMPLE_JD = """
Senior Backend Engineer

Responsibilities:
- Design and implement scalable backend services
- Build and maintain RESTful APIs
- Optimize database performance and queries
- Lead technical projects and mentor junior engineers

Requirements:
- 5+ years of Python development experience
- Experience with FastAPI or Django
- Strong knowledge of PostgreSQL
- Experience with Docker and cloud platforms (AWS/GCP)
- Excellent problem-solving skills
"""


@pytest.fixture
def sample_resume() -> str:
    return SAMPLE_RESUME.strip()


@pytest.fixture
def sample_jd() -> str:
    return SAMPLE_JD.strip()


@pytest.fixture
def sample_agent_input(sample_resume: str, sample_jd: str) -> AgentInput:
    return AgentInput(content=sample_resume, job_description=sample_jd)


@pytest.fixture
def mock_retriever() -> AsyncMock:
    retriever = AsyncMock(spec=Retriever)
    retriever.retrieve.return_value = [
        RetrievedSegment(
            content="Built REST API serving 10K requests/day with 99.9% uptime",
            score=0.89,
            segment_id="experience_0",
        ),
        RetrievedSegment(
            content="Led migration of monolithic app to microservices architecture",
            score=0.82,
            segment_id="experience_1",
        ),
        RetrievedSegment(
            content="Implemented CI/CD pipeline reducing deployment time by 60%",
            score=0.78,
            segment_id="experience_2",
        ),
    ]
    retriever.index_segments.return_value = 8
    return retriever


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.generate.return_value = (
        "- Led development of RESTful API serving 10,000+ daily requests with 99.9% uptime\n"
        "- Architected migration from monolithic to microservices, improving scalability by 3x\n"
        "- Implemented CI/CD pipeline that reduced deployment time by 60%\n"
        "- Optimized PostgreSQL queries resulting in 40% performance improvement"
    )
    return llm
