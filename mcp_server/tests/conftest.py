"""Shared test fixtures for Jenkins MCP Server tests."""

from unittest.mock import Mock, patch

import pytest
import jenkins


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for Jenkins connection."""
    monkeypatch.setenv("JENKINS_URL", "http://test-jenkins.com")
    monkeypatch.setenv("JENKINS_USERNAME", "test_user")
    monkeypatch.setenv("JENKINS_PASSWORD", "test_password")
    monkeypatch.setenv("PYTHONHTTPSVERIFY", "0")


@pytest.fixture
def missing_env_vars(monkeypatch):
    """Remove environment variables to test missing credentials."""
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("JENKINS_USERNAME", raising=False)
    monkeypatch.delenv("JENKINS_PASSWORD", raising=False)


@pytest.fixture
def sample_job_info():
    """Sample job information dictionary."""
    return {
        "name": "test-job",
        "url": "http://test-jenkins.com/job/test-job/",
        "buildable": True,
        "builds": [
            {"number": 1, "url": "http://test-jenkins.com/job/test-job/1/"},
            {"number": 2, "url": "http://test-jenkins.com/job/test-job/2/"},
        ],
        "lastBuild": {"number": 2, "url": "http://test-jenkins.com/job/test-job/2/"},
        "nextBuildNumber": 3,
        "description": "Test job description",
        "displayName": "test-job",
        "fullName": "test-job",
        "healthReport": [
            {
                "description": "Build stability: 1 out of the last 5 builds failed.",
                "iconClassName": "icon-health-60to79",
                "iconUrl": "health-60to79.png",
                "score": 80,
            }
        ],
        "inQueue": False,
        "keepDependencies": False,
        "lastSuccessfulBuild": {
            "number": 2,
            "url": "http://test-jenkins.com/job/test-job/2/",
        },
        "property": [],
        "queueItem": None,
    }


@pytest.fixture
def sample_jobs_list():
    """Sample list of all jobs."""
    return [
        {
            "name": "job1",
            "url": "http://test-jenkins.com/job/job1/",
            "color": "blue",
        },
        {
            "name": "job2",
            "url": "http://test-jenkins.com/job/job2/",
            "color": "red",
        },
        {
            "name": "job3",
            "url": "http://test-jenkins.com/job/job3/",
            "color": "disabled",
        },
    ]


@pytest.fixture
def sample_console_output():
    """Sample console output text."""
    return """Started by user admin
Running as SYSTEM
Building in workspace /var/jenkins_home/workspace/test-job
[test-job] $ /bin/sh -xe /tmp/jenkins123456789.sh
+ echo 'Hello World'
Hello World
+ echo 'Job completed successfully'
Job completed successfully
Finished: SUCCESS"""


@pytest.fixture
def jenkins_exception():
    """Jenkins exception fixture."""
    return jenkins.JenkinsException("Jenkins server error")


@pytest.fixture
def mock_logger():
    """Mock logger instance."""
    with patch("mcp_server.libs.jenkins_api.get_logger") as mock_get_logger:
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def valid_job_parameters():
    """Valid job parameters for testing."""
    return {"param1": "value1", "param2": "value2", "branch": "main"}


@pytest.fixture
def invalid_json_parameters():
    """Invalid JSON string for parameter testing."""
    return '{"invalid": json, "missing": quote}'


@pytest.fixture
def empty_job_info():
    """Empty job info (no builds)."""
    return {
        "name": "empty-job",
        "url": "http://test-jenkins.com/job/empty-job/",
        "buildable": True,
        "builds": [],
        "lastBuild": None,
        "nextBuildNumber": 1,
        "description": "Empty test job",
    }
